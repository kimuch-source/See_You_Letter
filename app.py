import os
import secrets
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


    timer_datetime = (now_jst + timedelta(hours=add_hours, minutes=add_minutes)).replace(tzinfo=None)

    new_memo = memo(content=content, timer=timer_datetime, user_id=current_user.id)
    db.session.add(new_memo)
    db.session.commit()

    try:
        message = f"タイマーをセットしました！\n内容: {content}\n期限: {timer_datetime.strftime('%H:%M')}"
        line_bot_api.push_message(YOUR_LINE_ID, TextSendMessage(text=message))
    except Exception as e:
        print(f"LINE通知に失敗しました: {e}")


    return redirect('/')




#LINE連携
YOUR_LINE_ID = os.getenv('MY_USER_ID')
LINE_CHANNEL_ID = os.getenv('CHANNEL_ID')
LINE_CHANNEL_SECRET = os.getenv('MY_CHANNEL_SECRET')
LINE_CHANNEL_ACCES_TOKEN = os.getenv('CHANNEL_ACCESS_TOKEN')
line_bot_api = LineBotApi(LINE_CHANNEL_ACCES_TOKEN)
REDIRECT_URI = 'https://your-domain.com/callback'



# @app.route('/user/<int:user_id>')
# @login_required
# def user_page(user_id):
#     user = users.query.get_or_404(user_id)
#     return render_template('user.html', user=user)


# @app.route('/line/login/<int:user_id>')
# @login_required
# def line_login(user_id):
#     state = f"{user_id}_{secrets.token_urlsafe(16)}"
#     session['line_state'] = state
    
#     params = {
#         'response_type': 'code',
#         'client_id': LINE_CLIENT_ID,
#         'redirect_uri': REDIRECT_URI,
#         'state': state,
#         'scope': 'profile openid',
#         'bot_prompt': 'aggressive'
#     }

#     line_url = f"https://access.line.me/oauth2/v2.1/authorize?{urlencode(params)}"
#     return redirect(line_url)

# @app.route('/callback')
# @login_required
# def callback():
#     code = request.args.get('code')
#     returned_state = request.args.get('state')
#     stored_state = session.get('line_state')

#     if not stored_state or returned_state != stored_state:
#         return "無効なリクエストです（state不一致）", 400
#     session.pop('line_state', None)

#     token_url = "https://api.line.me/oauth2/v2.1/token"
#     token_data = {
#         'grant_type': 'authorization_code',
#         'code': code,
#         'redirect_uri': REDIRECT_URI,
#         'client_id': LINE_CHANNEL_ID,
#         'client_secret': LINE_CHANNEL_SECRET
#     }
#     token_res = requests.post(token_url, data=token_data).json()
#     line_user_id = token_res.get('userId')

#     if not line_user_id:
#         return "LINEユーザー情報の取得に失敗しました", 500

#     profile_url = f"https://api.line.me/v2/bot/profile/{line_user_id}"
#     headers = {"Authorization": f"Bearer {os.getenv('CHANNEL_ACCESS_TOKEN')}"}
#     profile_res = requests.get(profile_url, headers=headers)

#     if profile_res.status_code == 404:
#         return "公式LINEを友だち追加してから再度お試しください！", 403

#     app_user_id = int(returned_state.split('_')[0])
#     user = users.query.get(app_user_id)

#     if user:
#         user.line = line_user_id
#         db.session.commit()
#         return f"連携完了！ユーザーID:{app_user_id}さん、リマインダーを送れるようになりました。"
#     else:
#         return "ユーザーが見つかりません", 404


# #LINEMessagingAPI,BackgroundScheduler
# def check_and_send_notifications():
#     with app.app_context():
#         now = datetime.now(timezone(timedelta(hours=9)))
#         memos_to_notify = memo.query.filter(memo.timer <= now).all()

#         for m in memos_to_notify:
#             try:
#                 line_bot_api.push_message(users.line, TextSendMessage(text=f"{m.content}"))
#                 print(f"通知成功: {m.content}")
                
#                 db.session.delete(m)
#                 db.session.commit()
#                 print(f"削除完了: {m.content}")

#             except Exception as e:
#                 print(f"自動通知エラー: {e}")

# scheduler = BackgroundScheduler()
# scheduler.add_job(func=check_and_send_notifications, trigger="interval", minutes=1)
# scheduler.start()

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





if __name__ == "__main__":
    app.run(debug=True)