# Staywise — Hostel Management Analytics

A mini hostel-management analytics dashboard built for a business analytics project. It uses **Flask and SQLite** for SQL-backed data, and Chart.js for interactive charts.

## Features

- KPI cards for occupancy, fee revenue, collection rate, overdue payments, and a performance score
- Interactive occupancy doughnut, six-month revenue bar chart, room-type chart, and payment-status chart
- Month and room-type filters that refresh the dashboard from the SQLite database
- “AI Analyst” insights generated from transparent business rules (no API key or external AI service required)
- Recent payment activity and CSV report export
- Demo hostel records are created automatically the first time the app starts

## Run locally

Requires Python 3.9 or newer.

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

Open [http://127.0.0.1:5000](http://127.0.0.1:5000).

The `hostel.db` SQLite file is created next to `app.py`. Delete that file and restart the app to restore the demo data.

## SQL database

The app initializes three related tables:

- `rooms`: room number, type, bed capacity, and monthly fee
- `residents`: name, room, check-in/check-out dates, and active status
- `payments`: resident, fee amount, payment date, and paid/pending/overdue status

Dashboard totals, filters, and charts are queried from these tables using SQLite SQL. Values supplied by the filters are parameterized.

## Project structure

```text
app.py                 Flask routes, SQLite schema, demo data, analytics queries
templates/index.html   Dashboard layout
static/styles.css      Responsive dashboard design
static/app.js          Chart rendering, filters, insights, CSV export
requirements.txt       Python dependencies
```

> **For a class presentation:** explain that the “AI Analyst” is a rule-based prototype that turns live SQL metrics into readable recommendations. It is intentionally transparent and works offline; connecting a generative AI API would require a separately configured service and credentials.
