import json
import jwt
import os
import secrets
import schedule
import threading
import time
import requests
from flask import Flask, session, request, redirect, render_template
from flask_login import UserMixin,LoginManager, login_user, logout_user, login_required, current_user
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv
from linebot import LineBotApi
from linebot.models import TextSendMessage
from urllib.parse import urlencode
from werkzeug.security import generate_password_hash, check_password_hash

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
    user_name = db.Column(db.String(30), nullable=False, unique=True)
    password = db.Column(db.String(255), nullable=False)
    line = db.Column(db.String(33), unique=True)

class memo(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False,)
    content = db.Column(db.String(255), nullable=False)
    timer = db.Column(db.DateTime, nullable=False)

with app.app_context():
    db.create_all()                           

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

#タイマー表示
def get_countdown_text(timer_time):
    JST = timezone(timedelta(hours=9), 'JST')
    now_jst = datetime.now(JST)
    now_naive = now_jst.replace(tzinfo=None)

    diff = timer_time - now_naive
    total_seconds = diff.total_seconds()

    hours, remainder = divmod(total_seconds, 3600)
    minutes, _ = divmod(remainder, 60)

    if hours > 0:
        return f"{int(hours)}時間{int(minutes)}分後"
    else:
        return f"{int(minutes)}分後"

 
@app.route('/memo', methods=['POST'])
@login_required
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
    return redirect('/')




#LINE連携
YOUR_LINE_ID = os.getenv('MY_USER_ID')
LINE_CHANNEL_ID = "2009911695"
LINE_CHANNEL_SECRET = "3627b3dee6f9c2b8bb31b83335067952"
LINE_CHANNEL_ACCES_TOKEN = os.getenv('CHANNEL_ACCESS_TOKEN')
line_bot_api = LineBotApi(LINE_CHANNEL_ACCES_TOKEN)
REDIRECT_URL = 'http://127.0.0.1:5000/callback'


@app.route('/callback',methods=["GET"])
def callback():
    # 認可コードを取得する
    request_code = request.args['code']
    uri_access_token = "https://api.line.me/oauth2/v2.1/token"
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    data_params = {
        "grant_type": "authorization_code",
        "code": request_code,
        "redirect_uri": REDIRECT_URL,
        "client_id": LINE_CHANNEL_ID,
        "client_secret": LINE_CHANNEL_SECRET
    }

    # トークンを取得するためにリクエストを送る
    response_post = requests.post(uri_access_token, headers=headers, data=data_params)
    print("中身の確認:",response_post)
    print("--- LINEからの返答ステータス ---", response_post.status_code)
    print("--- LINEからのエラー詳細 ---", response_post.text)

    # 安全に中身を読み込む
    response_json = response_post.json()
    if "id_token" not in response_json:
        return f"LINEログインエラー: {response_json.get('error_description', '不明なエラー')}", 400

    line_id_token = response_json["id_token"]

    # ペイロード部分をデコードすることで、ユーザ情報を取得する
    decoded_id_token = jwt.decode(line_id_token,
                                  LINE_CHANNEL_SECRET,
                                  audience=LINE_CHANNEL_ID,
                                  issuer='https://access.line.me',
                                  algorithms=['HS256'],
                                  leeway=10)

    return render_template("home.html", user_profile=decoded_id_token)





# #Cron-job.org
# @app.route('/keep_alive')
# def keep_alive():
#     check_and_send_notifications()
#     return "I'm alive!", 200




#ログアウト機能
@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect('login')



# worker.py の処理を別スレッドで裏側で起動する関数
def start_worker():
    import subprocess
    import sys
    # python worker.py をバックグラウンドの別プロセスとして起動します
    subprocess.Popen([sys.executable, "worker.py"])

if __name__ == "__main__":
    # ローカル開発環境（python app.py）のときだけ worker も同時に立ち上げる
    start_worker()
    app.run(debug=True)