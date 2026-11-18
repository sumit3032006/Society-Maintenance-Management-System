# Society Maintenance Management System

A console-based **Python 3 + SQLite3** project for managing a residential society: flats, residents,
monthly maintenance bills, payments (including partial payments), society expenses, complaints and
financial reports.

Developed as a Python and SQL practical assignment for **Anudip Foundation**.

## Features

- **Dashboard** - flats, residents, bills, collection, pending dues, expenses and complaint counts
- **Flat Management** - add, view, search, update, delete flats; list residents of a flat
- **Resident Management** - register, view, search (ID / name / flat), update, delete; SQL JOIN view
- **Maintenance Management** - generate monthly bills for all flats, duplicate-bill prevention,
  search, update amount, safe delete, PAID / PARTIALLY PAID / UNPAID filter
- **Payment Management** - partial payments, overpayment blocked, payment history and search,
  automatic payment status
- **Expense Management** - categorised expenses (Electricity, Water, Cleaning, Security, Repairs ...)
- **Complaint Management** - Pending / In Progress / Resolved workflow
- **Reports and Analytics** - monthly and annual collection, pending dues, flat-wise report,
  expense reports, income versus expenses, outstanding summary
- Optional **sample data** (fictional Indian data) that is asked before it is inserted

## Technology Stack

| Item | Details |
|------|---------|
| Language | Python 3 |
| Database | SQLite3 (built into Python) |
| Interface | Command line / console |
| Extra packages | None |

## Installation

1. Install Python 3.8 or newer from <https://www.python.org/downloads/>.
2. Download or clone this repository:
   ```
   git clone https://github.com/<your-username>/Society_Maintenance_Project.git
   cd Society_Maintenance_Project
   ```
3. No `pip install` is needed (see `requirements.txt`).

## How to Run

```
python society_management.py
```
(On some systems use `python3 society_management.py`.)

## Database Initialization

- The file `society_management.db` is **created automatically** next to the script on first run.
- All six tables (`flats`, `residents`, `maintenance`, `payments`, `expenses`, `complaints`) are created
  with PRIMARY KEY, FOREIGN KEY, UNIQUE, NOT NULL and CHECK constraints.
- Foreign keys are switched on for every connection (`PRAGMA foreign_keys = ON`).
- If the database is empty, the program asks whether to load sample data. You can also choose
  **Dashboard -> Load optional sample data**. Sample data is only loaded into an empty database,
  so it is never duplicated.
- To start again from scratch, delete `society_management.db` and run the program again.

## Sample Usage

1. Run the program and answer `y` to load sample data.
2. Choose `1` Dashboard -> `1` to see the summary.
3. Choose `4` Maintenance -> `1` to generate bills for a new month (running it twice shows duplicate protection).
4. Choose `5` Payment -> `1`, enter flat `B-202`, pick a bill, and pay part of the amount.
5. Choose `8` Reports -> any option to view the analytics.

## Screenshots

Screenshots are stored in the `screenshots/` folder:

| Screen | File |
|--------|------|
| Main menu | `screenshots/01_main_menu.png` |
| Dashboard | `screenshots/02_dashboard.png` |
| Flat management | `screenshots/03_flat_management.png` |
| Resident management | `screenshots/04_resident_management.png` |
| Maintenance management | `screenshots/05_maintenance_management.png` |
| Payment management | `screenshots/06_payment_management.png` |
| Expense management | `screenshots/07_expense_management.png` |
| Complaint management | `screenshots/08_complaint_management.png` |
| Reports | `screenshots/09_reports.png` |

> The images currently supplied are placeholders. Replace them with your own screenshots
> (see `screenshots/HOW_TO_REPLACE_SCREENSHOTS.txt`).

## SQL Concepts Demonstrated

- `CREATE TABLE`, `PRIMARY KEY AUTOINCREMENT`, `FOREIGN KEY ... ON DELETE RESTRICT`
- `NOT NULL`, `UNIQUE`, composite `UNIQUE (flat_id, month, year)`, `CHECK`, `DEFAULT`
- `INSERT`, `SELECT`, `UPDATE`, `DELETE` (CRUD) with **parameterized queries**
- `INNER JOIN`, `LEFT JOIN`, and joins across three tables
- Aggregates: `SUM()`, `COUNT()`, `AVG()`; `GROUP BY`, `ORDER BY`, `WHERE`, `LIKE`
- `CASE` expressions (automatic payment status), `COALESCE`, subqueries, `strftime()`
- Transactions: commit on success, rollback on error

## Project Structure

```
Society_Maintenance_Project/
├── society_management.py      # complete application (single file)
├── README.md
├── requirements.txt
├── .gitignore
├── documentation/
│   └── Society_Maintenance_Synopsis.docx
└── screenshots/
```

## Author and Course

- **Student Name:** [Your Name]
- **Course:** [Course Name]
- **Training Institute:** Anudip Foundation
- **Trainer / Submitted To:** [Trainer Name]
- **Batch / Centre:** [Batch or Centre Name]

All names, phone numbers and e-mail addresses in the sample data are fictional.
