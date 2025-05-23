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
            start_time TEXT,
            end_time TEXT,
            address TEXT,
            phone TEXT
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
        CREATE TABLE IF NOT EXISTS allowed_users (
            telegram_id INTEGER PRIMARY KEY
        )
    """)


    conn.commit()

def clear_user_fields(telegram_id: int):
    cursor.execute("""
        UPDATE users
        SET name = NULL,
            surname = NULL,
            birthdate = NULL,
            start_time = NULL,
            end_time = NULL,
            address = NULL,
            phone = NULL
        WHERE telegram_id = ?
    """, (telegram_id,))
    conn.commit()


def get_all_users():
    cursor.execute("""
        SELECT telegram_id, name, surname 
        FROM users
        WHERE name IS NOT NULL AND surname IS NOT NULL
    """)
    rows = cursor.fetchall()
    return [{"telegram_id": r[0], "name": r[1], "surname": r[2]} for r in rows]



def add_allowed_user(telegram_id: int):
    cursor.execute("INSERT OR IGNORE INTO allowed_users (telegram_id) VALUES (?)", (telegram_id,))
    conn.commit()

def is_user_allowed(telegram_id: int) -> bool:
    cursor.execute("SELECT 1 FROM allowed_users WHERE telegram_id = ?", (telegram_id,))
    return cursor.fetchone() is not None



def register_user(telegram_id, name, surname, birthdate, start_time, end_time, address, phone):
    cursor.execute("SELECT id FROM users WHERE telegram_id = ?", (telegram_id,))
    exists = cursor.fetchone()

    if exists:
        # 🔄 Mavjud bo‘lsa, yangilaydi
        cursor.execute("""
            UPDATE users
            SET name = ?, surname = ?, birthdate = ?, start_time = ?, end_time = ?, address = ?, phone = ?
            WHERE telegram_id = ?
        """, (name, surname, birthdate, start_time, end_time, address, phone, telegram_id))
    else:
        # ➕ Yo‘q bo‘lsa, yangi foydalanuvchi qo‘shadi
        cursor.execute("""
            INSERT INTO users (telegram_id, name, surname, birthdate, start_time, end_time, address, phone)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (telegram_id, name, surname, birthdate, start_time, end_time, address, phone))

    conn.commit()



def is_user_registered(telegram_id):
    cursor.execute("""
        SELECT name, surname FROM users WHERE telegram_id = ?
    """, (telegram_id,))
    row = cursor.fetchone()
    if not row:
        return False
    name, surname = row
    return bool(name and surname)  # Ikkalasi ham bo‘sh bo‘lmasligi kerak


def get_user_branch(telegram_id):
    cursor.execute("SELECT branch FROM users WHERE telegram_id = ?", (telegram_id,))
    row = cursor.fetchone()
    return row[0] if row else None

# def get_user_name(telegram_id):
#     cursor.execute("SELECT name, surname FROM users WHERE telegram_id = ?", (telegram_id,))
#     row = cursor.fetchone()
#     return f"{row[0]} {row[1]}" if row else "Noma'lum"
def get_user_name(telegram_id):
    cursor.execute("SELECT name, surname FROM users WHERE telegram_id = ?", (telegram_id,))
    row = cursor.fetchone()
    if row and row[0] and row[1]:
        return f"{row[0]} {row[1]}"
    return "❌ Ro‘yxatdan o‘tmagan"


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
    now = datetime.now().strftime("%H:%M")

    # Foydalanuvchi ma'lumotlari
    cursor.execute("SELECT id, name, surname FROM users WHERE telegram_id = ?", (telegram_id,))
    row = cursor.fetchone()
    if not row:
        return
    user_id, name, surname = row
    branch =  "-"  # ← Bo‘sh bo‘lsa, "-" belgilaymiz
    full_name = f"{name} {surname}"

    # 1. Avval 'ishdan_ketdi' yozuvi borligini tekshirish
    cursor.execute("""
        SELECT id FROM attendance
        WHERE user_id = ? AND date = ? AND action_type = 'ishdan_ketdi'
    """, (user_id, today))
    row = cursor.fetchone()
    if row:
        attendance_id = row[0]
        cursor.execute("""
            UPDATE attendance
            SET note = CASE
                WHEN note IS NULL OR note = '' THEN ?
                ELSE note || ' | ' || ?
            END
            WHERE id = ?
        """, (note, note, attendance_id))
        conn.commit()
        return

    # 2. 'ishga_keldi' yozuvi borligini tekshirish
    cursor.execute("""
        SELECT id FROM attendance
        WHERE user_id = ? AND date = ? AND action_type = 'ishga_keldi'
    """, (user_id, today))
    row = cursor.fetchone()
    if row:
        attendance_id = row[0]
        cursor.execute("""
            UPDATE attendance
            SET note = CASE
                WHEN note IS NULL OR note = '' THEN ?
                ELSE note || ' | ' || ?
            END
            WHERE id = ?
        """, (note, note, attendance_id))
        conn.commit()
        return

    # 3. Agar izoh qatori bor bo‘lsa → unga qo‘shamiz
    cursor.execute("""
        SELECT id FROM attendance
        WHERE user_id = ? AND date = ? AND action_type = 'izoh'
    """, (user_id, today))
    row = cursor.fetchone()
    if row:
        attendance_id = row[0]
        cursor.execute("""
            UPDATE attendance
            SET note = CASE
                WHEN note IS NULL OR note = '' THEN ?
                ELSE note || ' | ' || ?
            END,
            time = ?  -- vaqtni yangilab qo‘yish ham mumkin
            WHERE id = ?
        """, (note, note, now, attendance_id))
        conn.commit()
        return

    # 4. Umuman yozuv yo‘q bo‘lsa → yangi qator
    cursor.execute("""
        INSERT INTO attendance (
            user_id, full_name, time, date, branch,
            latitude, longitude, late_minutes, early_minutes, action_type, note
        ) VALUES (?, ?, ?, ?, ?, 0, 0, 0, 0, 'izoh', ?)
    """, (
        user_id, full_name, now, today, branch, note
    ))
    conn.commit()



