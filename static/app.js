const palette = {
  purple: "#8065e9",
  pale: "#e7e3f7",
  mint: "#54c7a2",
  yellow: "#edbd60",
  coral: "#f08779",
  blue: "#61a8e8",
};

const chartRefs = {};
const money = new Intl.NumberFormat("en-IN", {
  style: "currency",
  currency: "INR",
  maximumFractionDigits: 0,
});

function monthLabel(value) {
  return new Date(`${value}-02T00:00:00`).toLocaleDateString("en-IN", {
    month: "short",
    year: "2-digit",
  });
}

function makeChart(id, config) {
  if (chartRefs[id]) chartRefs[id].destroy();
  const context = document.getElementById(id);
  chartRefs[id] = new Chart(context, config);
}

function renderOccupancy(data) {
  const { occupied, available } = data.charts.occupancy;
  makeChart("occupancy-chart", {
    type: "doughnut",
    data: {
      labels: ["Occupied", "Available"],
      datasets: [{
        data: [occupied, available],
        backgroundColor: [palette.purple, palette.pale],
        borderWidth: 0,
        hoverOffset: 4,
      }],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      cutout: "76%",
      plugins: { legend: { display: false }, tooltip: { enabled: true } },
    },
  });
  document.getElementById("chart-occupancy").textContent = `${data.kpis.occupancy}%`;
  document.getElementById("legend-occupied").textContent = occupied;
  document.getElementById("legend-available").textContent = available;
}

function renderRevenue(data) {
  const rows = data.charts.revenueTrend;
  const total = rows.reduce((sum, row) => sum + row.revenue, 0);
  document.getElementById("trend-total").textContent = money.format(total);
  makeChart("revenue-chart", {
    type: "bar",
    data: {
      labels: rows.map((row) => monthLabel(row.month)),
      datasets: [{
        data: rows.map((row) => row.revenue),
        backgroundColor: rows.map((row) =>
          row.month === data.filters.month ? palette.purple : "#d9d1fb"),
        borderRadius: 5,
        maxBarThickness: 26,
      }],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { display: false },
        tooltip: { callbacks: { label: (context) => money.format(context.raw) } },
      },
      scales: {
        x: { grid: { display: false }, border: { display: false }, ticks: { color: "#9da4b1", font: { size: 8 } } },
        y: {
          beginAtZero: true,
          grid: { color: "#f1f2f6", drawTicks: false },
          border: { display: false },
          ticks: { color: "#a5abb7", font: { size: 8 }, maxTicksLimit: 4, callback: (value) => `₹${Math.round(value / 1000)}k` },
        },
      },
    },
  });
}

function renderRoomTypes(data) {
  const rows = data.charts.roomTypes;
  const colors = [palette.purple, palette.mint, palette.yellow, palette.blue];
  makeChart("room-chart", {
    type: "bar",
    data: {
      labels: rows.map((row) => row.type),
      datasets: [
        { label: "Occupied", data: rows.map((row) => row.occupied), backgroundColor: colors.slice(0, rows.length), borderRadius: 3, barThickness: 10 },
        { label: "Available", data: rows.map((row) => row.available), backgroundColor: "#eeeff4", borderRadius: 3, barThickness: 10 },
      ],
    },
    options: {
      indexAxis: "y",
      responsive: true,
      maintainAspectRatio: false,
      plugins: { legend: { display: false }, tooltip: { mode: "index", intersect: false } },
      scales: {
        x: { stacked: true, beginAtZero: true, grid: { color: "#f1f2f6" }, border: { display: false }, ticks: { color: "#a5abb7", font: { size: 8 }, precision: 0 } },
        y: { stacked: true, grid: { display: false }, border: { display: false }, ticks: { color: "#7f8899", font: { size: 8 } } },
      },
    },
  });
  document.getElementById("room-legend").innerHTML = rows.map((row, index) =>
    `<span><i class="room-chip" style="background:${colors[index % colors.length]}"></i>${row.type}<b>${row.occupied}/${row.occupied + row.available}</b></span>`,
  ).join("");
}

