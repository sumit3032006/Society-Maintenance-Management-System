"""
Society Maintenance Management System
======================================
A console-based project built with Python 3 and SQLite3.

It lets a society administrator manage flats, residents, monthly maintenance
bills, payments, society expenses and complaints, and view financial reports.

How to run:
    python society_management.py

The database file (society_management.db) is created automatically in the
same folder as this script the first time the program runs.
"""

import os
import sqlite3
from contextlib import contextmanager
from datetime import date, datetime

# ----------------------------------------------------------------------------
# 1. CONSTANTS
# ----------------------------------------------------------------------------

# The database file is stored next to this script.
DB_NAME = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                       "society_management.db")

LINE = "=" * 70
THIN_LINE = "-" * 70

MONTHS = ["January", "February", "March", "April", "May", "June", "July",
          "August", "September", "October", "November", "December"]

PAYMENT_MODES = ["Cash", "UPI", "Cheque", "Bank Transfer", "Card"]
RESIDENT_TYPES = ["Owner", "Tenant"]
EXPENSE_CATEGORIES = ["Electricity", "Water", "Cleaning", "Security",
                      "Repairs", "Lift Maintenance", "Garden", "Other"]
COMPLAINT_STATUSES = ["Pending", "In Progress", "Resolved"]

# SQL fragment that sorts month names in calendar order (January first).
MONTH_ORDER_SQL = "instr('" + ",".join(MONTHS) + "', m.month)"


# ----------------------------------------------------------------------------
# 2. DATABASE HELPERS
# ----------------------------------------------------------------------------

@contextmanager
def db_connection():
    """Open a connection, turn on foreign keys, commit on success,
    roll back on error and ALWAYS close the connection."""
    conn = sqlite3.connect(DB_NAME)
    conn.execute("PRAGMA foreign_keys = ON")   # SQLite needs this every time
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def fetch_all(sql, params=()):
    """Run a SELECT query and return all rows."""
    with db_connection() as conn:
        return conn.execute(sql, params).fetchall()


def fetch_one(sql, params=()):
    """Run a SELECT query and return the first row (or None)."""
    with db_connection() as conn:
        return conn.execute(sql, params).fetchone()


def run_write(sql, params=()):
    """Run an INSERT / UPDATE / DELETE query and return (rowcount, lastrowid)."""
    with db_connection() as conn:
        cursor = conn.execute(sql, params)
        return cursor.rowcount, cursor.lastrowid


def create_tables():
    """Create all six tables if they do not exist yet."""
    schema = """
    CREATE TABLE IF NOT EXISTS flats (
        flat_id     INTEGER PRIMARY KEY AUTOINCREMENT,
        flat_number TEXT NOT NULL UNIQUE,
        building    TEXT NOT NULL,
        floor       INTEGER CHECK (floor IS NULL OR floor >= 0)
    );

    CREATE TABLE IF NOT EXISTS residents (
        resident_id   INTEGER PRIMARY KEY AUTOINCREMENT,
        name          TEXT NOT NULL,
        phone         TEXT,
        email         TEXT,
        flat_id       INTEGER NOT NULL,
        resident_type TEXT CHECK (resident_type IN ('Owner', 'Tenant')),
        FOREIGN KEY (flat_id) REFERENCES flats (flat_id)
            ON DELETE RESTRICT ON UPDATE CASCADE
    );

    CREATE TABLE IF NOT EXISTS maintenance (
        maintenance_id INTEGER PRIMARY KEY AUTOINCREMENT,
        flat_id        INTEGER NOT NULL,
        month          TEXT NOT NULL,
        year           INTEGER NOT NULL CHECK (year BETWEEN 2000 AND 2100),
        amount         REAL NOT NULL CHECK (amount > 0),
        due_date       TEXT,
        UNIQUE (flat_id, month, year),
        FOREIGN KEY (flat_id) REFERENCES flats (flat_id)
            ON DELETE RESTRICT ON UPDATE CASCADE
    );

    CREATE TABLE IF NOT EXISTS payments (
        payment_id     INTEGER PRIMARY KEY AUTOINCREMENT,
        maintenance_id INTEGER NOT NULL,
        amount_paid    REAL NOT NULL CHECK (amount_paid > 0),
        payment_date   TEXT NOT NULL,
        payment_mode   TEXT CHECK (payment_mode IN
                           ('Cash', 'UPI', 'Cheque', 'Bank Transfer', 'Card')),
        FOREIGN KEY (maintenance_id) REFERENCES maintenance (maintenance_id)
            ON DELETE RESTRICT ON UPDATE CASCADE
    );

    CREATE TABLE IF NOT EXISTS expenses (
        expense_id   INTEGER PRIMARY KEY AUTOINCREMENT,
        description  TEXT NOT NULL,
        category     TEXT,
        amount       REAL NOT NULL CHECK (amount > 0),
        expense_date TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS complaints (
        complaint_id   INTEGER PRIMARY KEY AUTOINCREMENT,
        resident_id    INTEGER NOT NULL,
        description    TEXT NOT NULL,
        status         TEXT NOT NULL DEFAULT 'Pending'
                       CHECK (status IN ('Pending', 'In Progress', 'Resolved')),
        complaint_date TEXT NOT NULL,
        FOREIGN KEY (resident_id) REFERENCES residents (resident_id)
            ON DELETE RESTRICT ON UPDATE CASCADE
    );
    """
    with db_connection() as conn:
        conn.executescript(schema)


# ----------------------------------------------------------------------------
# 3. DISPLAY HELPERS
# ----------------------------------------------------------------------------

def print_header(title):
    """Print a centred heading between two lines."""
    print("\n" + LINE)
    print(title.center(len(LINE)))
    print(LINE)


def print_success(message):
    print(f"\n[SUCCESS] {message}")


def print_error(message):
    print(f"\n[ERROR] {message}")


def print_info(message):
    print(f"\n[INFO] {message}")


def pause():
    input("\nPress Enter to continue...")


def format_cell(value, header):
    """Format one table cell. Columns whose header ends with '(Rs)' are money."""
    if value is None:
        return "-"
    if header.endswith("(Rs)"):
        return f"{float(value):,.2f}"
    if isinstance(value, float):
        return f"{value:,.2f}"
    return str(value)


def print_table(headers, rows):
    """Print rows as a neatly aligned text table."""
    if not rows:
        print_info("No records found.")
        return
    text_rows = [[format_cell(v, h) for v, h in zip(row, headers)] for row in rows]
    widths = [max(len(h), *(len(r[i]) for r in text_rows))
              for i, h in enumerate(headers)]
    # Numbers are right-aligned, text is left-aligned.
    numeric = [all(isinstance(row[i], (int, float)) for row in rows if row[i] is not None)
               for i in range(len(headers))]

    def build(cells):
        parts = []
        for i, cell in enumerate(cells):
            parts.append(cell.rjust(widths[i]) if numeric[i] else cell.ljust(widths[i]))
        return " | ".join(parts)

    print(build(headers))
    print("-+-".join("-" * w for w in widths))
    for r in text_rows:
        print(build(r))
    print(f"\n({len(rows)} record(s))")