def get_birthdays_today():
    today = datetime.now().strftime("%d.%m")
    cursor.execute("""
        SELECT name, surname, telegram_id FROM users
        WHERE substr(birthdate, 1, 5) = ?
    """, (today,))
    return cursor.fetchall()

def delete_user_fields(telegram_id: int):
    cursor.execute("DELETE FROM users WHERE telegram_id = ?", (telegram_id,))
    conn.commit()


def delete_user(telegram_id):
    cursor.execute("SELECT id FROM users WHERE telegram_id = ?", (telegram_id,))
    row = cursor.fetchone()
    if not row:
        return
    user_id = row[0]

    # ❌ attendance jadvalidan hech narsa o‘chirilmaydi
    # 🔄 Faqat users va allowed_users dan o‘chiramiz
    cursor.execute("DELETE FROM users WHERE id = ?", (user_id,))
    remove_allowed_user(telegram_id)

    conn.commit()


def remove_allowed_user(telegram_id: int):
    cursor.execute("DELETE FROM allowed_users WHERE telegram_id = ?", (telegram_id,))
    conn.commit()


def load_allowed_users():
    cursor.execute("SELECT telegram_id FROM allowed_users")
    return [row[0] for row in cursor.fetchall()]



def export_users_to_excel():
    df = pd.read_sql_query("SELECT * FROM users", conn)
    path = "users_export.xlsx"
    df.to_excel(path, index=False)
    return path


