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
    tasks = db.relationship('Task', backref='user', cascade='all, delete-orphan')
    habits = db.relationship('Habit', backref='user', cascade='all, delete-orphan')
    colors = db.relationship('FavoriteColor', backref='user', cascade='all, delete-orphan')
    def set_password(self, password): self.password_hash = generate_password_hash(password)
    def check_password(self, password): return check_password_hash(self.password_hash, password)

class Task(db.Model):
    __tablename__ = 'tasks'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'))
    task_date = db.Column(db.Date, nullable=False)
    title = db.Column(db.String(100), nullable=False)
    is_completed = db.Column(db.Boolean, default=False)
    color = db.Column(db.String(20), default='#3182ce')
    is_notify = db.Column(db.Boolean, default=True)
    notify_days_before = db.Column(db.Integer, default=1)

class Habit(db.Model):
    __tablename__ = 'habits'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'))
    day_of_week = db.Column(db.String(20), nullable=False)
    title = db.Column(db.String(100), nullable=False)
    streak_count = db.Column(db.Integer, default=0)
    last_achieved_date = db.Column(db.Date)
    color = db.Column(db.String(20), default='#38a169')

class FavoriteColor(db.Model):
    __tablename__ = 'favorite_colors'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'))
    hex_code = db.Column(db.String(10), nullable=False)

