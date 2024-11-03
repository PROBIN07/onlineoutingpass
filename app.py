import sqlite3
import qrcode
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for
import os
import uuid

app = Flask(__name__, static_url_path='/static', static_folder='static')

def generate_outing_pass_url(student_name, date, reason, expiry_date, teacher, ban):
    unique_id = str(uuid.uuid4())  # 고유한 UUID 생성
    url = f"/outing_pass/{unique_id}/{student_name}/{date}/{reason}/{expiry_date}/{teacher}/{ban}"
    return url
    
def create_table():
    conn = sqlite3.connect('outing_passes.db')
    cursor = conn.cursor()
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS outing_passes (
        id INTEGER PRIMARY KEY,
        name TEXT,
        date TEXT,
        reason TEXT,
        expiry_date TEXT,
        teacher TEXT,
        ban TEXT
    )
    """)
    conn.commit()
    conn.close()
    
create_table()

class OutingPass:
    def __init__(self, name, date, reason, expiry_date, teacher, ban):
        self.name = name
        self.date = date
        self.reason = reason
        self.expiry_date = expiry_date
        self.teacher = teacher
        self.ban = ban

    def save_to_db(self):
        conn = sqlite3.connect('outing_passes.db')
        cursor = conn.cursor()
        cursor.execute("INSERT INTO outing_passes (name, date, reason, expiry_date, teacher, ban) VALUES (?, ?, ?, ?, ?, ?)",
                       (self.name, self.date, self.reason, self.expiry_date, self.teacher, self.ban))
        conn.commit()
        conn.close()

    def generate_qr_code(self):
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr_data = f"<확인용 정보>\n학반 : {self.ban}\n이름 : {self.name}\n발급 일시 : {self.date}\n사유 : {self.reason}\n외출 기한 : {self.expiry_date}\n발급 교사 : {self.teacher}\n"
        qr.add_data(qr_data)
        qr.make(fit=True)

        img = qr.make_image(fill_color="black", back_color="white")
        img.save(f"static/{self.name}_outing_pass.png")

@app.route('/')
def index():
    return render_template('create_outing_pass.html')

@app.route('/create_outing_pass', methods=['POST'])
def create_outing_pass():
    name = request.form['name']
    date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    reason = request.form['reason']
    expiry_date = request.form['expiry_date']
    teacher = request.form['teacher']
    ban = request.form['ban']

    outing_pass = OutingPass(name, date, reason, expiry_date, teacher, ban)

    outing_pass.save_to_db()

    outing_pass.generate_qr_code()

    return redirect(url_for('display_outing_pass', name=name, date=date, reason=reason, expiry_date=expiry_date, teacher=teacher, ban=ban))

@app.route('/outing_pass/<name>/<date>/<reason>/<expiry_date>/<teacher>/<ban>')
def display_outing_pass(name, date, reason, expiry_date, teacher, ban):
    return render_template('display_outing_pass.html', name=name, date=date, reason=reason, expiry_date=expiry_date, teacher=teacher, ban=ban)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))