def export_attendance_yearly():
    current_year = datetime.now().strftime("%Y")

    query = """
           SELECT
               u.id              AS "Hodim ID",
               u.telegram_id     AS "Telegram ID",
               a.full_name       AS "F.I.Sh.",
               a.branch          AS "Filial",
               a.date            AS "Sana",
               a.time            AS "Vaqt",
               a.action_type     AS "Holat",
               a.late_minutes    AS "Kechikish (daqiqa)",
               a.early_minutes   AS "Erta ketish (daqiqa)",
               a.note            AS "Izoh",
               u.start_time      AS "Ish boshlanishi",
               u.end_time        AS "Ish tugashi"
           FROM attendance a
           JOIN users u ON a.user_id = u.id
           WHERE substr(a.date, 7, 4) = ?
           ORDER BY a.full_name, a.date, a.time
       """

    df = pd.read_sql_query(query, conn, params=(current_year,))

    if df.empty:
        return None

    # ⏱ Kechikish va erta ketishni soat:daqiqaga o‘tkazish
    def format_minutes(mins):
        if not mins or mins == 0:
            return ""
        hours = mins // 60
        minutes = mins % 60
        return f"{hours}:{str(minutes).zfill(2)}"

    df["Kechikish"] = df["Kechikish (daqiqa)"].apply(format_minutes)
    df["Erta ketish"] = df["Erta ketish (daqiqa)"].apply(format_minutes)

    df.drop(columns=["Kechikish (daqiqa)", "Erta ketish (daqiqa)"], inplace=True)

    # ✅ Ustunlarni tartiblaymiz
    df = df[[  # tartib
        "Hodim ID", "Telegram ID", "F.I.Sh.", "Filial", "Sana", "Vaqt", "Holat",
        "Ish boshlanishi", "Ish tugashi", "Kechikish", "Erta ketish", "Izoh"
    ]]

    # 📊 Umumiy statistika hisoblash
    def parse_minutes(val):
        try:
            if pd.isna(val) or not val.strip():
                return 0
            h, m = val.split(":")
            return int(h) * 60 + int(m)
        except:
            return 0

    df_keldi = df[df["Holat"] == "ishga_keldi"].copy()
    df_ketdi = df[df["Holat"] == "ishdan_ketdi"].copy()

    summary = (
        df_keldi
        .groupby(["Hodim ID", "F.I.Sh."])
        .agg(
            Ish_kunlari=("Sana", "nunique"),
            Umumiy_kechikish=("Kechikish", lambda x: sum(parse_minutes(p) for p in x))
        )
        .reset_index()
    )

    erta = (
        df_ketdi
        .groupby(["Hodim ID", "F.I.Sh."])
        .agg(Umumiy_erta_ketish=("Erta ketish", lambda x: sum(parse_minutes(p) for p in x)))
        .reset_index()
    )

    summary = pd.merge(summary, erta, on=["Hodim ID", "F.I.Sh."], how="left").fillna(0)

    def format_total(mins):
        try:
            mins = int(mins)
            if mins <= 0:
                return "0:00"
            return f"{mins // 60}:{str(mins % 60).zfill(2)}"
        except:
            return "0:00"

    summary["Umumiy kechikish"] = summary["Umumiy_kechikish"].apply(format_total)
    summary["Umumiy erta ketish"] = summary["Umumiy_erta_ketish"].apply(format_total)
    summary.drop(columns=["Umumiy_kechikish", "Umumiy_erta_ketish"], inplace=True)

    # 📁 Excelga yozish
    file_path = f"attendance_{current_year}.xlsx"
    writer = pd.ExcelWriter(file_path, engine="xlsxwriter")

    df.to_excel(writer, index=False, sheet_name="Davomat")
    summary.to_excel(writer, index=False, sheet_name="Yakuniy statistikalar")

    # 📐 Ustunlarga mos kenglik
    for sheet in writer.sheets:
        worksheet = writer.sheets[sheet]
        data = df if sheet == "Davomat" else summary
        for i, col in enumerate(data.columns):
            max_len = max(data[col].astype(str).map(len).max(), len(col))
            worksheet.set_column(i, i, max_len + 2)

    writer.close()
    return file_path


def export_attendance_monthly():
    now = datetime.now()
    current_month = f"{now.month:02d}.{now.year}"

    query = """
        SELECT
            u.id              AS "Hodim ID",
            u.telegram_id     AS "Telegram ID",
            a.full_name       AS "F.I.Sh.",
            a.branch          AS "Filial",
            a.date            AS "Sana",
            a.time            AS "Vaqt",
            a.action_type     AS "Holat",
            a.late_minutes    AS "Kechikish (daqiqa)",
            a.early_minutes   AS "Erta ketish (daqiqa)",
            a.note            AS "Izoh",
            u.start_time      AS "Ish boshlanishi",
            u.end_time        AS "Ish tugashi"
        FROM attendance a
        JOIN users u ON a.user_id = u.id
        WHERE substr(a.date, 4, 7) = ?
        ORDER BY a.full_name, a.date, a.time
    """

    df = pd.read_sql_query(query, conn, params=(current_month,))

    if df.empty:
        return None

    # ⏱ format: 15 -> 0:15, 75 -> 1:15
    def format_minutes(mins):
        if not mins or mins == 0:
            return ""
        hours = mins // 60
        minutes = mins % 60
        return f"{hours}:{str(minutes).zfill(2)}"

    df["Kechikish"] = df["Kechikish (daqiqa)"].apply(format_minutes)
    df["Erta ketish"] = df["Erta ketish (daqiqa)"].apply(format_minutes)

    df.drop(columns=["Kechikish (daqiqa)", "Erta ketish (daqiqa)"], inplace=True)

    df = df[[  # tartib
        "Hodim ID", "Telegram ID", "F.I.Sh.", "Filial", "Sana", "Vaqt", "Holat",
        "Ish boshlanishi", "Ish tugashi", "Kechikish", "Erta ketish", "Izoh"
    ]]

    # 📊 Yakuniy statistikalar
    def parse_minutes(val):
        try:
            if pd.isna(val) or not val.strip():
                return 0
            h, m = val.split(":")
            return int(h) * 60 + int(m)
        except:
            return 0

    df_keldi = df[df["Holat"] == "ishga_keldi"].copy()
    df_ketdi = df[df["Holat"] == "ishdan_ketdi"].copy()

    summary = (
        df_keldi
        .groupby(["Hodim ID", "F.I.Sh."])
        .agg(
            Ish_kunlari=("Sana", "nunique"),
            Umumiy_kechikish=("Kechikish", lambda x: sum(parse_minutes(p) for p in x))
        )
        .reset_index()
    )

    erta = (
        df_ketdi
        .groupby(["Hodim ID", "F.I.Sh."])
        .agg(Umumiy_erta_ketish=("Erta ketish", lambda x: sum(parse_minutes(p) for p in x)))
        .reset_index()
    )

    summary = pd.merge(summary, erta, on=["Hodim ID", "F.I.Sh."], how="left").fillna(0)

    def format_total(mins):
        try:
            mins = int(mins)
            if mins <= 0:
                return "0:00"
            return f"{mins // 60}:{str(mins % 60).zfill(2)}"
        except:
            return "0:00"

    summary["Umumiy kechikish"] = summary["Umumiy_kechikish"].apply(format_total)
    summary["Umumiy erta ketish"] = summary["Umumiy_erta_ketish"].apply(format_total)
    summary.drop(columns=["Umumiy_kechikish", "Umumiy_erta_ketish"], inplace=True)

    # 📁 Excelga yozish
    file_path = f"attendance_{now.year}_{now.month:02d}.xlsx"
    writer = pd.ExcelWriter(file_path, engine="xlsxwriter")

    df.to_excel(writer, index=False, sheet_name="Davomat")
    summary.to_excel(writer, index=False, sheet_name="Yakuniy statistikalar")

    # 📐 Ustunlarga mos kenglik
    for sheet in writer.sheets:
        worksheet = writer.sheets[sheet]
        data = df if sheet == "Davomat" else summary
        for i, col in enumerate(data.columns):
            max_len = max(data[col].astype(str).map(len).max(), len(col))
            worksheet.set_column(i, i, max_len + 2)

    writer.close()
    return file_path