function renderPaymentStatus(data) {
  const status = data.charts.payments;
  const values = [status.paid, status.pending, status.overdue];
  makeChart("payment-chart", {
    type: "doughnut",
    data: {
      labels: ["Paid", "Pending", "Overdue"],
      datasets: [{ data: values, backgroundColor: [palette.mint, palette.yellow, palette.coral], borderWidth: 0, hoverOffset: 4 }],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      cutout: "71%",
      plugins: { legend: { display: false }, tooltip: { enabled: true } },
    },
  });
  document.getElementById("paid-count").textContent = status.paid;
  document.getElementById("pending-count").textContent = status.pending;
  document.getElementById("overdue-count").textContent = status.overdue;
}

function renderPayments(rows) {
  const body = document.getElementById("payments-body");
  document.getElementById("empty-state").hidden = rows.length > 0;
  body.innerHTML = rows.map((payment) => {
    const initials = payment.full_name.split(" ").map((part) => part[0]).slice(0, 2).join("");
    return `<tr>
      <td><span class="resident-cell"><i class="resident-initial">${initials}</i>${payment.full_name}</span></td>
      <td>${payment.room_number}</td>
      <td>${money.format(payment.amount)}</td>
      <td>${payment.paid_on}</td>
      <td><span class="status-pill status-${payment.status}">${payment.status}</span></td>
    </tr>`;
  }).join("");
}

function renderInsights(insights) {
  document.getElementById("insights-list").innerHTML = insights.map((insight) =>
    `<div class="insight"><span class="insight-mark">✦</span><span>${insight}</span></div>`,
  ).join("");
}

async function loadDashboard() {
  const loading = document.getElementById("loading-message");
  loading.textContent = "Refreshing your hostel analytics…";
  loading.classList.add("visible");
  const params = new URLSearchParams({
    month: document.getElementById("month-filter").value,
    roomType: document.getElementById("type-filter").value,
  });
  try {
    const response = await fetch(`/api/dashboard?${params}`);
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || "Could not load dashboard data.");

    document.getElementById("occupancy-value").textContent = `${data.kpis.occupancy}%`;
    document.getElementById("occupied-beds").textContent = data.kpis.occupiedBeds;
    document.getElementById("total-beds").textContent = data.kpis.totalBeds;
    document.getElementById("occupancy-progress").style.width = `${data.kpis.occupancy}%`;
    document.getElementById("revenue-value").textContent = money.format(data.kpis.revenue);
    document.getElementById("collection-rate").textContent = data.kpis.collectionRate;
    document.getElementById("overdue-value").textContent = data.kpis.overduePayments;
    document.getElementById("score-value").textContent =
      Math.round(data.kpis.occupancy * 0.6 + data.kpis.collectionRate * 0.4);

    renderOccupancy(data);
    renderRevenue(data);
    renderRoomTypes(data);
    renderPaymentStatus(data);
    renderPayments(data.recentPayments);
    renderInsights(data.insights);
  } catch (error) {
    loading.textContent = error.message;
    return;
  }
  loading.classList.remove("visible");
}

function exportReport() {
  const month = document.getElementById("month-filter").value;
  const type = document.getElementById("type-filter").value;
  const rows = [
    ["Hostel Analytics Report", month],
    ["Room type filter", type],
    [],
    ["Resident", "Room", "Amount (INR)", "Date", "Status"],
    ...Array.from(document.querySelectorAll("#payments-body tr"), (row) =>
      Array.from(row.querySelectorAll("td"), (cell, index) =>
        index === 0
          ? cell.querySelector(".resident-cell").lastChild.textContent.trim()
          : cell.innerText.replace(/\s+/g, " ").trim(),
      ),
    ),
  ];
  const csv = rows.map((row) => row.map((cell) => `"${String(cell ?? "").replaceAll('"', '""')}"`).join(",")).join("\n");
  const link = document.createElement("a");
  link.href = URL.createObjectURL(new Blob([csv], { type: "text/csv;charset=utf-8" }));
  link.download = `hostel-report-${month}.csv`;
  link.click();
  URL.revokeObjectURL(link.href);
}

const now = new Date();
document.getElementById("month-filter").value = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}`;
document.getElementById("today-date").textContent = now.toLocaleDateString("en-IN", { day: "numeric", month: "long", year: "numeric" }).toUpperCase();
document.getElementById("month-filter").addEventListener("change", loadDashboard);
document.getElementById("type-filter").addEventListener("change", loadDashboard);
document.getElementById("export-button").addEventListener("click", exportReport);
loadDashboard();
