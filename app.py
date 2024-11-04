import sqlite3
import qrcode
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, session
from werkzeug.security import generate_password_hash, check_password_hash
import os
import uuid

app = Flask(__name__, static_url_path='/static', static_folder='static')
app.secret_key = 'a_very_secret_key_12345'  # 비밀 키 설정

def create_tables():
    conn = sqlite3.connect('outing_passes.db')
    cursor = conn.cursor()
    
    # Create outing passes table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS outing_passes (
        id INTEGER PRIMARY KEY,
        name TEXT,
        date TEXT,
        reason TEXT,
        expiry_date TEXT,
        teacher TEXT,
        ban TEXT,
        unique_id TEXT
    )
    """)
    
    # Create users table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY,
        username TEXT UNIQUE,
        password TEXT
    )
    """)
    
    conn.commit()
    conn.close()

create_tables()

def add_unique_id_column():
    conn = sqlite3.connect('outing_passes.db')
    cursor = conn.cursor()
    cursor.execute("ALTER TABLE outing_passes ADD COLUMN unique_id TEXT")
    conn.commit()
    conn.close()

try:
    add_unique_id_column()
except sqlite3.OperationalError:
    pass  # 컬럼이 이미 존재하는 경우 에러 무시

class OutingPass:
    def __init__(self, name, date, reason, expiry_date, teacher, ban):
        self.name = name
        self.date = date
        self.reason = reason
        self.expiry_date = expiry_date
        self.teacher = teacher
        self.ban = ban
        self.unique_id = str(uuid.uuid4())  # 고유한 UUID 생성

    def save_to_db(self):
        conn = sqlite3.connect('outing_passes.db')
        cursor = conn.cursor()
        cursor.execute("INSERT INTO outing_passes (name, date, reason, expiry_date, teacher, ban, unique_id) VALUES (?, ?, ?, ?, ?, ?, ?)",
                       (self.name, self.date, self.reason, self.expiry_date, self.teacher, self.ban, self.unique_id))
        conn.commit()
        conn.close()

    def generate_qr_code(self):
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        url = f"http://127.0.0.1:10000/outing_pass/{self.unique_id}"  # 고유한 URL 생성
        qr_data = f"{url}\n확인용 정보\n학반 : {self.ban}\n이름 : {self.name}\n발급 일시 : {self.date}\n사유 : {self.reason}\n외출 기한 : {self.expiry_date}\n발급 교사 : {self.teacher}"
        qr.add_data(qr_data)
        qr.make(fit=True)

        img = qr.make_image(fill_color="black", back_color="white")
        img.save(f"static/{self.unique_id}_outing_pass.png")

@app.route('/')
def index():
    return render_template('login.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        conn = sqlite3.connect('outing_passes.db')
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
        user = cursor.fetchone()
        conn.close()
        
        if user and check_password_hash(user[2], password):
            session['user_id'] = user[0]
            session['username'] = user[1]
            return redirect(url_for('create_outing_pass'))
        else:
            return "Login failed"
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = generate_password_hash(request.form['password'], method='pbkdf2:sha256')  # 해싱 방법 수정
        
        conn = sqlite3.connect('outing_passes.db')
        cursor = conn.cursor()
        try:
            cursor.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, password))
            conn.commit()
        except sqlite3.IntegrityError:
            conn.close()
            return "Username already exists"
        conn.close()
        
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    session.pop('username', None)
    return redirect(url_for('index'))

@app.route('/create_outing_pass', methods=['GET', 'POST'])
def create_outing_pass():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        name = request.form['name']
        date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        reason = request.form['reason']
        expiry_date = request.form['expiry_date']
        teacher = session['username']  # 로그인한 사용자 이름을 발급 교사로 설정
        ban = request.form['ban']

        outing_pass = OutingPass(name, date, reason, expiry_date, teacher, ban)

        outing_pass.save_to_db()
        outing_pass.generate_qr_code()

        return redirect(url_for('display_outing_pass', unique_id=outing_pass.unique_id))
    
    return render_template('create_outing_pass.html', username=session['username'])

@app.route('/outing_pass/<unique_id>')
def display_outing_pass(unique_id):
    conn = sqlite3.connect('outing_passes.db')
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM outing_passes WHERE unique_id = ?", (unique_id,))
    outing_pass = cursor.fetchone()
    conn.close()

    if outing_pass:
        name, date, reason, expiry_date, teacher, ban = outing_pass[1], outing_pass[2], outing_pass[3], outing_pass[4], outing_pass[5], outing_pass[6]
        return render_template('display_outing_pass.html', name=name, date=date, reason=reason, expiry_date=expiry_date, teacher=teacher, ban=ban)
    return "유효하지 않은 외출증입니다!"

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