def export_attendance_previous_month():
    today = datetime.now()
    year = today.year
    month = today.month - 1 if today.month > 1 else 12
    if today.month == 1:
        year -= 1  # Agar yanvar bo‘lsa, yil kamayadi

    target = f"{month:02d}.{year}"

    query = """
        SELECT
            u.id              AS "Hodim ID",
            u.telegram_id     AS "Telegram ID",
            u.start_time      AS "Boshlanish vaqti",
            u.end_time        AS "Tugash vaqti",
            a.full_name       AS "F.I.Sh.",
            a.branch          AS "Filial",
            a.date            AS "Sana",
            a.time            AS "Vaqt",
            a.action_type     AS "Holat",
            a.late_minutes    AS "Kechikish (daqiqa)",
            a.early_minutes   AS "Erta ketish (daqiqa)",
            a.note            AS "Izoh"
        FROM attendance a
        JOIN users u ON a.user_id = u.id
        WHERE substr(a.date, 4, 7) = ?
        ORDER BY a.full_name, a.date, a.time
    """

    df = pd.read_sql_query(query, conn, params=(target,))
    if df.empty:
        return None

    # Vaqtlarni formatlash
    def format_minutes(mins):
        if not mins or mins == 0:
            return ""
        hours = mins // 60
        minutes = mins % 60
        return f"{hours}:{str(minutes).zfill(2)}"

    df["Kechikish"] = df["Kechikish (daqiqa)"].apply(format_minutes)
    df["Erta ketish"] = df["Erta ketish (daqiqa)"].apply(format_minutes)
    df.drop(columns=["Kechikish (daqiqa)", "Erta ketish (daqiqa)"], inplace=True)

    df = df[[  # ustun tartibi
        "Hodim ID", "Telegram ID", "F.I.Sh.", "Filial", "Sana", "Vaqt", "Holat",
        "Boshlanish vaqti", "Tugash vaqti", "Kechikish", "Erta ketish", "Izoh"
    ]]

    file_path = f"attendance_{year}_{month:02d}.xlsx"
    writer = pd.ExcelWriter(file_path, engine="xlsxwriter")

    df.to_excel(writer, index=False, sheet_name="Davomat")

    # Ustun kengligi avtomatik
    worksheet = writer.sheets["Davomat"]
    for i, col in enumerate(df.columns):
        max_len = max(df[col].astype(str).map(len).max(), len(col))
        worksheet.set_column(i, i, max_len + 2)

    writer.close()
    return file_path


def get_user_work_hours(telegram_id: int):
    cursor.execute("SELECT start_time, end_time FROM users WHERE telegram_id = ?", (telegram_id,))
    row = cursor.fetchone()
    if row and row[0] and row[1]:
        return row[0], row[1]
    return None, None



