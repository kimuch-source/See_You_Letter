from flask import Flask
from flask import request, redirect, render_template
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin,LoginManager, login_user, logout_user, login_required
from werkzeug.security import generate_password_hash, check_password_hash
import os

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://postgres:0784@localhost/see_you_letter_db'
app.config['SECRET_KEY'] = os.urandom(24)
db = SQLAlchemy()
db.init_app(app)

login_manager = LoginManager()
login_manager.init_app(app)

class users(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_name = db.Column(db.String(30), unique=True)
    password = db.Column(db.String(255),)
    line = db.Column(db.String(20))


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
    


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect('login')


if __name__ == "__main__":
    app.run(debug=True)