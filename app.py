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

# --- 🚀 重要：強制的にテーブルを作るための秘密のページ ---
@app.route('/init-db')
def init_db():
    try:
        db.create_all()
        return "データベースの初期化（テーブル作成）に成功しました！戻って新規登録してください。"
    except Exception as e:
        return f"エラーが発生しました: {e}"

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

# --- 各ルート設定 ---

@app.route('/')
def index():
    if not current_user.is_authenticated: return redirect(url_for('login'))
    today = date.today()
    try:
        tasks = Task.query.filter_by(user_id=current_user.id).all()
    except:
        return redirect(url_for('init_db')) # エラーが出たら初期化ページへ飛ばす
    
    urgent_tasks_html = ""
    for t in tasks:
        if not t.is_completed and t.is_notify:
            notice_start = t.task_date - timedelta(days=t.notify_days_before)
            if notice_start <= today <= t.task_date:
                diff = (t.task_date - today).days
                urgent_tasks_html += f'<div class="card alert-card"><b>【{"今日まで" if diff==0 else "あと"+str(diff)+"日"}】</b> {t.title}</div>'

    content = f"<h2>こんにちは、{current_user.username} さん</h2>{f'<div><h3>🔥 緊急タスク</h3>{urgent_tasks_html}</div><hr>' if urgent_tasks_html else ''}<div id='calendar'></div>"
    return render_template_string(BASE_HTML, content=content)

@app.route('/api/events')
@login_required
def get_events():
    start_str = request.args.get('start', '').split('T')[0]
    end_str = request.args.get('end', '').split('T')[0]
    start_dt = datetime.strptime(start_str, '%Y-%m-%d').date() if start_str else date.today() - timedelta(days=30)
    end_dt = datetime.strptime(end_str, '%Y-%m-%d').date() if end_str else date.today() + timedelta(days=30)
    events = []
    today = date.today()
    tasks = Task.query.filter_by(user_id=current_user.id).all()
    for t in tasks:
        if start_dt <= t.task_date <= end_dt:
            events.append({'title': f"📌 {t.title}", 'start': t.task_date.isoformat(), 'color': t.color if not t.is_completed else '#ccc'})
    return jsonify(events)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        try:
            user = User(username=request.form.get('username'), email=request.form.get('email'))
            user.set_password(request.form.get('password'))
            db.session.add(user); db.session.commit()
            return redirect(url_for('login'))
        except:
            return redirect(url_for('init_db')) # テーブルがないなら初期化ページへ
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

if __name__ == '__main__':
    app.run()
