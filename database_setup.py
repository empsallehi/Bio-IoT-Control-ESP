import sqlite3
import random
from datetime import datetime, timedelta

def build_advanced_system():
    conn = sqlite3.connect("biotech_lab_access.db")
    cursor = conn.cursor()

    # پاک کردن جدول‌های قبلی در صورت وجود برای ثبت دیتای تمیز جدید
    cursor.execute("DROP TABLE IF EXISTS employees")
    cursor.execute("DROP TABLE IF EXISTS access_logs")

    # ۱. ساخت جدول کارمندان دقیقاً طبق فیلدهای عکس ارسالی
    cursor.execute("""
    CREATE TABLE employees (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        national_id TEXT UNIQUE,
        personnel_code TEXT,
        full_name TEXT,
        role TEXT,
        card_uid TEXT,
        pin_code TEXT,
        failed_attempts INTEGER DEFAULT 0,
        is_active INTEGER DEFAULT 1
    )""")

    # ۲. ساخت جدول گزارشات تردد (Logs)
    cursor.execute("""
    CREATE TABLE access_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        card_uid TEXT,
        employee_name TEXT,
        timestamp TEXT,
        gate_name TEXT,
        status TEXT
    )""")

    # ساخت ایندکس زمانی برای بالا بردن سرعت چارت‌های داشبورد
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_timestamp ON access_logs(timestamp);")

    # لیست پرسنل اصلی آزمایشگاه بیوتکنولوژی طبق ساختار شما
    staff_list = [
        ('1112223334', '980101', 'Khatere Salehi', 'Lab Manager', '01020304', '1234'),
        ('2223334445', '980102', 'Dr. Arvin Rad', 'Senior Geneticist', '11223344', '5566'),
        ('3334445556', '980103', 'Maryam Amiri', 'Cell Culture Tech', '55667788', '7788'),
        ('4444556667', '980104', 'Ali Davoudi', 'Intern', 'AABBCCDD', '0000'),
        ('5556667778', '980105', 'Dr. Sara Mahdavi', 'Bioinformatician', 'C0FFEE99', '1122')
    ]
    
    for emp in staff_list:
        cursor.execute("""
            INSERT INTO employees (national_id, personnel_code, full_name, role, card_uid, pin_code) 
            VALUES (?, ?, ?, ?, ?, ?)
        """, emp)
    conn.commit()

    # 📊 تولید هوشمند لاگ‌های فرضی سال ۲۰۲۶ برای تحلیل داده و نمودارهای داشبورد
    print("Generating comprehensive records for analytical charts...")
    start_date = datetime(2026, 1, 1)
    end_date = datetime.now()
    delta_days = (end_date - start_date).days
    
    gates = ["Biotech Lab Main Gate", "Genetics Cleanroom", "Bioinformatics Unit"]
    statuses = ["ALLOWED", "ALLOWED", "ALLOWED", "DENIED_PIN", "UNKNOWN_CARD"]

    logs_batch = []
    for d in range(delta_days + 1):
        curr_date = start_date + timedelta(days=d)
        scans = random.randint(5, 12) if curr_date.weekday() >= 5 else random.randint(25, 45)
        
        for _ in range(scans):
            card = random.choice(['01020304', '11223344', '55667788', 'AABBCCDD', 'C0FFEE99', '99887766'])
            hour = random.choice([8, 8, 9, 12, 14, 17, 17, random.randint(0,23)])
            fake_time = curr_date.replace(hour=hour, minute=random.randint(0,59), second=random.randint(0,59)).strftime("%Y-%m-%d %H:%M:%S")
            
            cursor.execute("SELECT full_name, is_active FROM employees WHERE card_uid=?", (card,))
            emp_status = cursor.fetchone()
            
            if emp_status:
                name = emp_status[0]
                status = random.choice(statuses) if emp_status[1] == 1 else "BLOCKED_CARD"
            else:
                name = "Unauthorized Unknown"
                status = "UNKNOWN_CARD"
                
            logs_batch.append((card, name, fake_time, random.choice(gates), status))

    cursor.executemany("INSERT INTO access_logs (card_uid, employee_name, timestamp, gate_name, status) VALUES (?,?,?,?,?)", logs_batch)
    conn.commit()
    conn.close()
    print("Database built successfully!")

if __name__ == "__main__":
    build_advanced_system()