# --- ログイン管理 ---
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id): return db.session.get(User, int(user_id))

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
        .flash-msg { background: #fed7d7; color: #c53030; border: 1px solid #feb2b2; padding: 10px; margin-bottom: 20px; border-radius: 5px; text-align: center; }
        button.main-btn { background: #333; color: white; padding: 10px; border: none; border-radius: 5px; cursor: pointer; width: 100%; font-size: 1rem; }
        .delete-btn { color: #ff9999; font-size: 0.8rem; text-decoration: underline; cursor: pointer; background: none; border: none; margin-left: 15px; }
        .streak-badge { font-size: 0.8rem; background: #fffaf0; color: #dd6b20; border: 1px solid #fbd38d; padding: 2px 8px; border-radius: 12px; font-weight: bold; margin-left: 8px; }
    </style>
</head>
<body>
    <nav>
        <a href="/">HOME</a>
        {% if current_user.is_authenticated %}
            <a href="/tasks">タスク追加</a>
            <a href="/habits">習慣管理</a>
            <a href="/logout">ログアウト</a>
            <form action="/delete_account" method="POST" style="display:inline;" onsubmit="return confirm('退会すると全データが削除されます。よろしいですか？');">
                <button type="submit" class="delete-btn">退会</button>
            </form>
        {% else %}
            <a href="/login">ログイン</a>
            <a href="/register">新規登録</a>
        {% endif %}
    </nav>
    <div class="container">
        {% with messages = get_flashed_messages() %}{% if messages %}{% for m in messages %}<div class="flash-msg">{{ m }}</div>{% endfor %}{% endif %}{% endwith %}
        {{ content | safe }}
    </div>
</body>
</html>
"""

def get_color_ui_html(current_color, picker_id, bar_id):
    favs = FavoriteColor.query.filter_by(user_id=current_user.id).all()
    fav_dots = "".join([f'<div class="color-dot" style="width:25px;height:25px;border-radius:50%;display:inline-block;margin-right:5px;cursor:pointer;background:{f.hex_code};" onclick="applyFav(\'{f.hex_code}\', \'{picker_id}\', \'{bar_id}\')" oncontextmenu="deleteFav(event, \'{f.id}\')"></div>' for f in favs])
    return f"""
    <div style="margin:10px 0;">
        <input type="color" id="{picker_id}" name="color" value="{current_color}" style="width:100%;height:40px;cursor:pointer;">
        <div id="{bar_id}" style="height:10px;background:{current_color};margin-top:2px;border-radius:5px;"></div>
        <div style="margin-top:10px;">{fav_dots}</div>
        <button type="button" onclick="saveFav('{picker_id}')" style="font-size:0.7rem;margin-top:5px;">この色を保存</button>
    </div>
    <script>
        document.getElementById('{picker_id}').oninput = function() {{ document.getElementById('{bar_id}').style.background = this.value; }};
        function applyFav(hex, pId, bId) {{ document.getElementById(pId).value = hex; document.getElementById(bId).style.background = hex; }}
        function saveFav(pId) {{ fetch('/colors/favorite', {{ method: 'POST', headers: {{ 'Content-Type': 'application/json' }}, body: JSON.stringify({{ hex: document.getElementById(pId).value }}) }}).then(() => location.reload()); }}
        function deleteFav(e, id) {{ e.preventDefault(); if(confirm('消去？')) fetch('/colors/favorite/delete/'+id, {{method:'POST'}}).then(()=>location.reload()); }}
    </script>
    """

@app.route('/')
def index():
    if not current_user.is_authenticated: return redirect(url_for('login'))
    today = date.today()
    tasks = Task.query.filter_by(user_id=current_user.id).all()
    urgent_html = ""
    for t in tasks:
        if not t.is_completed and t.is_notify:
            diff = (t.task_date - today).days
            if 0 <= diff <= t.notify_days_before:
                urgent_html += f'<div class="card alert-card"><b>【{"今日まで" if diff==0 else "あと"+str(diff)+"日"}】</b> {t.title}</div>'
    
    content = f"""
    <h2>こんにちは、{current_user.username}さん</h2>
    {urgent_html}
    <div id='calendar'></div>
    <script>
      document.addEventListener('DOMContentLoaded', function() {{
        var cal = new FullCalendar.Calendar(document.getElementById('calendar'), {{
          initialView: 'dayGridMonth', locale: 'ja',
          events: '/api/events',
          eventClick: function(info) {{
            var p = info.event.extendedProps;
            if(p.type==='タスク') {{ if(confirm('完了状態を切り替えますか？')) window.location.href='/tasks/complete/'+p.db_id; }}
            else {{ 
              if(p.is_today && !p.already_done) {{ if(confirm('「'+info.event.title+'」を達成しましたか？')) window.location.href='/habits/achieve/'+p.db_id+'?from=home'; }}
              else {{ window.location.href='/habits'; }}
            }}
          }}
        }});
        cal.render();
      }});
    </script>
    """
    return render_template_string(BASE_HTML, content=content)

@app.route('/api/events')
@login_required
def get_events():
    events = []
    today = date.today()
    # カレンダーが表示しようとしている期間を取得
    start_str = request.args.get('start', '').split('T')[0]
    end_str = request.args.get('end', '').split('T')[0]
    start_dt = datetime.strptime(start_str, '%Y-%m-%d').date() if start_str else today - timedelta(days=35)
    end_dt = datetime.strptime(end_str, '%Y-%m-%d').date() if end_str else today + timedelta(days=35)

    # タスク
    tasks = Task.query.filter_by(user_id=current_user.id).all()
    for t in tasks:
        if start_dt <= t.task_date <= end_dt:
            events.append({'title': f"{'✅' if t.is_completed else '📌'} {t.title}", 'start': t.task_date.isoformat(), 'color': t.color if not t.is_completed else '#ccc', 'extendedProps': {'type':'タスク', 'db_id':t.id}})
    
    # 習慣（カレンダーの表示期間に合わせて動的に生成）
    habits = Habit.query.filter_by(user_id=current_user.id).all()
    curr = start_dt
    while curr <= end_dt:
        dow_str = ['月曜日','火曜日','水曜日','木曜日','金曜日','土曜日','日曜日'][curr.weekday()]
        for h in habits:
            if h.day_of_week == dow_str:
                is_achieved = (h.last_achieved_date == curr)
                events.append({
                    'title': f"{'✅' if is_achieved else '🔄'} {h.title}",
                    'start': curr.isoformat(),
                    'color': '#ccc' if is_achieved else h.color,
                    'extendedProps': {'type':'習慣', 'db_id':h.id, 'is_today':(curr==today), 'already_done':(h.last_achieved_date==today)}
                })
        curr += timedelta(days=1)
    return jsonify(events)

@app.route('/tasks', methods=['GET', 'POST'])
@login_required
def manage_tasks():
    if request.method == 'POST':
        nb = int(request.form.get('notify', 1))
        new_t = Task(user_id=current_user.id, task_date=datetime.strptime(request.form.get('date'), '%Y-%m-%d').date(), title=request.form.get('title'), color=request.form.get('color'), is_notify=(nb >= 0), notify_days_before=max(0, nb))
        db.session.add(new_t); db.session.commit(); return redirect(url_for('manage_tasks'))
    tasks = Task.query.filter_by(user_id=current_user.id).order_by(Task.task_date).all()
    t_html = "".join([f'<div class="card" style="border-left-color: {t.color};"><b>{t.task_date}</b> {t.title} <a href="/tasks/delete/{t.id}" style="float:right; color:#999;">削除</a></div>' for t in tasks])
    options = '<option value="-1">通知しない</option>' + "".join([f'<option value="{i}" {"selected" if i==1 else ""}>{i}日前</option>' for i in range(1, 8)])
    return render_template_string(BASE_HTML, content=f'<h2>タスク登録</h2><form method="POST">日付:<input type="date" name="date" required>タイトル:<input type="text" name="title" required>通知:<select name="notify">{options}</select>表示色:{get_color_ui_html("#3182ce", "cp", "cb")}<button type="submit" class="main-btn">保存</button></form><hr>{t_html}')

@app.route('/habits', methods=['GET', 'POST'])
@login_required
def manage_habits():
    if request.method == 'POST':
        new_h = Habit(user_id=current_user.id, day_of_week=request.form.get('dow'), title=request.form.get('title'), color=request.form.get('color'))
        db.session.add(new_h); db.session.commit(); return redirect(url_for('manage_habits'))
    habits = Habit.query.filter_by(user_id=current_user.id).all()
    h_html = "".join([f'<div class="card" style="border-left-color: {h.color};"><b>{h.title}</b> ({h.day_of_week}) <span class="streak-badge">🔥 {h.streak_count}日継続</span><a href="/habits/delete/{h.id}" style="float:right; color:#999;">削除</a></div>' for h in habits])
    return render_template_string(BASE_HTML, content=f'<h2>習慣管理</h2><form method="POST">曜日:<select name="dow"><option>月曜日</option><option>火曜日</option><option>水曜日</option><option>木曜日</option><option>金曜日</option><option>土曜日</option><option>日曜日</option></select>タイトル:<input type="text" name="title" required>表示色:{get_color_ui_html("#38a169", "hcp", "hcb")}<button type="submit" class="main-btn">保存</button></form><hr>{h_html}')

@app.route('/habits/achieve/<int:id>')
@login_required
def achieve_habit(id):
    h = db.session.get(Habit, id)
    if h and h.last_achieved_date != date.today():
        h.streak_count += 1; h.last_achieved_date = date.today(); db.session.commit()
    return redirect(url_for('index') if request.args.get('from') == 'home' else url_for('manage_habits'))

@app.route('/tasks/complete/<int:id>')
@login_required
def complete_task(id):
    t = db.session.get(Task, id); t.is_completed = not t.is_completed; db.session.commit(); return redirect(url_for('index'))

@app.route('/colors/favorite', methods=['POST'])
@login_required
def add_favorite():
    c = FavoriteColor(user_id=current_user.id, hex_code=request.json.get('hex')); db.session.add(c); db.session.commit(); return jsonify({'success':True})

@app.route('/colors/favorite/delete/<int:id>', methods=['POST'])
@login_required
def delete_favorite(id):
    c = db.session.get(FavoriteColor, id); db.session.delete(c); db.session.commit(); return jsonify({'success':True})

@app.route('/tasks/delete/<int:id>')
@login_required
def delete_task(id):
    t = db.session.get(Task, id); db.session.delete(t); db.session.commit(); return redirect(url_for('manage_tasks'))

@app.route('/habits/delete/<int:id>')
@login_required
def delete_habit(id):
    h = db.session.get(Habit, id); db.session.delete(h); db.session.commit(); return redirect(url_for('manage_habits'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form.get('email')
        if User.query.filter_by(email=email).first(): flash('登録済みです'); return redirect(url_for('register'))
        user = User(username=request.form.get('username'), email=email); user.set_password(request.form.get('password'))
        db.session.add(user); db.session.commit(); return redirect(url_for('login'))
    return render_template_string(BASE_HTML, content='<h2>新規登録</h2><form method="POST">名前:<input type="text" name="username">メール:<input type="email" name="email">パスワード:<input type="password" name="password"><button type="submit" class="main-btn">登録</button></form>')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user = User.query.filter_by(email=request.form.get('email')).first()
        if user and user.check_password(request.form.get('password')): login_user(user); return redirect(url_for('index'))
        flash('失敗しました')
    return render_template_string(BASE_HTML, content='<h2>ログイン</h2><form method="POST">メール:<input type="email" name="email">パスワード:<input type="password" name="password"><button type="submit" class="main-btn">ログイン</button></form>')

@app.route('/logout')
def logout(): logout_user(); return redirect(url_for('login'))

@app.route('/delete_account', methods=['POST'])
@login_required
def delete_account():
    user = db.session.get(User, current_user.id); logout_user(); db.session.delete(user); db.session.commit(); flash('削除完了'); return redirect(url_for('register'))

@app.route('/init-db')
def init_db(): db.create_all(); return "OK"

if __name__ == '__main__': app.run()
