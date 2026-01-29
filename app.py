import os
from flask import Flask, render_template_string, request, redirect, url_for, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, date, timedelta

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'your-secret-key-123')

# --- データベース設定 ---
database_url = os.environ.get('DATABASE_URL')
if database_url and database_url.startswith("postgres://"):
    database_url = database_url.replace("postgres://", "postgresql://", 1)

app.config['SQLALCHEMY_DATABASE_URI'] = database_url or "postgresql://guest:password@localhost:5432/my-db"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# --- データベースモデル ---
class User(db.Model, UserMixin):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    def set_password(self, password): self.password_hash = generate_password_hash(password)
    def check_password(self, password): return check_password_hash(self.password_hash, password)

class Task(db.Model):
    __tablename__ = 'tasks'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    task_date = db.Column(db.Date, nullable=False)
    title = db.Column(db.String(100), nullable=False)
    detail = db.Column(db.Text)
    priority = db.Column(db.Integer, default=1)
    is_completed = db.Column(db.Boolean, default=False)
    color = db.Column(db.String(20), default='#3182ce')
    is_notify = db.Column(db.Boolean, default=True)
    notify_days_before = db.Column(db.Integer, default=1)

class Habit(db.Model):
    __tablename__ = 'habits'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    day_of_week = db.Column(db.String(20), nullable=False)
    title = db.Column(db.String(100), nullable=False)
    detail = db.Column(db.Text)
    streak_count = db.Column(db.Integer, default=0)
    last_achieved_date = db.Column(db.Date)
    color = db.Column(db.String(20), default='#38a169')

class FavoriteColor(db.Model):
    __tablename__ = 'favorite_colors'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    hex_code = db.Column(db.String(10), nullable=False)

# --- ログイン管理 ---
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))

# --- HTML共通レイアウト ---
BASE_HTML = """
<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <title>Task & Habit Dashboard</title>
    <script src='https://cdn.jsdelivr.net/npm/fullcalendar@6.1.8/index.global.min.js'></script>
    <style>
        body { font-family: sans-serif; margin: 0; background: #f4f7f6; color: #333; }
        nav { background: #333; color: white; padding: 15px; text-align: center; }
        nav a { color: white; margin: 0 15px; text-decoration: none; font-weight: bold; }
        .container { max-width: 1000px; margin: 20px auto; padding: 20px; background: white; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
        .card { padding: 12px; border-radius: 8px; border-left: 8px solid; background: #f9f9f9; margin-bottom: 10px; position: relative; }
        .alert-card { background: #fff5f5; border: 2px solid #feb2b2; border-left: 10px solid #f56565; color: #c53030; }
        button.main-btn { background: #333; color: white; padding: 10px; border: none; border-radius: 5px; cursor: pointer; width: 100%; font-size: 1rem; }
        form label { font-weight: bold; display: block; margin-top: 10px; }
        form input, form select, form textarea { width: 100%; padding: 10px; margin: 5px 0; border: 1px solid #ddd; border-radius: 5px; box-sizing: border-box; }
        .color-selector-wrapper { position: relative; width: 100%; margin-top: 5px; height: 40px; }
        .real-picker { position: absolute; opacity: 0; width: 100%; height: 100%; cursor: pointer; z-index: 2; }
        .visual-bar { width: 100%; height: 100%; border-radius: 8px; border: 2px solid rgba(0,0,0,0.05); transition: transform 0.1s; }
        .fav-palette { display: flex; flex-wrap: wrap; gap: 10px; margin-top: 10px; }
        .color-dot { width: 30px; height: 30px; border-radius: 50%; cursor: pointer; border: 2px solid #fff; box-shadow: 0 0 3px rgba(0,0,0,0.2); transition: transform 0.2s; }
        .add-fav-btn { font-size: 0.8rem; cursor: pointer; color: #666; background: #eee; border: none; padding: 5px 10px; border-radius: 4px; margin-top: 5px; }
        .streak-badge { font-size: 0.8rem; background: #fffaf0; color: #dd6b20; border: 1px solid #fbd38d; padding: 2px 8px; border-radius: 12px; font-weight: bold; margin-left: 8px; }
        #calendar { margin-bottom: 30px; }
    </style>
</head>
<body>
    <nav>
        <a href="/">HOME</a>
        {% if current_user.is_authenticated %}
            <a href="/tasks">タスク追加</a>
            <a href="/habits">習慣管理</a>
            <a href="/logout">ログアウト</a>
        {% else %}
            <a href="/login">ログイン</a>
            <a href="/register">新規登録</a>
        {% endif %}
    </nav>
    <div class="container">{{ content | safe }}</div>
</body>
</html>
"""

# --- 色管理用UI ---
def get_color_ui_html(current_color, picker_id, bar_id):
    favs = FavoriteColor.query.filter_by(user_id=current_user.id).all()
    fav_dots = "".join([f'<div class="color-dot" style="background: {f.hex_code};" onclick="applyFav(\'{f.hex_code}\', \'{picker_id}\', \'{bar_id}\')"></div>' for f in favs])
    return f"""
    <div class="color-selector-wrapper">
        <input type="color" name="color" class="real-picker" id="{picker_id}" value="{current_color}">
        <div id="{bar_id}" class="visual-bar" style="background: {current_color};"></div>
    </div>
    <div class="fav-palette">{fav_dots}</div>
    <button type="button" class="add-fav-btn" onclick="saveFav('{picker_id}')">お気に入り登録</button>
    <script>
        document.getElementById('{picker_id}').oninput = function() {{ document.getElementById('{bar_id}').style.background = this.value; }};
        function applyFav(hex, pId, bId) {{ document.getElementById(pId).value = hex; document.getElementById(bId).style.background = hex; }}
        function saveFav(pId) {{
            const hex = document.getElementById(pId).value;
            fetch('/colors/favorite', {{ method: 'POST', headers: {{ 'Content-Type': 'application/json' }}, body: JSON.stringify({{ hex: hex }}) }})
            .then(res => res.json()).then(data => {{ if(data.success) location.reload(); }});
        }}
    </script>
    """

