import sqlite3
from datetime import datetime, timedelta
from flask import Flask, render_template, request, jsonify

app = Flask(__name__)
DB_NAME = "biotech_lab_access.db"

@app.route('/')
def index():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT id, card_uid, employee_name, timestamp, gate_name, status FROM access_logs ORDER BY id DESC LIMIT 50")
    recent_logs = cursor.fetchall()
    conn.close()
    return render_template("dashboard.html", recent_logs=recent_logs)

@app.route('/api/stats')
def api_stats():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM access_logs")
    total = cursor.fetchone()[0] or 1
    cursor.execute("SELECT COUNT(*) FROM access_logs WHERE status='ALLOWED'")
    allowed = cursor.fetchone()[0] or 0
    denied = total - allowed

    cursor.execute("SELECT STRFTIME('%H', timestamp) as hr, COUNT(*) as cnt FROM access_logs GROUP BY hr")
    heatmap_raw = {int(r['hr']): r['cnt'] for r in cursor.fetchall()}
    heatmap_data = [heatmap_raw.get(h, 0) for h in range(24)]

    line_labels, line_allowed, line_denied = [], [], []
    for i in range(6, -1, -1):
        d = (datetime.now() - timedelta(days=i)).strftime('%Y-%m-%d')
        line_labels.append(d)
        cursor.execute("SELECT COUNT(*) FROM access_logs WHERE timestamp LIKE ? AND status='ALLOWED'", (d+'%',))
        line_allowed.append(cursor.fetchone()[0])
        cursor.execute("SELECT COUNT(*) FROM access_logs WHERE timestamp LIKE ? AND status!='ALLOWED'", (d+'%',))
        line_denied.append(cursor.fetchone()[0])

    cursor.execute("SELECT card_uid, full_name, role FROM employees WHERE is_active=0")
    blocked = [{"card_uid": r["card_uid"], "name": r["full_name"], "role": r["role"], "reason": "3 Wrong PIN attempts"} for r in cursor.fetchall()]

    conn.close()
    return jsonify({
        "total": total, "allowed": allowed, "denied": denied,
        "failure_rate": round((denied/total)*100, 1), "success_rate": round((allowed/total)*100, 1),
        "heatmap": heatmap_data, "blocked_analysis": None,
        "line": {"labels": line_labels, "allowed": line_allowed, "denied": line_denied},
        "blocked_employees": blocked
    })

@app.route('/unblock', methods=['POST'])
def unblock():
    card_uid = request.form.get('card_uid')
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("UPDATE employees SET is_active=1, failed_attempts=0 WHERE card_uid=?", (card_uid,))
    conn.commit()
    conn.close()
    return jsonify({"status": "OK"})

@app.route('/scan', methods=['POST'])
def scan_card():
    data = request.json or {}
    card_uid = data.get('uid', '').strip().upper()
    submitted_pin = data.get('pin', '').strip()
    
    print(f"--- [SCAN RECEIVED] Card: {card_uid} | PIN: {submitted_pin} ---")

    if not card_uid:
        return 'U'

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    gate = "Biotech Lab Main Gate"

    cursor.execute("SELECT full_name, pin_code, is_active, failed_attempts FROM employees WHERE card_uid = ?", (card_uid,))
    user = cursor.fetchone()

    if not user:
        cursor.execute("INSERT INTO access_logs (card_uid, employee_name, timestamp, gate_name, status) VALUES (?,?,?,?,?)", (card_uid, "Unknown Stranger", current_time, gate, "UNKNOWN_CARD"))
        conn.commit()
        conn.close()
        return 'U'

    name, correct_pin, is_active, failed_attempts = user

    if is_active == 0:
        cursor.execute("INSERT INTO access_logs (card_uid, employee_name, timestamp, gate_name, status) VALUES (?,?,?,?,?)", (card_uid, name, current_time, gate, "BLOCKED_CARD"))
        conn.commit()
        conn.close()
        return 'L'

    # درخواست پین کد (مرحله اول)
    if not submitted_pin:
        conn.close()
        return 'P'

    # تایید نهایی پین کد (مرحله دوم)
    if submitted_pin == correct_pin:
        cursor.execute("UPDATE employees SET failed_attempts=0 WHERE card_uid=?", (card_uid,))
        cursor.execute("INSERT INTO access_logs (card_uid, employee_name, timestamp, gate_name, status) VALUES (?,?,?,?,?)", (card_uid, name, current_time, gate, "ALLOWED"))
        conn.commit()
        conn.close()
        return 'A'
    else:
        new_attempts = failed_attempts + 1
        if new_attempts >= 3:
            cursor.execute("UPDATE employees SET is_active=0, failed_attempts=? WHERE card_uid=?", (new_attempts, card_uid))
            cursor.execute("INSERT INTO access_logs (card_uid, employee_name, timestamp, gate_name, status) VALUES (?,?,?,?,?)", (card_uid, name, current_time, gate, "CARD_LOCKED"))
            conn.commit()
            conn.close()
            return 'L'
        else:
            cursor.execute("UPDATE employees SET failed_attempts=? WHERE card_uid=?", (new_attempts, card_uid))
            cursor.execute("INSERT INTO access_logs (card_uid, employee_name, timestamp, gate_name, status) VALUES (?,?,?,?,?)", (card_uid, name, current_time, gate, "DENIED_PIN"))
            conn.commit()
            conn.close()
            return 'W'

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)