def run_menu(title, options):
    """Show a submenu repeatedly until the user chooses 0 (return).
    options is a list of (label, function) pairs."""
    while True:
        print_header(title)
        for number, (label, _) in enumerate(options, start=1):
            print(f"{number}. {label}")
        print("0. Return to Main Menu")
        print(LINE)
        choice = input("Enter your choice: ").strip()
        if choice == "0":
            return
        if choice.isdigit() and 1 <= int(choice) <= len(options):
            try:
                options[int(choice) - 1][1]()
            except sqlite3.IntegrityError as error:
                print_error(explain_integrity_error(error))
            except sqlite3.Error as error:
                print_error(f"Database error: {error}")
            pause()
        else:
            print_error("Invalid choice. Please select a number from the menu.")


def explain_integrity_error(error):
    """Turn a technical SQLite constraint error into a friendly message."""
    message = str(error)
    if "FOREIGN KEY" in message:
        return ("This action breaks a relationship between tables. A record "
                "that is still linked to other records (residents, bills, "
                "payments or complaints) cannot be deleted, and a record "
                "cannot point to something that does not exist.")
    if "UNIQUE" in message:
        return f"Duplicate record: this entry already exists. ({message})"
    if "CHECK" in message:
        return f"The value entered is not allowed. ({message})"
    if "NOT NULL" in message:
        return f"A required field was left empty. ({message})"
    return f"Constraint error: {message}"


# ----------------------------------------------------------------------------
# 4. INPUT VALIDATION HELPERS
# ----------------------------------------------------------------------------

def ask_text(prompt, required=True, default=None):
    """Ask for text. If a default is given, pressing Enter keeps it."""
    while True:
        hint = f" [{default}]" if default not in (None, "") else ""
        value = input(f"{prompt}{hint}: ").strip()
        if value:
            return value
        if default is not None:
            return default
        if not required:
            return ""
        print_error("This field cannot be empty.")


def ask_int(prompt, min_value=None, max_value=None, default=None, required=True):
    """Ask for a whole number within an optional range."""
    while True:
        hint = f" [{default}]" if default is not None else ""
        value = input(f"{prompt}{hint}: ").strip()
        if value == "":
            if default is not None:
                return default
            if not required:
                return None
            print_error("This field cannot be empty.")
            continue
        try:
            number = int(value)
        except ValueError:
            print_error("Please enter a valid whole number.")
            continue
        if min_value is not None and number < min_value:
            print_error(f"Value must be at least {min_value}.")
        elif max_value is not None and number > max_value:
            print_error(f"Value must be at most {max_value}.")
        else:
            return number


def ask_float(prompt, min_value=0.01, default=None):
    """Ask for a money amount (positive number, rounded to 2 decimals)."""
    while True:
        hint = f" [{default}]" if default is not None else ""
        value = input(f"{prompt}{hint}: ").strip()
        if value == "" and default is not None:
            return default
        try:
            number = float(value)
        except ValueError:
            print_error("Please enter a valid number (example: 2500 or 2500.50).")
            continue
        if number != number or number in (float("inf"), float("-inf")):
            print_error("Please enter a normal number.")
        elif number < min_value:
            print_error(f"Amount must be at least {min_value}.")
        else:
            return round(number, 2)


def ask_date(prompt, default=None):
    """Ask for a date in YYYY-MM-DD format and check that it is real."""
    while True:
        hint = f" [{default}]" if default else ""
        value = input(f"{prompt} (YYYY-MM-DD){hint}: ").strip()
        if value == "" and default:
            return default
        try:
            return datetime.strptime(value, "%Y-%m-%d").strftime("%Y-%m-%d")
        except ValueError:
            print_error("Invalid date. Use the format YYYY-MM-DD (example: 2026-11-05).")


def ask_phone(default=""):
    """Ask for an optional 10-digit mobile number."""
    while True:
        value = ask_text("Phone number (10 digits, optional)", required=False,
                         default=default)
        if value == "" or (value.isdigit() and len(value) == 10):
            return value
        print_error("Phone number must contain exactly 10 digits.")


def ask_email(default=""):
    """Ask for an optional e-mail address with a simple format check."""
    while True:
        value = ask_text("Email (optional)", required=False, default=default)
        if value == "":
            return value
        local, _, domain = value.partition("@")
        if local and "." in domain and not domain.startswith(".") \
                and not domain.endswith(".") and " " not in value:
            return value
        print_error("Please enter a valid e-mail address (example: name@example.com).")


def ask_choice(prompt, options, default=None):
    """Show a numbered list of options and return the chosen one."""
    print(f"\n{prompt}")
    for number, option in enumerate(options, start=1):
        print(f"  {number}. {option}")
    default_number = options.index(default) + 1 if default in options else None
    index = ask_int("Enter option number", 1, len(options), default=default_number)
    return options[index - 1]


def ask_yes_no(prompt):
    """Ask a yes/no question and return True or False."""
    while True:
        answer = input(f"{prompt} (y/n): ").strip().lower()
        if answer in ("y", "yes"):
            return True
        if answer in ("n", "no"):
            return False
        print_error("Please type y or n.")


def today():
    return date.today().strftime("%Y-%m-%d")


# ----------------------------------------------------------------------------
# 5. LOOK-UP HELPERS (used by several modules)
# ----------------------------------------------------------------------------

def get_flat_by_number():
    """Ask for a flat number and return its row, or None if not found."""
    number = ask_text("Enter flat number (example: A-101)").upper()
    flat = fetch_one("SELECT flat_id, flat_number, building, floor FROM flats "
                     "WHERE flat_number = ?", (number,))
    if flat is None:
        print_error(f"Flat '{number}' was not found.")
    return flat


def get_resident_by_id():
    """Ask for a resident ID and return the row, or None if not found."""
    resident_id = ask_int("Enter resident ID", 1)
    resident = fetch_one(
        "SELECT r.resident_id, r.name, r.phone, r.email, r.flat_id, r.resident_type, "
        "f.flat_number FROM residents r JOIN flats f ON f.flat_id = r.flat_id "
        "WHERE r.resident_id = ?", (resident_id,))
    if resident is None:
        print_error(f"Resident ID {resident_id} was not found.")
    return resident


# ----------------------------------------------------------------------------
# 6. MODULE 1 - DASHBOARD
# ----------------------------------------------------------------------------