# --- ルート設定 ---

@app.route('/')
def index():
    if not current_user.is_authenticated: return redirect(url_for('login'))
    today = date.today()
    tasks = Task.query.filter_by(user_id=current_user.id).all()
    urgent_html = "".join([f'<div class="card alert-card"><b>🔥 あと{(t.task_date - today).days}日:</b> {t.title}</div>' for t in tasks if not t.is_completed and (t.task_date - today).days <= t.notify_days_before])
    content = f"<h2>こんにちは、{current_user.username}さん</h2>{urgent_html}<div id='calendar'></div><script>document.addEventListener('DOMContentLoaded', function() {{ var cal = new FullCalendar.Calendar(document.getElementById('calendar'), {{ initialView: 'dayGridMonth', locale: 'ja', events: '/api/events' }}); cal.render(); }});</script>"
    return render_template_string(BASE_HTML, content=content)

@app.route('/api/events')
@login_required
def get_events():
    events = []
    tasks = Task.query.filter_by(user_id=current_user.id).all()
    for t in tasks:
        events.append({'title': f"📌 {t.title}", 'start': t.task_date.isoformat(), 'color': t.color if not t.is_completed else '#ccc'})
    
    habits = Habit.query.filter_by(user_id=current_user.id).all()
    today = date.today()
    for i in range(-30, 31):
        curr = today + timedelta(days=i)
        dow = ['月曜日','火曜日','水曜日','木曜日','金曜日','土曜日','日曜日'][curr.weekday()]
        for h in habits:
            if h.day_of_week == dow:
                events.append({'title': f"🔄 {h.title}", 'start': curr.isoformat(), 'color': h.color})
    return jsonify(events)

@app.route('/tasks', methods=['GET', 'POST'])
@login_required
def manage_tasks():
    if request.method == 'POST':
        new_t = Task(user_id=current_user.id, task_date=datetime.strptime(request.form.get('date'), '%Y-%m-%d').date(), title=request.form.get('title'), color=request.form.get('color'))
        db.session.add(new_t); db.session.commit(); return redirect(url_for('manage_tasks'))
    tasks = Task.query.filter_by(user_id=current_user.id).order_by(Task.task_date).all()
    t_html = "".join([f'<div class="card" style="border-left-color: {t.color};">{t.task_date} {t.title}</div>' for t in tasks])
    return render_template_string(BASE_HTML, content=f'<h2>タスク登録</h2><form method="POST">日付:<input type="date" name="date" required>タイトル:<input type="text" name="title" required>色:{get_color_ui_html("#3182ce", "cp", "cb")}<button type="submit" class="main-btn">保存</button></form><hr>{t_html}')

@app.route('/habits', methods=['GET', 'POST'])
@login_required
def manage_habits():
    if request.method == 'POST':
        new_h = Habit(user_id=current_user.id, day_of_week=request.form.get('dow'), title=request.form.get('title'), color=request.form.get('color'))
        db.session.add(new_h); db.session.commit(); return redirect(url_for('manage_habits'))
    habits = Habit.query.filter_by(user_id=current_user.id).all()
    h_html = "".join([f'<div class="card" style="border-left-color: {h.color};">{h.title} ({h.day_of_week})</div>' for h in habits])
    return render_template_string(BASE_HTML, content=f'<h2>習慣登録</h2><form method="POST">曜日:<select name="dow"><option>月曜日</option><option>火曜日</option><option>水曜日</option><option>木曜日</option><option>金曜日</option><option>土曜日</option><option>日曜日</option></select>タイトル:<input type="text" name="title" required>色:{get_color_ui_html("#38a169", "hcp", "hcb")}<button type="submit" class="main-btn">保存</button></form><hr>{h_html}')

@app.route('/colors/favorite', methods=['POST'])
@login_required
def add_favorite_color():
    hex_code = request.json.get('hex')
    if hex_code:
        new_fav = FavoriteColor(user_id=current_user.id, hex_code=hex_code)
        db.session.add(new_fav); db.session.commit()
    return jsonify({'success': True})

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        user = User(username=request.form.get('username'), email=request.form.get('email'))
        user.set_password(request.form.get('password'))
        db.session.add(user); db.session.commit(); return redirect(url_for('login'))
    return render_template_string(BASE_HTML, content='<h2>新規登録</h2><form method="POST">名前:<input type="text" name="username">メール:<input type="email" name="email">パスワード:<input type="password" name="password"><button type="submit" class="main-btn">登録</button></form>')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user = User.query.filter_by(email=request.form.get('email')).first()
        if user and user.check_password(request.form.get('password')):
            login_user(user); return redirect(url_for('index'))
    return render_template_string(BASE_HTML, content='<h2>ログイン</h2><form method="POST">メール:<input type="email" name="email">パスワード:<input type="password" name="password"><button type="submit" class="main-btn">ログイン</button></form>')

@app.route('/logout')
def logout(): logout_user(); return redirect(url_for('login'))

@app.route('/init-db')
def init_db():
    db.create_all()
    return "完了"

if __name__ == '__main__':
    app.run()
