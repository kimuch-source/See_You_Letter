import os
from flask import Flask
from flask import request, redirect, render_template
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin,LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from flask_migrate import Migrate
from dotenv import load_dotenv
from datetime import datetime, timedelta, timezone
from linebot import LineBotApi
from linebot.models import TextSendMessage

load_dotenv()


app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DB_URL')
app.config['SECRET_KEY'] = os.getenv('SEACRET_KEY')
db = SQLAlchemy()
db.init_app(app)
migrate = Migrate(app,db)

login_manager = LoginManager()
login_manager.init_app(app)

#データベース設計
class users(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_name = db.Column(db.String(30), unique=True)
    password = db.Column(db.String(255),)
    line = db.Column(db.String(20), unique=True)

class memo(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    content = db.Column(db.String(255), nullable=False)
    timer = db.Column(db.DateTime, nullable=False)

@login_manager.user_loader
def load_user(user_id):
    return users.query.get(int(user_id))



#新規登録画面
@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        user_name = request.form.get('user_name')
        password = request.form.get('password')
        repassword = request.form.get('repassword')

        if password != repassword:
            return "パスワードが一致しません。もう一度入力してください。"

        user = users(user_name=user_name, password=generate_password_hash(password))

        db.session.add(user)
        db.session.commit()
        return redirect('/login')
    else:
        return render_template('auth/signup.html')
    


#ログイン画面
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user_name = request.form.get('user_name')
        password = request.form.get('password')

        user = users.query.filter_by(user_name=user_name).first()
        if check_password_hash(user.password, password):
            login_user(user) 
            return redirect('/')
    else:
        return render_template('auth/login.html')
    


#ホーム画面
@app.route('/')
@login_required
def home():
    memos_from_db = memo.query.filter_by(user_id=current_user.id).all()
    display_memos = []
    JST = timezone(timedelta(hours=9), 'JST')
    now_jst = datetime.now(JST)

    for m in memos_from_db:
        now_naive = now_jst.replace(tzinfo=None)
        if m.timer > now_naive:
            display_memos.append({
                'content':m.content,
                'countdown' : get_countdown_text(m.timer)
            })

    return render_template('home.html', memos=display_memos)

def get_countdown_text(timer_time):
    JST = timezone(timedelta(hours=9), 'JST')
    now_jst = datetime.now(JST)
    now_naive = now_jst.replace(tzinfo=None)

    diff = timer_time - now_naive
    total_seconds = diff.total_seconds()

    hours, remainder = divmod(total_seconds, 3600)
    minutes, _ = divmod(remainder, 60)

    if hours > 0:
        return f"あと{int(hours)}時間{int(minutes)}分"
    else:
        return f"あと{int(minutes)}分"


LINE_CHANNEL_ACCES_TOKEN = os.getenv('MY_CHANNEL_ACCESS_TOKEN')
line_bot_api = LineBotApi(LINE_CHANNEL_ACCES_TOKEN)
YOUR_LINE_ID = os.getenv('MY_USER_ID')  
@app.route('/memo', methods=['POST'])
def add_memo():
    content = request.form.get('content')
    JST = timezone(timedelta(hours=9), 'JST')
    now_jst = datetime.now(JST)
    input_h = request.form.get('input_hours')
    input_m = request.form.get('input_minutes')
    add_hours = int(input_h)
    add_minutes = int(input_m)
    timer = now_jst + timedelta(hours=add_hours, minutes=add_minutes)
    new_memo = memo(user_id=current_user.id, content=content, timer=timer)    
    db.session.add(new_memo)
    db.session.commit()


    # 1. ここで計算した変数名は何になっていますか？（例: target_time とか）
    timer_datetime = (now_jst + timedelta(hours=add_hours, minutes=add_minutes)).replace(tzinfo=None)

    # 2. データベース保存
    new_memo = memo(content=content, timer=timer_datetime, user_id=current_user.id)
    db.session.add(new_memo)
    db.session.commit()
    

    try:
        message = f"タイマーをセットしました！\n内容: {content}\n期限: {timer_datetime.strftime('%H:%M')}"
        line_bot_api.push_message(YOUR_LINE_ID, TextSendMessage(text=message))
    except Exception as e:
        print(f"LINE通知に失敗しました: {e}")

    return redirect('/')

#ログアウト機能
@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect('login')





if __name__ == "__main__":
    app.run(debug=True)