def show_dashboard():
    print_header("DASHBOARD")
    total_flats = fetch_one("SELECT COUNT(*) FROM flats")[0]
    total_residents = fetch_one("SELECT COUNT(*) FROM residents")[0]
    total_bills = fetch_one("SELECT COUNT(*) FROM maintenance")[0]
    billed = fetch_one("SELECT COALESCE(SUM(amount), 0) FROM maintenance")[0]
    collected = fetch_one("SELECT COALESCE(SUM(amount_paid), 0) FROM payments")[0]
    expenses = fetch_one("SELECT COALESCE(SUM(amount), 0) FROM expenses")[0]
    complaint_counts = dict(fetch_all(
        "SELECT status, COUNT(*) FROM complaints GROUP BY status"))

    rows = [
        ("Total flats", total_flats),
        ("Total residents", total_residents),
        ("Total maintenance bills", total_bills),
        ("Total maintenance billed", f"Rs. {billed:,.2f}"),
        ("Total maintenance collected", f"Rs. {collected:,.2f}"),
        ("Total pending maintenance", f"Rs. {billed - collected:,.2f}"),
        ("Total society expenses", f"Rs. {expenses:,.2f}"),
        ("Pending complaints", complaint_counts.get("Pending", 0)),
        ("In-progress complaints", complaint_counts.get("In Progress", 0)),
        ("Resolved complaints", complaint_counts.get("Resolved", 0)),
    ]
    for label, value in rows:
        print(f"  {label:<32}: {value}")




# ----------------------------------------------------------------------------
# 7. SAMPLE DATA (optional)
# ----------------------------------------------------------------------------

def insert_sample_data():
    """Insert fictional sample records in ONE transaction (all or nothing)."""
    flats = [("A-101", "A", 1), ("A-102", "A", 1), ("A-201", "A", 2),
             ("A-202", "A", 2), ("A-301", "A", 3), ("B-101", "B", 1),
             ("B-102", "B", 1), ("B-201", "B", 2), ("B-202", "B", 2),
             ("B-301", "B", 3)]
    # (name, phone, email, flat_number, type) - all names/numbers are fictional.
    residents = [
        ("Rajesh Kulkarni", "9000000101", "rajesh.k@example.com", "A-101", "Owner"),
        ("Priya Deshmukh", "9000000102", "priya.d@example.com", "A-102", "Tenant"),
        ("Amit Patil", "9000000201", "amit.p@example.com", "A-201", "Owner"),
        ("Sneha Joshi", "9000000202", "sneha.j@example.com", "A-202", "Owner"),
        ("Vikram Singh", "9000000301", "vikram.s@example.com", "A-301", "Tenant"),
        ("Neha Sharma", "9000000401", "neha.s@example.com", "B-101", "Owner"),
        ("Suresh Iyer", "9000000402", "suresh.i@example.com", "B-102", "Owner"),
        ("Anita Verma", "9000000501", "anita.v@example.com", "B-201", "Tenant"),
        ("Mohan Naik", "9000000502", "mohan.n@example.com", "B-202", "Owner"),
    ]   # flat B-301 is left vacant on purpose
    expenses = [
        ("Common area electricity bill", "Electricity", 18500.00, "2026-09-07"),
        ("Water tanker supply", "Water", 6200.00, "2026-09-15"),
        ("Housekeeping staff salary", "Cleaning", 12000.00, "2026-09-30"),
        ("Security guard salary", "Security", 21000.00, "2026-09-30"),
        ("Lift repair and servicing", "Repairs", 9500.00, "2026-10-12"),
        ("Common area electricity bill", "Electricity", 17200.00, "2026-10-07"),
        ("Housekeeping staff salary", "Cleaning", 12000.00, "2026-10-31"),
        ("Security guard salary", "Security", 21000.00, "2026-10-31"),
        ("Garden maintenance", "Garden", 3500.00, "2026-11-05"),
    ]
    complaints = [
        (1, "Water leakage from the ceiling in the bedroom.", "Pending", "2026-10-02"),
        (3, "Street light near Block A gate is not working.", "In Progress", "2026-10-10"),
        (5, "Parking slot is occupied by an outside vehicle.", "Resolved", "2026-10-15"),
        (6, "Lift makes a loud noise on the third floor.", "Pending", "2026-11-03"),
        (8, "Garbage is not collected on time.", "Resolved", "2026-11-08"),
    ]

    with db_connection() as conn:
        conn.executemany("INSERT INTO flats (flat_number, building, floor) "
                         "VALUES (?, ?, ?)", flats)
        for name, phone, email, flat_number, rtype in residents:
            conn.execute(
                "INSERT INTO residents (name, phone, email, flat_id, resident_type) "
                "VALUES (?, ?, ?, (SELECT flat_id FROM flats WHERE flat_number = ?), ?)",
                (name, phone, email, flat_number, rtype))

        # Bills: Sep, Oct and Nov 2026, Rs. 2500 per flat.
        for month_no, month in ((9, "September"), (10, "October"), (11, "November")):
            conn.execute(
                "INSERT INTO maintenance (flat_id, month, year, amount, due_date) "
                "SELECT flat_id, ?, 2026, 2500, ? FROM flats ORDER BY flat_id",
                (month, f"2026-{month_no:02d}-10"))

        bill_ids = [r[0] for r in conn.execute(
            "SELECT maintenance_id FROM maintenance ORDER BY maintenance_id")]
        # (index of bill, amount paid, date, mode)
        payments = []
        for i in range(0, 8):
            payments.append((i, 2500, f"2026-09-{5 + i:02d}", PAYMENT_MODES[i % 5]))
        payments.append((8, 1000, "2026-09-20", "Cash"))           # partial
        for i in range(10, 15):
            payments.append((i, 2500, f"2026-10-{4 + i - 10:02d}", PAYMENT_MODES[i % 5]))
        payments.append((15, 1500, "2026-10-18", "UPI"))           # partial
        for i in range(20, 23):
            payments.append((i, 2500, f"2026-11-{3 + i - 20:02d}", "UPI"))
        for index, amount, pay_date, mode in payments:
            conn.execute(
                "INSERT INTO payments (maintenance_id, amount_paid, payment_date, "
                "payment_mode) VALUES (?, ?, ?, ?)",
                (bill_ids[index], amount, pay_date, mode))

        conn.executemany("INSERT INTO expenses (description, category, amount, "
                         "expense_date) VALUES (?, ?, ?, ?)", expenses)
        conn.executemany("INSERT INTO complaints (resident_id, description, status, "
                         "complaint_date) VALUES (?, ?, ?, ?)", complaints)


def load_sample_data():
    """Ask the user, then load sample data - only into an EMPTY database,
    so records are never duplicated when the program restarts."""
    if fetch_one("SELECT COUNT(*) FROM flats")[0] > 0:
        print_info("Sample data can only be loaded into an empty database "
                   "(flats already exist), so nothing was changed.")
        return
    print_info("The sample data contains 10 flats, 9 residents, 30 bills, "
               "payments, expenses and complaints (all fictional).")
    if ask_yes_no("Do you want to insert the sample records?"):
        insert_sample_data()
        print_success("Sample data inserted successfully.")
    else:
        print_info("Starting with an empty database.")


# ----------------------------------------------------------------------------
# 8. MODULE 2 - FLAT MANAGEMENT
# ----------------------------------------------------------------------------

