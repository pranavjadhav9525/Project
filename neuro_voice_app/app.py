from flask import Flask, render_template, request, redirect, url_for, session, g, jsonify
import sqlite3
import os
from datetime import datetime

app = Flask(__name__)
app.secret_key = "supersecretkey123"
DATABASE = "appdata.db"

def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
        db.row_factory = sqlite3.Row
    return db

@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

def init_db():
    if not os.path.exists(DATABASE):
        db = sqlite3.connect(DATABASE)
        cur = db.cursor()
        cur.execute('''
            CREATE TABLE users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                theme TEXT DEFAULT 'light'
            )
        ''')
        cur.execute('''
            CREATE TABLE voice_queries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL,
                query_text TEXT NOT NULL,
                timestamp TEXT NOT NULL
            )
        ''')
        db.commit()
        db.close()

@app.before_request
def load_theme():
    g.theme = 'light'
    if 'username' in session:
        db = get_db()
        row = db.execute("SELECT theme FROM users WHERE username = ?", (session['username'],)).fetchone()
        if row and row['theme']:
            g.theme = row['theme']

@app.route('/')
def index():
    if session.get('username'):
        if session.get('username') == 'admin':
            return redirect(url_for('admin_dashboard'))
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

# Register
@app.route('/register', methods=['GET','POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username','').strip()
        password = request.form.get('password','').strip()
        if not username or not password:
            return render_template('register.html', error="Fill both fields", theme='light')
        db = get_db()
        try:
            db.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, password))
            db.commit()
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            return render_template('register.html', error="Username exists", theme='light')
    return render_template('register.html', theme='light')

# Login
@app.route('/login', methods=['GET','POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username','').strip()
        password = request.form.get('password','').strip()
        if username == 'admin' and password == 'password':
            session['username'] = 'admin'
            return redirect(url_for('admin_dashboard'))
        db = get_db()
        user = db.execute("SELECT * FROM users WHERE username=? AND password=?", (username, password)).fetchone()
        if user:
            session['username'] = username
            return redirect(url_for('dashboard'))
        return render_template('login.html', error="Invalid credentials", theme='light')
    return render_template('login.html', theme='light')

# Dashboard
@app.route('/dashboard')
def dashboard():
    if 'username' not in session or session.get('username') == 'admin':
        return redirect(url_for('login'))
    db = get_db()
    rows = db.execute("SELECT query_text, timestamp FROM voice_queries WHERE username=? ORDER BY timestamp DESC",
                      (session['username'],)).fetchall()
    texts = [{"text": r["query_text"], "ts": r["timestamp"]} for r in rows]
    return render_template('dashboard.html', theme=g.theme, username=session['username'], voice_texts=texts)

# Save query (AJAX endpoint or form POST)
@app.route('/save_query', methods=['POST'])
def save_query():
    if 'username' not in session or session.get('username') == 'admin':
        return jsonify({"status":"error","message":"unauthorized"}), 403
    data_text = request.form.get('voice_text') or (request.get_json() or {}).get('query')
    if not data_text:
        return jsonify({"status":"error","message":"empty"}), 400
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    db = get_db()
    db.execute("INSERT INTO voice_queries (username, query_text, timestamp) VALUES (?, ?, ?)",
               (session['username'], data_text, ts))
    db.commit()
    return jsonify({"status":"ok","message":"saved"})

# Change theme (per-user)
@app.route('/change_theme', methods=['POST'])
def change_theme():
    if 'username' not in session:
        return redirect(url_for('login'))
    theme = request.form.get('theme','light')
    db = get_db()
    db.execute("UPDATE users SET theme = ? WHERE username = ?", (theme, session['username']))
    db.commit()
    return redirect(url_for('dashboard'))

# Admin dashboard
@app.route('/admin/dashboard', methods=['GET','POST'])
def admin_dashboard():
    if 'username' not in session or session['username'] != 'admin':
        return redirect(url_for('login'))
    db = get_db()
    rows = db.execute("SELECT username, query_text, timestamp FROM voice_queries ORDER BY timestamp DESC").fetchall()
    grouped = {}
    for r in rows:
        grouped.setdefault(r['username'], []).append({"text": r['query_text'], "ts": r['timestamp']})
    if request.method == 'POST':
        # allow admin to change theme for a user if needed (optional)
        target = request.form.get('target_user')
        theme = request.form.get('theme')
        if target and theme:
            db.execute("UPDATE users SET theme=? WHERE username=?", (theme, target))
            db.commit()
            return redirect(url_for('admin_dashboard'))
    return render_template('admin.html', theme='light', grouped=grouped)

# Logout
@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

if __name__ == '__main__':
    init_db()
    app.run(debug=True)
