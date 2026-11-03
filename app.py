from __future__ import annotations

import sqlite3
from datetime import date
from pathlib import Path

from flask import Flask, jsonify, render_template, request

BASE_DIR = Path(__file__).resolve().parent
DATABASE = BASE_DIR / "hostel.db"

app = Flask(__name__)


def get_db() -> sqlite3.Connection:
    connection = sqlite3.connect(DATABASE)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def initialize_database() -> None:
    with get_db() as db:
        db.executescript(
            """
            CREATE TABLE IF NOT EXISTS rooms (
                id INTEGER PRIMARY KEY,
                room_number TEXT NOT NULL UNIQUE,
                room_type TEXT NOT NULL,
                capacity INTEGER NOT NULL CHECK (capacity > 0),
                monthly_fee REAL NOT NULL CHECK (monthly_fee >= 0)
            );

            CREATE TABLE IF NOT EXISTS residents (
                id INTEGER PRIMARY KEY,
                full_name TEXT NOT NULL,
                room_id INTEGER NOT NULL REFERENCES rooms(id),
                check_in TEXT NOT NULL,
                check_out TEXT,
                status TEXT NOT NULL CHECK (status IN ('active', 'checked_out'))
            );

            CREATE TABLE IF NOT EXISTS payments (
                id INTEGER PRIMARY KEY,
                resident_id INTEGER NOT NULL REFERENCES residents(id),
                amount REAL NOT NULL CHECK (amount >= 0),
                paid_on TEXT NOT NULL,
                status TEXT NOT NULL CHECK (status IN ('paid', 'pending', 'overdue'))
            );
            """
        )

        if db.execute("SELECT COUNT(*) FROM rooms").fetchone()[0]:
            return

        rooms = [
            ("101", "Single", 1, 8500),
            ("102", "Single", 1, 8500),
            ("103", "Double", 2, 6200),
            ("104", "Double", 2, 6200),
            ("105", "Double", 2, 6200),
            ("201", "Triple", 3, 4800),
            ("202", "Triple", 3, 4800),
            ("203", "Triple", 3, 4800),
            ("204", "Suite", 2, 10500),
            ("205", "Suite", 2, 10500),
        ]
        db.executemany(
            "INSERT INTO rooms (room_number, room_type, capacity, monthly_fee) VALUES (?, ?, ?, ?)",
            rooms,
        )

        residents = [
            ("Aarav Sharma", 1, "2026-02-01", None, "active"),
            ("Isha Patel", 2, "2026-03-12", None, "active"),
            ("Kabir Mehta", 3, "2026-01-18", None, "active"),
            ("Mira Nair", 3, "2026-04-04", None, "active"),
            ("Rohan Das", 4, "2026-02-22", None, "active"),
            ("Ananya Rao", 5, "2026-05-09", None, "active"),
            ("Dev Malhotra", 6, "2026-01-05", None, "active"),
            ("Sana Khan", 6, "2026-01-11", None, "active"),
            ("Vihaan Joshi", 7, "2026-03-03", None, "active"),
            ("Tara Menon", 8, "2026-04-15", None, "active"),
            ("Arjun Singh", 9, "2026-02-16", None, "active"),
            ("Nisha Verma", 9, "2026-06-02", None, "active"),
            ("Reyansh Shah", 10, "2026-01-28", None, "active"),
            ("Myra Kapoor", 4, "2025-08-01", "2026-01-20", "checked_out"),
        ]
        db.executemany(
            "INSERT INTO residents (full_name, room_id, check_in, check_out, status) VALUES (?, ?, ?, ?, ?)",
            residents,
        )

        payment_rows = []
        today = date.today()
        monthly_fees = {
            row["id"]: row["monthly_fee"]
            for row in db.execute("SELECT id, monthly_fee FROM rooms").fetchall()
        }
        for month_offset in range(5, -1, -1):
            month_index = today.month - 1 - month_offset
            year = today.year + month_index // 12
            month = month_index % 12 + 1
            paid_on = f"{year:04d}-{month:02d}-05"
            for resident_id in range(1, 14):
                room_id = residents[resident_id - 1][1]
                amount = monthly_fees[room_id]
                payment_status = (
                    "overdue" if month_offset == 0 and resident_id in (5, 11)
                    else "pending" if month_offset == 0 and resident_id == 8
                    else "paid"
                )
                payment_rows.append((resident_id, amount, paid_on, payment_status))

        db.executemany(
            "INSERT INTO payments (resident_id, amount, paid_on, status) VALUES (?, ?, ?, ?)",
            payment_rows,
        )