def add_flat():
    print_header("ADD FLAT")
    number = ask_text("Flat number (example: A-101)").upper()
    building = ask_text("Building / block (example: A)").upper()
    floor = ask_int("Floor number (0 = ground floor, optional)", 0, 100, required=False)
    run_write("INSERT INTO flats (flat_number, building, floor) VALUES (?, ?, ?)",
              (number, building, floor))
    print_success(f"Flat {number} added successfully.")


FLAT_LIST_SQL = ("SELECT f.flat_id, f.flat_number, f.building, f.floor, "
                 "COUNT(r.resident_id) FROM flats f "
                 "LEFT JOIN residents r ON r.flat_id = f.flat_id ")
FLAT_HEADERS = ["ID", "Flat No", "Building", "Floor", "Residents"]


def view_flats():
    print_header("ALL FLATS")
    rows = fetch_all(FLAT_LIST_SQL + "GROUP BY f.flat_id ORDER BY f.building, f.flat_number")
    print_table(FLAT_HEADERS, rows)


def search_flats():
    print_header("SEARCH FLAT")
    keyword = ask_text("Enter flat number or building to search")
    rows = fetch_all(FLAT_LIST_SQL + "WHERE f.flat_number LIKE ? OR f.building LIKE ? "
                     "GROUP BY f.flat_id ORDER BY f.flat_number",
                     (f"%{keyword}%", f"%{keyword}%"))
    print_table(FLAT_HEADERS, rows)


def update_flat():
    print_header("UPDATE FLAT")
    flat = get_flat_by_number()
    if flat is None:
        return
    flat_id, old_number, old_building, old_floor = flat
    print_info("Press Enter to keep the current value.")
    number = ask_text("Flat number", default=old_number).upper()
    building = ask_text("Building / block", default=old_building).upper()
    floor = ask_int("Floor number", 0, 100, default=old_floor, required=False)
    run_write("UPDATE flats SET flat_number = ?, building = ?, floor = ? "
              "WHERE flat_id = ?", (number, building, floor, flat_id))
    print_success("Flat details updated successfully.")


def delete_flat():
    print_header("DELETE FLAT")
    flat = get_flat_by_number()
    if flat is None:
        return
    if not ask_yes_no(f"Are you sure you want to delete flat {flat[1]}?"):
        print_info("Delete cancelled.")
        return
    # ON DELETE RESTRICT makes SQLite refuse if residents or bills exist.
    run_write("DELETE FROM flats WHERE flat_id = ?", (flat[0],))
    print_success(f"Flat {flat[1]} deleted.")


def residents_of_flat():
    print_header("RESIDENTS OF A FLAT")
    flat = get_flat_by_number()
    if flat is None:
        return
    print(f"\nFlat {flat[1]} - Building {flat[2]}, Floor {flat[3] if flat[3] is not None else '-'}")
    rows = fetch_all("SELECT resident_id, name, phone, email, resident_type "
                     "FROM residents WHERE flat_id = ? ORDER BY name", (flat[0],))
    print_table(["ID", "Name", "Phone", "Email", "Type"], rows)


def flat_menu():
    run_menu("FLAT MANAGEMENT", [
        ("Add flat", add_flat),
        ("Display all flats", view_flats),
        ("Search flat", search_flats),
        ("Update flat details", update_flat),
        ("Delete flat", delete_flat),
        ("Display residents of a flat", residents_of_flat),
    ])


# ----------------------------------------------------------------------------
# 9. MODULE 3 - RESIDENT MANAGEMENT
# ----------------------------------------------------------------------------

RESIDENT_JOIN_SQL = ("SELECT r.resident_id, r.name, r.phone, r.email, f.flat_number, "
                     "f.building, r.resident_type "
                     "FROM residents r JOIN flats f ON f.flat_id = r.flat_id ")
RESIDENT_HEADERS = ["ID", "Name", "Phone", "Email", "Flat No", "Building", "Type"]


def register_resident():
    print_header("REGISTER RESIDENT")
    name = ask_text("Resident name")
    phone = ask_phone()
    email = ask_email()
    flat = get_flat_by_number()
    if flat is None:
        return
    rtype = ask_choice("Resident type", RESIDENT_TYPES)
    _, new_id = run_write(
        "INSERT INTO residents (name, phone, email, flat_id, resident_type) "
        "VALUES (?, ?, ?, ?, ?)", (name, phone or None, email or None, flat[0], rtype))
    print_success(f"Resident registered with ID {new_id} in flat {flat[1]}.")


def view_residents():
    print_header("ALL RESIDENTS")
    rows = fetch_all(RESIDENT_JOIN_SQL + "ORDER BY f.flat_number, r.name")
    print_table(RESIDENT_HEADERS, rows)


def search_residents():
    print_header("SEARCH RESIDENT")
    by = ask_choice("Search by", ["Resident ID", "Name", "Flat number"])
    if by == "Resident ID":
        rid = ask_int("Enter resident ID", 1)
        rows = fetch_all(RESIDENT_JOIN_SQL + "WHERE r.resident_id = ?", (rid,))
    elif by == "Name":
        keyword = ask_text("Enter name (or part of it)")
        rows = fetch_all(RESIDENT_JOIN_SQL + "WHERE r.name LIKE ? ORDER BY r.name",
                         (f"%{keyword}%",))
    else:
        keyword = ask_text("Enter flat number (or part of it)")
        rows = fetch_all(RESIDENT_JOIN_SQL + "WHERE f.flat_number LIKE ? "
                         "ORDER BY f.flat_number", (f"%{keyword}%",))
    print_table(RESIDENT_HEADERS, rows)


def update_resident():
    print_header("UPDATE RESIDENT")
    resident = get_resident_by_id()
    if resident is None:
        return
    rid, old_name, old_phone, old_email, old_flat_id, old_type, old_flat_no = resident
    print_info("Press Enter to keep the current value.")
    name = ask_text("Resident name", default=old_name)
    phone = ask_phone(default=old_phone or "")
    email = ask_email(default=old_email or "")
    flat_id = old_flat_id
    if ask_yes_no(f"Move resident to a different flat? (currently {old_flat_no})"):
        flat = get_flat_by_number()
        if flat is None:
            return
        flat_id = flat[0]
    rtype = ask_choice("Resident type", RESIDENT_TYPES, default=old_type)
    run_write("UPDATE residents SET name = ?, phone = ?, email = ?, flat_id = ?, "
              "resident_type = ? WHERE resident_id = ?",
              (name, phone or None, email or None, flat_id, rtype, rid))
    print_success("Resident details updated successfully.")


def delete_resident():
    print_header("DELETE RESIDENT")
    resident = get_resident_by_id()
    if resident is None:
        return
    if not ask_yes_no(f"Are you sure you want to delete {resident[1]}?"):
        print_info("Delete cancelled.")
        return
    run_write("DELETE FROM residents WHERE resident_id = ?", (resident[0],))
    print_success("Resident deleted.")


