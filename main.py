import os
from flask import Flask, render_template, request, redirect, session, url_for
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from werkzeug.security import check_password_hash, generate_password_hash
from datetime import datetime

app_name = 'School'  # Change this to your desired app name, e.g., 'University' or 'Your Company Name'

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///db.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_ECHO'] = True
app.secret_key = 'secret_salt'  # Change this on Public build!
db = SQLAlchemy(app)


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True)
    password = db.Column(db.String(128))
    allow_sell = db.Column(db.Boolean, default=False)
    isAdmin = db.Column(db.Boolean, default=False)
    total_earnings = db.Column(db.Float, default=0.0)


class Students(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nfc_tag_id = db.Column(db.String(100), unique=True)
    barcode = db.Column(db.String(100), unique=True)
    balance = db.Column(db.Float, default=0.0)


class TransactionsPOS(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('students.id'))
    seller_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    pay_with_cash = db.Column(db.Boolean, default=False)
    pay_with_credit = db.Column(db.Boolean, default=False)
    total_amount = db.Column(db.Float, default=0.0)
    transaction_date = db.Column(db.DateTime, default=datetime.utcnow)
    items = db.relationship('TransactionItems', backref='transaction', lazy=True)


class TransactionItems(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    transaction_id = db.Column(db.Integer, db.ForeignKey('transactions_pos.id'))
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'))
    quantity = db.Column(db.Integer, default=1)


class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    price = db.Column(db.Float)


class TransactionsLoadMoney(db.Model):
    id = db.Column(db.Integer, primary_key=True)


def create_default_user():
    admin_user = User(username='admin', password=generate_password_hash('password'), isAdmin=True)
    db.session.add(admin_user)
    db.session.commit()


if not os.path.exists('instance/db.db'):
    with app.app_context():
        db.create_all()
        create_default_user()
        print("Datenbank erstellt.")


@app.route('/')
def index():
    return render_template('index.html', app_name=app_name)


@app.route('/login', methods=['GET', 'POST'])
def login():
    error = request.args.get('error', '')
    if 'username' in session:
        return redirect(url_for('dashboard'))
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        session_user = User.query.filter_by(username=username).first()
        if session_user and check_password_hash(session_user.password, password):
            session['username'] = username
            session['user_id'] = session_user.id
            return redirect(url_for('dashboard'))
        else:
            return render_template('login.html', app_name=app_name, error="Invalid username or password")
    return render_template('login.html', app_name=app_name, error=error)


@app.route('/user', methods=['GET', 'POST'])
def user():
    if 'username' not in session:
        return redirect(url_for('login', error="You do not have permission to access the user page. Please login."))
    session_user = db.session.get(User, session['user_id'])
    return render_template('user.html', user_name=session_user.username, app_name=app_name)


@app.route('/dashboard', methods=['GET', 'POST'])
def dashboard():
    if 'username' not in session:
        return redirect(url_for('login', error="You do not have permission to access the dashboard. Please login."))
    session_user = db.session.get(User, session['user_id'])
    return render_template('dashboard.html', user_name=session_user.username, app_name=app_name)


@app.route('/add_seller', methods=['GET', 'POST'])
def add_seller():
    if not check_permissions(['isAdmin']):
        return redirect(url_for('login', error="You do not have permission to add sellers. Please login as an admin."))
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        allow_sell = request.form.get('allow_sell') == 'on'
        isAdmin = request.form.get('isAdmin') == 'on'
        new_seller = User(username=username, password=generate_password_hash(password), allow_sell=allow_sell,
                          isAdmin=isAdmin)
        db.session.add(new_seller)
        db.session.commit()
        return redirect(url_for('dashboard'))
    return render_template('add_seller.html', app_name=app_name)


@app.route('/kiosk', methods=['GET', 'POST'])
def kiosk():
    if not check_permissions(['allow_sell']):
        return redirect(url_for('login', error="You do not have permission to sell. Please login as a seller."))
    session_user = db.session.get(User, session['user_id'])
    return render_template('kiosk.html', app_name=app_name, user_name=session_user.username)


@app.route('/change_password', methods=['GET', 'POST'])
def change_password():
    if 'username' not in session:
        return redirect(url_for('index'))
    if request.method == 'POST':
        old_password = request.form.get('old_password')
        new_password = request.form.get('new_password')
        session_user = User.query.filter_by(username=session['username']).first()
        if session_user and check_password_hash(session_user.password, old_password):
            session_user.password = generate_password_hash(new_password)
            db.session.commit()
            return redirect(url_for('user'))
        else:
            return render_template('change_password.html', app_name=app_name, error="Old password is incorrect.")
    return render_template('change_password.html', app_name=app_name)


@app.route('/logout')
def logout():
    session.pop('username', None)
    return redirect(url_for('index'))


@app.route('/admin_dashboard', methods=['GET', 'POST'])
def admin_dashboard():
    if not check_permissions(['isAdmin']):
        return redirect(url_for('login', error="You do not have permission to access the admin dashboard. Please login as an admin."))
    users = User.query.all()
    return render_template('admin_dashboard.html', app_name=app_name, users=users)


@app.route('/update_user', methods=['POST'])
def update_user():
    if not check_permissions(['isAdmin']):
        return redirect(url_for('login', error="You do not have permission to update users. Please login as an admin."))
    user_id = request.form.get('user_id')
    username = request.form.get('username')
    allow_sell = request.form.get('allow_sell') == 'on'
    isAdmin = request.form.get('isAdmin') == 'on'
    session_user = User.query.get(user_id)
    if session_user:
        session_user.username = username
        session_user.allow_sell = allow_sell
        session_user.isAdmin = isAdmin
        db.session.commit()
        return redirect(url_for('admin_dashboard'))
    else:
        return redirect(url_for('admin_dashboard', error="User not found."))


def check_permissions(required_permissions):
    if 'username' not in session:
        return False
    session_user = db.session.get(User, session['user_id'])
    for permission in required_permissions:
        if not getattr(session_user, permission):
            return False
    return True


if __name__ == '__main__':
    app.run(debug=True, port=5500)
