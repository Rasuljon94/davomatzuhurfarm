import sqlite3
from datetime import datetime
import pandas as pd

from sqlite3 import Connection
conn: Connection = sqlite3.connect("davomat.db")
cursor = conn.cursor()

def create_tables():
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            telegram_id INTEGER UNIQUE,
            name TEXT,
            surname TEXT,
            birthdate TEXT,
            branch TEXT
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS attendance (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            full_name TEXT,
            time TEXT,
            date TEXT,
            branch TEXT,
            latitude REAL,
            longitude REAL,
            late_minutes INTEGER DEFAULT 0,
            early_minutes INTEGER DEFAULT 0,
            action_type TEXT,
            note TEXT
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS comments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            text TEXT,
            date TEXT,
            time TEXT
        )
    """)
    conn.commit()

def register_user(telegram_id, name, surname, birthdate, branch):
    cursor.execute("""
        INSERT OR IGNORE INTO users (telegram_id, name, surname, birthdate, branch)
        VALUES (?, ?, ?, ?, ?)
    """, (telegram_id, name, surname, birthdate, branch))
    conn.commit()

def is_user_registered(telegram_id):
    cursor.execute("SELECT id FROM users WHERE telegram_id = ?", (telegram_id,))
    return cursor.fetchone() is not None

def get_user_branch(telegram_id):
    cursor.execute("SELECT branch FROM users WHERE telegram_id = ?", (telegram_id,))
    row = cursor.fetchone()
    return row[0] if row else None

def get_user_name(telegram_id):
    cursor.execute("SELECT name, surname FROM users WHERE telegram_id = ?", (telegram_id,))
    row = cursor.fetchone()
    return f"{row[0]} {row[1]}" if row else "Noma'lum"

def has_checked_in_today(telegram_id, action_type):
    today = datetime.now().strftime("%d.%m.%Y")
    cursor.execute("""
        SELECT a.id FROM attendance a
        JOIN users u ON a.user_id = u.id
        WHERE u.telegram_id = ? AND a.action_type = ? AND a.date = ?
    """, (telegram_id, action_type, today))
    return cursor.fetchone() is not None

def log_attendance(telegram_id, action_type, time, date, branch, location,
                   late_minutes=0, early_minutes=0, full_name="", note=""):
    cursor.execute("SELECT id FROM users WHERE telegram_id = ?", (telegram_id,))
    user = cursor.fetchone()
    if not user:
        return
    user_id = user[0]
    cursor.execute("""
        INSERT INTO attendance (user_id, full_name, time, date, branch, latitude, longitude,
        late_minutes, early_minutes, action_type, note)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        user_id, full_name, time, date, branch,
        location[0], location[1],
        late_minutes, early_minutes,
        action_type, note
    ))
    conn.commit()

def save_note_to_today_attendance(telegram_id: int, note: str):
    today = datetime.now().strftime("%d.%m.%Y")
    cursor.execute("""
        UPDATE attendance
        SET note = ?
        WHERE user_id = (
            SELECT id FROM users WHERE telegram_id = ?
        ) AND date = ? AND action_type = 'check_in'
    """, (note, telegram_id, today))
    conn.commit()

def log_comment(telegram_id, text, date, time):
    cursor.execute("SELECT id FROM users WHERE telegram_id = ?", (telegram_id,))
    user = cursor.fetchone()
    if user:
        user_id = user[0]
        cursor.execute("""
            INSERT INTO comments (user_id, text, date, time)
            VALUES (?, ?, ?, ?)
        """, (user_id, text, date, time))
        conn.commit()

def get_birthdays_today():
    today = datetime.now().strftime("%d.%m")
    cursor.execute("""
        SELECT name, surname, telegram_id FROM users
        WHERE substr(birthdate, 1, 5) = ?
    """, (today,))
    return cursor.fetchall()

def update_user_fields(telegram_id, fields: dict):
    columns = ", ".join([f"{k} = ?" for k in fields.keys()])
    values = list(fields.values())
    values.append(telegram_id)
    cursor.execute(f"""
        UPDATE users SET {columns} WHERE telegram_id = ?
    """, values)
    conn.commit()

def delete_user(telegram_id):
    cursor.execute("DELETE FROM users WHERE telegram_id = ?", (telegram_id,))
    conn.commit()

def export_users_to_excel():
    df = pd.read_sql_query("SELECT * FROM users", conn)
    path = "users_export.xlsx"
    df.to_excel(path, index=False)
    return path

def export_attendance_yearly():
    import pandas as pd
    from datetime import datetime

    # Joriy yilni olish
    current_year = datetime.now().strftime("%Y")

    # attendance jadvalidagi full_name ustunini olishga o'zgardi
    query = """
        SELECT
            a.full_name        AS full_name,
            a.branch           AS branch,
            a.date             AS date,
            a.time             AS time,
            a.action_type      AS action_type,
            a.late_minutes     AS late_minutes,
            a.early_minutes    AS early_minutes,
            a.note             AS note
        FROM attendance AS a
        WHERE substr(a.date, 7, 4) = ?
        ORDER BY a.date ASC, a.time ASC
    """

    # So‘rovni bajarish
    df = pd.read_sql_query(query, conn, params=(current_year,))

    # Excelga saqlash
    path = f"attendance_{current_year}.xlsx"
    df.to_excel(path, index=False)
    return path