def resident_flat_details():
    """Show one resident together with full flat information (SQL JOIN)."""
    print_header("RESIDENT AND FLAT DETAILS (JOIN)")
    rid = ask_int("Enter resident ID", 1)
    rows = fetch_all(
        "SELECT r.resident_id, r.name, r.resident_type, f.flat_number, f.building, "
        "f.floor, r.phone, r.email "
        "FROM residents r INNER JOIN flats f ON r.flat_id = f.flat_id "
        "WHERE r.resident_id = ?", (rid,))
    print_table(["ID", "Name", "Type", "Flat No", "Building", "Floor", "Phone", "Email"], rows)


def resident_menu():
    run_menu("RESIDENT MANAGEMENT", [
        ("Register resident", register_resident),
        ("View all residents", view_residents),
        ("Search resident (ID / name / flat number)", search_residents),
        ("Update resident details", update_resident),
        ("Delete resident", delete_resident),
        ("Resident and flat information (JOIN)", resident_flat_details),
    ])


# ----------------------------------------------------------------------------
# 10. MODULE 4 - MAINTENANCE MANAGEMENT
# ----------------------------------------------------------------------------

def bill_query(where=""):
    """Return SQL listing bills with paid amount, pending amount and status.
    The status is calculated automatically from the payments made."""
    return (
        "SELECT m.maintenance_id AS bill_id, f.flat_number, m.month, m.year, m.amount, "
        "       COALESCE(SUM(p.amount_paid), 0) AS paid, "
        "       m.amount - COALESCE(SUM(p.amount_paid), 0) AS pending, "
        "       CASE WHEN COALESCE(SUM(p.amount_paid), 0) = 0 THEN 'UNPAID' "
        "            WHEN COALESCE(SUM(p.amount_paid), 0) >= m.amount THEN 'PAID' "
        "            ELSE 'PARTIALLY PAID' END AS status, "
        "       m.due_date "
        "FROM maintenance m "
        "JOIN flats f ON f.flat_id = m.flat_id "
        "LEFT JOIN payments p ON p.maintenance_id = m.maintenance_id "
        + where +
        " GROUP BY m.maintenance_id "
        f"ORDER BY m.year, {MONTH_ORDER_SQL}, f.flat_number")


BILL_HEADERS = ["Bill ID", "Flat No", "Month", "Year", "Amount (Rs)", "Paid (Rs)",
                "Pending (Rs)", "Status", "Due Date"]


def show_bills(where="", params=(), status=None):
    sql = bill_query(where)
    if status:
        sql = f"SELECT * FROM ({sql}) WHERE status = ?"
        params = tuple(params) + (status,)
    print_table(BILL_HEADERS, fetch_all(sql, params))


def generate_monthly_bills():
    print_header("GENERATE MONTHLY MAINTENANCE BILLS")
    flat_count = fetch_one("SELECT COUNT(*) FROM flats")[0]
    if flat_count == 0:
        print_error("There are no flats yet. Add flats first.")
        return
    month = ask_choice("Select month", MONTHS)
    year = ask_int("Year (example: 2026)", 2000, 2100)
    amount = ask_float("Maintenance amount per flat (Rs.)")
    due_date = ask_date("Due date", default=f"{year}-{MONTHS.index(month) + 1:02d}-10")
    created = skipped = 0
    with db_connection() as conn:
        for (flat_id,) in conn.execute("SELECT flat_id FROM flats").fetchall():
            # INSERT OR IGNORE skips a flat that already has a bill for this month.
            cursor = conn.execute(
                "INSERT OR IGNORE INTO maintenance (flat_id, month, year, amount, due_date) "
                "VALUES (?, ?, ?, ?, ?)", (flat_id, month, year, amount, due_date))
            if cursor.rowcount:
                created += 1
            else:
                skipped += 1
    print_success(f"{created} bill(s) created for {month} {year}.")
    if skipped:
        print_info(f"{skipped} flat(s) already had a bill for this month and were skipped "
                   "(duplicate bills are not allowed).")


def add_single_bill():
    print_header("CREATE BILL FOR ONE FLAT")
    flat = get_flat_by_number()
    if flat is None:
        return
    month = ask_choice("Select month", MONTHS)
    year = ask_int("Year (example: 2026)", 2000, 2100)
    amount = ask_float("Maintenance amount (Rs.)")
    due_date = ask_date("Due date", default=f"{year}-{MONTHS.index(month) + 1:02d}-10")
    run_write("INSERT INTO maintenance (flat_id, month, year, amount, due_date) "
              "VALUES (?, ?, ?, ?, ?)", (flat[0], month, year, amount, due_date))
    print_success(f"Bill created for flat {flat[1]} - {month} {year}.")


def view_bills():
    print_header("ALL MAINTENANCE RECORDS")
    show_bills()


def search_bills():
    print_header("SEARCH MAINTENANCE BILLS")
    by = ask_choice("Search by", ["Flat number", "Month", "Year"])
    if by == "Flat number":
        keyword = ask_text("Enter flat number (or part of it)")
        show_bills("WHERE f.flat_number LIKE ?", (f"%{keyword}%",))
    elif by == "Month":
        month = ask_choice("Select month", MONTHS)
        show_bills("WHERE m.month = ?", (month,))
    else:
        year = ask_int("Enter year", 2000, 2100)
        show_bills("WHERE m.year = ?", (year,))


def update_bill_amount():
    print_header("UPDATE MAINTENANCE AMOUNT")
    bill_id = ask_int("Enter bill ID", 1)
    row = fetch_one(bill_query("WHERE m.maintenance_id = ?"), (bill_id,))
    if row is None:
        print_error(f"Bill ID {bill_id} was not found.")
        return
    print_table(BILL_HEADERS, [row])
    paid = row[5]
    new_amount = ask_float("New maintenance amount (Rs.)")
    if new_amount < paid:
        print_error(f"New amount cannot be less than the Rs. {paid:,.2f} already paid.")
        return
    run_write("UPDATE maintenance SET amount = ? WHERE maintenance_id = ?",
              (new_amount, bill_id))
    print_success("Maintenance amount updated.")


def delete_bill():
    print_header("DELETE MAINTENANCE RECORD")
    bill_id = ask_int("Enter bill ID", 1)
    row = fetch_one(bill_query("WHERE m.maintenance_id = ?"), (bill_id,))
    if row is None:
        print_error(f"Bill ID {bill_id} was not found.")
        return
    print_table(BILL_HEADERS, [row])
    if row[5] > 0:
        print_error("This bill already has payments, so it cannot be deleted.")
        return
    if ask_yes_no("Are you sure you want to delete this bill?"):
        run_write("DELETE FROM maintenance WHERE maintenance_id = ?", (bill_id,))
        print_success("Bill deleted.")
    else:
        print_info("Delete cancelled.")


def bills_by_status():
    print_header("BILLS BY PAYMENT STATUS")
    status = ask_choice("Select status", ["PAID", "PARTIALLY PAID", "UNPAID"])
    show_bills(status=status)


