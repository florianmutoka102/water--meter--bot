import sqlite3
from datetime import datetime

DB_PATH = "water_meter.db"

def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_connection()
    cursor = conn.cursor()

    # Customers table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS customers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            account_number TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL,
            phone TEXT,
            address TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Meter readings table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS meter_readings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            account_number TEXT NOT NULL,
            reading INTEGER NOT NULL,
            date TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (account_number) REFERENCES customers(account_number)
        )
    """)

    # Insert sample customers for testing
    sample_customers = [
        ("WS001", "Juma Mwangi", "+255712345678", "Mtaa wa Mji"),
        ("WS002", "Amina Hassan", "+255787654321", "Kariakoo"),
        ("WS003", "Peter Kimaro", "+255756789012", "Sinza"),
    ]
    for acc, name, phone, addr in sample_customers:
        cursor.execute("""
            INSERT OR IGNORE INTO customers (account_number, name, phone, address)
            VALUES (?, ?, ?, ?)
        """, (acc, name, phone, addr))

    conn.commit()
    conn.close()
    print("✅ Database initialized successfully!")

def get_customer(account_number):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM customers WHERE account_number = ?",
        (account_number.upper(),)
    )
    row = cursor.fetchone()
    conn.close()
    if row:
        return dict(row)
    return None

def save_reading(account_number, reading):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO meter_readings (account_number, reading, date)
        VALUES (?, ?, ?)
    """, (account_number.upper(), reading, datetime.now().strftime("%Y-%m-%d %H:%M")))
    conn.commit()
    conn.close()

def get_history(account_number):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT reading, date FROM meter_readings
        WHERE account_number = ?
        ORDER BY id DESC
        LIMIT 10
    """, (account_number.upper(),))
    rows = cursor.fetchall()
    conn.close()
    return [{"reading": row["reading"], "date": row["date"]} for row in rows]

def calculate_bill(account_number):
    TARIFF = 500  # TZS per m³
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT reading FROM meter_readings
        WHERE account_number = ?
        ORDER BY id DESC
        LIMIT 2
    """, (account_number.upper(),))
    rows = cursor.fetchall()
    conn.close()

    if len(rows) < 2:
        return None

    curr = rows[0]["reading"]
    prev = rows[1]["reading"]
    units = curr - prev

    if units < 0:
        units = 0

    total = units * TARIFF
    return {
        "curr": curr,
        "prev": prev,
        "units": units,
        "total": total
    }