def dashboard_data(selected_month: str, selected_type: str) -> dict:
    with get_db() as db:
        room_filter = ""
        parameters: list[str] = []
        if selected_type != "All room types":
            room_filter = "AND r.room_type = ?"
            parameters.append(selected_type)

        occupancy = db.execute(
            f"""
            WITH room_capacity AS (
                SELECT COALESCE(SUM(r.capacity), 0) AS beds
                FROM rooms r
                WHERE 1 = 1 {room_filter}
            ),
            occupied_residents AS (
                SELECT COUNT(res.id) AS occupied
                FROM residents res
                JOIN rooms r ON r.id = res.room_id
                WHERE res.status = 'active' {room_filter}
            )
            SELECT room_capacity.beds, occupied_residents.occupied
            FROM room_capacity, occupied_residents
            """,
            [*parameters, *parameters],
        ).fetchone()
        total_beds = occupancy["beds"]
        occupied_beds = occupancy["occupied"]

        revenue = db.execute(
            f"""
            SELECT COALESCE(SUM(p.amount), 0) AS amount
            FROM payments p
            JOIN residents res ON res.id = p.resident_id
            JOIN rooms r ON r.id = res.room_id
            WHERE p.status = 'paid' AND strftime('%Y-%m', p.paid_on) = ?
                {room_filter}
            """,
            [selected_month, *parameters],
        ).fetchone()["amount"]

        payment_counts = db.execute(
            f"""
            SELECT p.status, COUNT(*) AS count, COALESCE(SUM(p.amount), 0) AS amount
            FROM payments p
            JOIN residents res ON res.id = p.resident_id
            JOIN rooms r ON r.id = res.room_id
            WHERE strftime('%Y-%m', p.paid_on) = ? {room_filter}
            GROUP BY p.status
            """,
            [selected_month, *parameters],
        ).fetchall()
        payment_status = {row["status"]: row["count"] for row in payment_counts}

        room_rows = db.execute(
            f"""
            WITH room_stats AS (
                SELECT r.id, r.room_type, r.capacity, COUNT(res.id) AS occupied
                FROM rooms r
                LEFT JOIN residents res
                    ON res.room_id = r.id AND res.status = 'active'
                GROUP BY r.id
            )
            SELECT room_type, SUM(capacity) AS capacity, SUM(occupied) AS occupied
            FROM room_stats
            WHERE 1 = 1 {"AND room_type = ?" if selected_type != "All room types" else ""}
            GROUP BY room_type
            ORDER BY room_type
            """,
            [selected_type] if selected_type != "All room types" else [],
        ).fetchall()

        monthly_rows = db.execute(
            f"""
            SELECT strftime('%Y-%m', p.paid_on) AS month,
                   COALESCE(SUM(CASE WHEN p.status = 'paid' THEN p.amount ELSE 0 END), 0) AS revenue
            FROM payments p
            JOIN residents res ON res.id = p.resident_id
            JOIN rooms r ON r.id = res.room_id
            WHERE p.paid_on >= date(?, '-5 months', 'start of month')
                AND p.paid_on < date(?, '+1 month', 'start of month')
                {room_filter}
            GROUP BY month
            ORDER BY month
            """,
            [f"{selected_month}-01", f"{selected_month}-01", *parameters],
        ).fetchall()

        recent_payments = db.execute(
            f"""
            SELECT res.full_name, r.room_number, p.amount, p.status, p.paid_on
            FROM payments p
            JOIN residents res ON res.id = p.resident_id
            JOIN rooms r ON r.id = res.room_id
            WHERE strftime('%Y-%m', p.paid_on) = ? {room_filter}
            ORDER BY CASE p.status WHEN 'overdue' THEN 0 WHEN 'pending' THEN 1 ELSE 2 END,
                     p.amount DESC
            LIMIT 6
            """,
            [selected_month, *parameters],
        ).fetchall()

    occupied_percent = round(occupied_beds / total_beds * 100) if total_beds else 0
    paid_count = payment_status.get("paid", 0)
    pending_count = payment_status.get("pending", 0)
    overdue_count = payment_status.get("overdue", 0)
    expected_revenue = sum(row["amount"] for row in payment_counts)
    collection_rate = round(revenue / expected_revenue * 100) if expected_revenue else 0

    insights = []
    if occupied_percent >= 85:
        insights.append(f"Occupancy is strong at {occupied_percent}%, leaving limited beds to fill.")
    else:
        insights.append(f"{total_beds - occupied_beds} beds are available; a focused admissions campaign could improve occupancy.")
    if overdue_count:
        insights.append(f"{overdue_count} payment(s) are overdue this month. Prioritize gentle reminders to residents.")
    else:
        insights.append("There are no overdue payments for the selected month.")
    insights.append(f"Fee collection is {collection_rate}% for the selected month.")

    return {
        "filters": {
            "month": selected_month,
            "roomTypes": ["All room types", *sorted({row["room_type"] for row in room_rows})]
            if selected_type == "All room types"
            else ["All room types", "Double", "Single", "Suite", "Triple"],
            "roomType": selected_type,
        },
        "kpis": {
            "occupancy": occupied_percent,
            "occupiedBeds": occupied_beds,
            "totalBeds": total_beds,
            "revenue": revenue,
            "collectionRate": collection_rate,
            "overduePayments": overdue_count,
        },
        "charts": {
            "occupancy": {"occupied": occupied_beds, "available": max(total_beds - occupied_beds, 0)},
            "revenueTrend": [
                {"month": row["month"], "revenue": row["revenue"]} for row in monthly_rows
            ],
            "roomTypes": [
                {"type": row["room_type"], "occupied": row["occupied"],
                 "available": max(row["capacity"] - row["occupied"], 0)}
                for row in room_rows
            ],
            "payments": {
                "paid": paid_count,
                "pending": pending_count,
                "overdue": overdue_count,
            },
        },
        "insights": insights,
        "recentPayments": [dict(row) for row in recent_payments],
    }


@app.get("/")
def index():
    return render_template("index.html")


@app.get("/api/dashboard")
def api_dashboard():
    month = request.args.get("month", date.today().strftime("%Y-%m"))
    room_type = request.args.get("roomType", "All room types")
    try:
        date.fromisoformat(f"{month}-01")
    except ValueError:
        return jsonify({"error": "Month must use YYYY-MM format."}), 400
    if room_type not in {"All room types", "Single", "Double", "Triple", "Suite"}:
        return jsonify({"error": "Unknown room type."}), 400
    return jsonify(dashboard_data(month, room_type))


initialize_database()

if __name__ == "__main__":
    app.run(debug=False)