def maintenance_menu():
    run_menu("MAINTENANCE MANAGEMENT", [
        ("Generate monthly bills for all flats", generate_monthly_bills),
        ("Create bill for a single flat", add_single_bill),
        ("Display all maintenance records", view_bills),
        ("Search bills (flat / month / year)", search_bills),
        ("Update maintenance amount", update_bill_amount),
        ("Delete maintenance record", delete_bill),
        ("Show paid / partially paid / unpaid bills", bills_by_status),
    ])


# ----------------------------------------------------------------------------
# 11. MODULE 5 - PAYMENT MANAGEMENT
# ----------------------------------------------------------------------------

def add_payment(bill_id, amount, payment_date, mode):
    """Save a payment inside one transaction.
    Returns True if saved, False if it would exceed the outstanding amount."""
    with db_connection() as conn:
        row = conn.execute(
            "SELECT m.amount - COALESCE((SELECT SUM(amount_paid) FROM payments "
            "WHERE maintenance_id = m.maintenance_id), 0) "
            "FROM maintenance m WHERE m.maintenance_id = ?", (bill_id,)).fetchone()
        if row is None or amount > round(row[0], 2):
            return False
        conn.execute("INSERT INTO payments (maintenance_id, amount_paid, payment_date, "
                     "payment_mode) VALUES (?, ?, ?, ?)",
                     (bill_id, amount, payment_date, mode))
    return True


def record_payment():
    print_header("RECORD MAINTENANCE PAYMENT")
    flat = get_flat_by_number()
    if flat is None:
        return
    bills = [b for b in fetch_all(bill_query("WHERE f.flat_number = ?"), (flat[1],))
             if b[6] > 0]
    if not bills:
        print_info(f"Flat {flat[1]} has no outstanding bills.")
        return
    print(f"\nOutstanding bills for flat {flat[1]}:")
    print_table(BILL_HEADERS, bills)
    valid_ids = {b[0]: b for b in bills}
    while True:
        bill_id = ask_int("Enter Bill ID to pay", 1)
        if bill_id in valid_ids:
            break
        print_error("That Bill ID is not in the list above.")
    pending = valid_ids[bill_id][6]
    print_info(f"Outstanding amount for this bill: Rs. {pending:,.2f}")
    while True:
        amount = ask_float("Amount being paid (Rs.)")
        if amount <= pending:
            break
        print_error(f"Payment cannot exceed the outstanding amount (Rs. {pending:,.2f}).")
    mode = ask_choice("Payment mode", PAYMENT_MODES)
    pay_date = ask_date("Payment date", default=today())
    if add_payment(bill_id, amount, pay_date, mode):
        remaining = round(pending - amount, 2)
        status = "PAID" if remaining == 0 else "PARTIALLY PAID"
        print_success(f"Payment of Rs. {amount:,.2f} recorded by {mode}.")
        print(f"   Bill status: {status}   |   Balance due: Rs. {remaining:,.2f}")
    else:
        print_error("Payment was not saved because it exceeds the outstanding amount.")


PAYMENT_SQL = ("SELECT p.payment_id, f.flat_number, m.month, m.year, p.amount_paid, "
               "p.payment_date, p.payment_mode "
               "FROM payments p "
               "JOIN maintenance m ON m.maintenance_id = p.maintenance_id "
               "JOIN flats f ON f.flat_id = m.flat_id ")
PAYMENT_HEADERS = ["Pay ID", "Flat No", "Month", "Year", "Paid (Rs)", "Date", "Mode"]


def payment_history():
    print_header("PAYMENT HISTORY")
    rows = fetch_all(PAYMENT_SQL + "ORDER BY p.payment_date DESC, p.payment_id DESC")
    print_table(PAYMENT_HEADERS, rows)


def search_payments():
    print_header("SEARCH PAYMENT RECORDS")
    by = ask_choice("Search by", ["Flat number", "Payment mode", "Payment date / month"])
    if by == "Flat number":
        keyword = ask_text("Enter flat number (or part of it)")
        rows = fetch_all(PAYMENT_SQL + "WHERE f.flat_number LIKE ? "
                         "ORDER BY p.payment_date DESC", (f"%{keyword}%",))
    elif by == "Payment mode":
        mode = ask_choice("Select mode", PAYMENT_MODES)
        rows = fetch_all(PAYMENT_SQL + "WHERE p.payment_mode = ? "
                         "ORDER BY p.payment_date DESC", (mode,))
    else:
        keyword = ask_text("Enter date or month (example: 2026-10 or 2026-10-05)")
        rows = fetch_all(PAYMENT_SQL + "WHERE p.payment_date LIKE ? "
                         "ORDER BY p.payment_date DESC", (f"{keyword}%",))
    print_table(PAYMENT_HEADERS, rows)


def payment_summary():
    print_header("TOTAL PAID AND PENDING SUMMARY")
    rows = fetch_all(
        f"SELECT status, COUNT(*), SUM(amount), SUM(paid), SUM(pending) "
        f"FROM ({bill_query()}) GROUP BY status ORDER BY status")
    print_table(["Status", "Bills", "Billed (Rs)", "Paid (Rs)", "Pending (Rs)"], rows)
    if rows:
        print(f"\n  Total billed   : Rs. {sum(r[2] for r in rows):,.2f}")
        print(f"  Total paid     : Rs. {sum(r[3] for r in rows):,.2f}")
        print(f"  Total pending  : Rs. {sum(r[4] for r in rows):,.2f}")


def payment_menu():
    run_menu("PAYMENT MANAGEMENT", [
        ("Record maintenance payment", record_payment),
        ("Display payment history", payment_history),
        ("Search payment records", search_payments),
        ("Bill-wise payment status (PAID / PARTIALLY PAID / UNPAID)", view_bills),
        ("Total paid and pending summary", payment_summary),
    ])


# ----------------------------------------------------------------------------
# 12. MODULE 6 - EXPENSE MANAGEMENT
# ----------------------------------------------------------------------------

EXPENSE_HEADERS = ["ID", "Description", "Category", "Amount (Rs)", "Date"]


def add_expense():
    print_header("ADD SOCIETY EXPENSE")
    description = ask_text("Expense description")
    category = ask_choice("Category", EXPENSE_CATEGORIES)
    amount = ask_float("Amount (Rs.)")
    expense_date = ask_date("Expense date", default=today())
    run_write("INSERT INTO expenses (description, category, amount, expense_date) "
              "VALUES (?, ?, ?, ?)", (description, category, amount, expense_date))
    print_success("Expense added successfully.")


def view_expenses():
    print_header("ALL EXPENSES")
    rows = fetch_all("SELECT expense_id, description, category, amount, expense_date "
                     "FROM expenses ORDER BY expense_date DESC, expense_id DESC")
    print_table(EXPENSE_HEADERS, rows)
    if rows:
        print(f"Total expenses: Rs. {sum(r[3] for r in rows):,.2f}")


def search_expenses():
    print_header("SEARCH EXPENSES")
    by = ask_choice("Search by", ["Description keyword", "Category", "Date / month"])
    base = ("SELECT expense_id, description, category, amount, expense_date FROM expenses ")
    if by == "Description keyword":
        keyword = ask_text("Enter keyword")
        rows = fetch_all(base + "WHERE description LIKE ? ORDER BY expense_date DESC",
                         (f"%{keyword}%",))
    elif by == "Category":
        category = ask_choice("Select category", EXPENSE_CATEGORIES)
        rows = fetch_all(base + "WHERE category = ? ORDER BY expense_date DESC", (category,))
    else:
        keyword = ask_text("Enter date or month (example: 2026-10 or 2026-10-05)")
        rows = fetch_all(base + "WHERE expense_date LIKE ? ORDER BY expense_date DESC",
                         (f"{keyword}%",))
    print_table(EXPENSE_HEADERS, rows)


def update_expense():
    print_header("UPDATE EXPENSE")
    expense_id = ask_int("Enter expense ID", 1)
    row = fetch_one("SELECT expense_id, description, category, amount, expense_date "
                    "FROM expenses WHERE expense_id = ?", (expense_id,))
    if row is None:
        print_error(f"Expense ID {expense_id} was not found.")
        return
    print_info("Press Enter to keep the current value.")
    description = ask_text("Description", default=row[1])
    category = ask_choice("Category", EXPENSE_CATEGORIES,
                          default=row[2] if row[2] in EXPENSE_CATEGORIES else None)
    amount = ask_float("Amount (Rs.)", default=row[3])
    expense_date = ask_date("Expense date", default=row[4])
    run_write("UPDATE expenses SET description = ?, category = ?, amount = ?, "
              "expense_date = ? WHERE expense_id = ?",
              (description, category, amount, expense_date, expense_id))
    print_success("Expense updated successfully.")


def delete_expense():
    print_header("DELETE EXPENSE")
    expense_id = ask_int("Enter expense ID", 1)
    row = fetch_one("SELECT expense_id, description, category, amount, expense_date "
                    "FROM expenses WHERE expense_id = ?", (expense_id,))
    if row is None:
        print_error(f"Expense ID {expense_id} was not found.")
        return
    print_table(EXPENSE_HEADERS, [row])
    if ask_yes_no("Are you sure you want to delete this expense?"):
        run_write("DELETE FROM expenses WHERE expense_id = ?", (expense_id,))
        print_success("Expense deleted.")
    else:
        print_info("Delete cancelled.")


def expense_menu():
    run_menu("EXPENSE MANAGEMENT", [
        ("Add society expense", add_expense),
        ("View expenses", view_expenses),
        ("Search expenses", search_expenses),
        ("Update expense", update_expense),
        ("Delete expense", delete_expense),
    ])


# ----------------------------------------------------------------------------
# 13. MODULE 7 - COMPLAINT MANAGEMENT
# ----------------------------------------------------------------------------

COMPLAINT_SQL = ("SELECT c.complaint_id, r.name, f.flat_number, c.description, "
                 "c.status, c.complaint_date "
                 "FROM complaints c "
                 "JOIN residents r ON r.resident_id = c.resident_id "
                 "JOIN flats f ON f.flat_id = r.flat_id ")
COMPLAINT_HEADERS = ["ID", "Resident", "Flat No", "Description", "Status", "Date"]


def register_complaint():
    print_header("REGISTER COMPLAINT")
    resident = get_resident_by_id()
    if resident is None:
        return
    description = ask_text("Complaint description")
    complaint_date = ask_date("Complaint date", default=today())
    _, new_id = run_write("INSERT INTO complaints (resident_id, description, status, "
                          "complaint_date) VALUES (?, ?, 'Pending', ?)",
                          (resident[0], description, complaint_date))
    print_success(f"Complaint registered with ID {new_id} (status: Pending).")


def view_complaints():
    print_header("ALL COMPLAINTS")
    rows = fetch_all(COMPLAINT_SQL + "ORDER BY c.complaint_date DESC, c.complaint_id DESC")
    print_table(COMPLAINT_HEADERS, rows)


def search_complaints():
    print_header("SEARCH COMPLAINTS")
    by = ask_choice("Search by", ["Description keyword", "Status", "Resident name"])
    if by == "Description keyword":
        keyword = ask_text("Enter keyword")
        rows = fetch_all(COMPLAINT_SQL + "WHERE c.description LIKE ? "
                         "ORDER BY c.complaint_date DESC", (f"%{keyword}%",))
    elif by == "Status":
        status = ask_choice("Select status", COMPLAINT_STATUSES)
        rows = fetch_all(COMPLAINT_SQL + "WHERE c.status = ? "
                         "ORDER BY c.complaint_date DESC", (status,))
    else:
        keyword = ask_text("Enter resident name (or part of it)")
        rows = fetch_all(COMPLAINT_SQL + "WHERE r.name LIKE ? "
                         "ORDER BY c.complaint_date DESC", (f"%{keyword}%",))
    print_table(COMPLAINT_HEADERS, rows)


def get_complaint():
    complaint_id = ask_int("Enter complaint ID", 1)
    row = fetch_one(COMPLAINT_SQL + "WHERE c.complaint_id = ?", (complaint_id,))
    if row is None:
        print_error(f"Complaint ID {complaint_id} was not found.")
    return row


def update_complaint_description():
    print_header("UPDATE COMPLAINT DESCRIPTION")
    row = get_complaint()
    if row is None:
        return
    description = ask_text("New description", default=row[3])
    run_write("UPDATE complaints SET description = ? WHERE complaint_id = ?",
              (description, row[0]))
    print_success("Complaint description updated.")


def update_complaint_status():
    print_header("UPDATE COMPLAINT STATUS")
    row = get_complaint()
    if row is None:
        return
    print_info(f"Current status: {row[4]}")
    status = ask_choice("New status", COMPLAINT_STATUSES, default=row[4])
    run_write("UPDATE complaints SET status = ? WHERE complaint_id = ?", (status, row[0]))
    print_success(f"Complaint {row[0]} is now '{status}'.")


def delete_complaint():
    print_header("DELETE COMPLAINT")
    row = get_complaint()
    if row is None:
        return
    if ask_yes_no("Are you sure you want to delete this complaint?"):
        run_write("DELETE FROM complaints WHERE complaint_id = ?", (row[0],))
        print_success("Complaint deleted.")
    else:
        print_info("Delete cancelled.")


def complaint_menu():
    run_menu("COMPLAINT MANAGEMENT", [
        ("Register complaint", register_complaint),
        ("View all complaints", view_complaints),
        ("Search complaints", search_complaints),
        ("Update complaint description", update_complaint_description),
        ("Update complaint status", update_complaint_status),
        ("Delete complaint", delete_complaint),
    ])


# ----------------------------------------------------------------------------
# 14. MODULE 8 - REPORTS AND ANALYTICS
# ----------------------------------------------------------------------------

# Total paid for each bill, used to avoid double counting in the reports.
PAID_PER_BILL = ("LEFT JOIN (SELECT maintenance_id, SUM(amount_paid) AS paid "
                 "FROM payments GROUP BY maintenance_id) p "
                 "ON p.maintenance_id = m.maintenance_id ")


def monthly_collection_report():
    print_header("MONTHLY MAINTENANCE COLLECTION REPORT")
    rows = fetch_all(
        "SELECT m.year, m.month, COUNT(*), SUM(m.amount), "
        "SUM(COALESCE(p.paid, 0)), SUM(m.amount - COALESCE(p.paid, 0)) "
        "FROM maintenance m " + PAID_PER_BILL +
        f"GROUP BY m.year, m.month ORDER BY m.year, {MONTH_ORDER_SQL}")
    print_table(["Year", "Month", "Bills", "Billed (Rs)", "Collected (Rs)",
                 "Pending (Rs)"], rows)


def annual_collection_report():
    print_header("ANNUAL MAINTENANCE COLLECTION REPORT")
    rows = fetch_all(
        "SELECT m.year, COUNT(*), SUM(m.amount), SUM(COALESCE(p.paid, 0)), "
        "SUM(m.amount - COALESCE(p.paid, 0)), AVG(m.amount) "
        "FROM maintenance m " + PAID_PER_BILL +
        "GROUP BY m.year ORDER BY m.year")
    print_table(["Year", "Bills", "Billed (Rs)", "Collected (Rs)", "Pending (Rs)",
                 "Avg Bill (Rs)"], rows)


def pending_dues_report():
    print_header("PENDING DUES REPORT")
    rows = fetch_all(f"SELECT * FROM ({bill_query()}) WHERE pending > 0")
    print_table(BILL_HEADERS, rows)
    if rows:
        print(f"Total pending dues: Rs. {sum(r[6] for r in rows):,.2f}")


def flatwise_report():
    print_header("FLAT-WISE MAINTENANCE REPORT")
    rows = fetch_all(
        "SELECT f.flat_number, COUNT(m.maintenance_id), COALESCE(SUM(m.amount), 0), "
        "COALESCE(SUM(p.paid), 0), COALESCE(SUM(m.amount - COALESCE(p.paid, 0)), 0), "
        "COALESCE(AVG(m.amount), 0) "
        "FROM flats f LEFT JOIN maintenance m ON m.flat_id = f.flat_id " + PAID_PER_BILL +
        "GROUP BY f.flat_id ORDER BY f.flat_number")
    print_table(["Flat No", "Bills", "Billed (Rs)", "Paid (Rs)", "Pending (Rs)",
                 "Avg Bill (Rs)"], rows)


def expense_category_report():
    print_header("EXPENSE CATEGORY REPORT")
    rows = fetch_all("SELECT category, COUNT(*), SUM(amount), AVG(amount) "
                     "FROM expenses GROUP BY category ORDER BY SUM(amount) DESC")
    print_table(["Category", "Entries", "Total (Rs)", "Average (Rs)"], rows)


def monthly_expense_report():
    print_header("MONTHLY EXPENSE REPORT")
    rows = fetch_all("SELECT strftime('%Y-%m', expense_date) AS ym, COUNT(*), SUM(amount) "
                     "FROM expenses GROUP BY ym ORDER BY ym")
    print_table(["Month", "Entries", "Total (Rs)"], rows)


def income_vs_expense_report():
    print_header("TOTAL INCOME VERSUS TOTAL EXPENSES")
    income = fetch_one("SELECT COALESCE(SUM(amount_paid), 0) FROM payments")[0]
    expenses = fetch_one("SELECT COALESCE(SUM(amount), 0) FROM expenses")[0]
    balance = income - expenses
    print(f"  Total income (maintenance collected) : Rs. {income:>12,.2f}")
    print(f"  Total expenses                       : Rs. {expenses:>12,.2f}")
    print("  " + "-" * 52)
    label = "Surplus" if balance >= 0 else "Deficit"
    print(f"  {label:<37}: Rs. {abs(balance):>12,.2f}")


def outstanding_summary_report():
    print_header("OUTSTANDING MAINTENANCE SUMMARY")
    billed, collected = fetch_one(
        "SELECT COALESCE(SUM(m.amount), 0), COALESCE(SUM(p.paid), 0) "
        "FROM maintenance m " + PAID_PER_BILL)
    outstanding = billed - collected
    percent = (collected / billed * 100) if billed else 0
    print(f"  Total billed          : Rs. {billed:,.2f}")
    print(f"  Total collected       : Rs. {collected:,.2f}")
    print(f"  Total outstanding     : Rs. {outstanding:,.2f}")
    print(f"  Collection percentage : {percent:.1f}%\n")
    rows = fetch_all(f"SELECT status, COUNT(*), SUM(pending) FROM ({bill_query()}) "
                     "GROUP BY status ORDER BY status")
    print_table(["Status", "Bills", "Pending (Rs)"], rows)


def reports_menu():
    run_menu("REPORTS AND ANALYTICS", [
        ("Monthly maintenance collection report", monthly_collection_report),
        ("Annual maintenance collection report", annual_collection_report),
        ("Pending dues report", pending_dues_report),
        ("Flat-wise maintenance report", flatwise_report),
        ("Expense category report", expense_category_report),
        ("Monthly expense report", monthly_expense_report),
        ("Total income versus total expenses", income_vs_expense_report),
        ("Outstanding maintenance summary", outstanding_summary_report),
    ])


# ----------------------------------------------------------------------------
# 15. MAIN PROGRAM
# ----------------------------------------------------------------------------

def dashboard_submenu():
    run_menu("DASHBOARD", [
        ("Show dashboard summary", show_dashboard),
        ("Load optional sample data (empty database only)", load_sample_data),
    ])


def main():
    create_tables()                       # database + tables are created on first run
    print_header("SOCIETY MAINTENANCE MANAGEMENT SYSTEM")
    if fetch_one("SELECT COUNT(*) FROM flats")[0] == 0:
        print_info("The database is empty.")
        load_sample_data()                # asks the user first

    menu_actions = {
        "1": dashboard_submenu,
        "2": flat_menu,
        "3": resident_menu,
        "4": maintenance_menu,
        "5": payment_menu,
        "6": expense_menu,
        "7": complaint_menu,
        "8": reports_menu,
    }
    while True:
        print("\n" + LINE)
        print("SOCIETY MAINTENANCE MANAGEMENT SYSTEM".center(len(LINE)))
        print(LINE + "\n")
        print("1. Dashboard")
        print("2. Flat Management")
        print("3. Resident Management")
        print("4. Maintenance Management")
        print("5. Payment Management")
        print("6. Expense Management")
        print("7. Complaint Management")
        print("8. Reports and Analytics")
        print("9. Exit")
        print("\n" + LINE)
        choice = input("Enter your choice: ").strip()
        if choice == "9":
            print("\nThank you for using the Society Maintenance Management System.")
            break
        action = menu_actions.get(choice)
        if action:
            action()
        else:
            print_error("Invalid choice. Please enter a number from 1 to 9.")


if __name__ == "__main__":
    try:
        main()
    except (KeyboardInterrupt, EOFError):
        print("\n\nProgram closed by the user. Goodbye!")
