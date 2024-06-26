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
    add_seller = db.Column(db.Boolean, default=False)
    add_students = db.Column(db.Boolean, default=False)
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
    admin_user = User(username='admin', password=generate_password_hash('password'), add_seller=True, add_students=True)
    db.session.add(admin_user)
    db.session.commit()


if not os.path.exists('instance/db.db'):
    with app.app_context():
        db.create_all()
        create_default_user()
        print("Datenbank erstellt.")


# Permission Check
# Check if user is logged in
#  if 'username' not in session:
#      return redirect(url_for('login'))
#
# Check if user has permission to add seller
#  if 'username' not in session or not session['add_seller']:
#      return redirect(url_for('login'))
#
# Check if user has permission to add students
#  if 'username' not in session or not session['add_students']:
#      return redirect(url_for('login'))
#
# Check if user has permission to sell
#  if 'username' not in session or not session['allow_sell']:
#      return redirect(url_for('login'))

@app.route('/')
def index():
    return render_template('index.html', app_name=app_name)


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        session_user = User.query.filter_by(username=username).first()
        if session_user and check_password_hash(session_user.password, password):
            session['user_id'] = session_user.id
            return redirect(url_for('dashboard'))
        else:
            return render_template('login.html', error="Invalid username or password")
    return render_template('login.html', app_name=app_name)


@app.route('/dashboard', methods=['GET', 'POST'])
def dashboard():
    if 'username' not in session:
        return redirect(url_for('login'))
    session_user = User.query.get(session['user_id'])
    return render_template('dashboard.html', user_name=session_user.username, app_name=app_name)


@app.route('/user', methods=['GET', 'POST'])
def user():
    if 'username' not in session:
        return redirect(url_for('login'))
    return render_template('user.html', user_name=session_user.username, app_name=app_name)


@app.route('/kiosk', methods=['GET', 'POST'])
def kiosk():
    if 'username' not in session or not session['allow_sell']:
        return redirect(url_for('login'))
    return render_template('kiosk.html', app_name=app_name)


@app.route('/logout')
def logout():
    session.pop('username', None)
    return redirect(url_for('index'))


if __name__ == '__main__':
    app.run(debug=True, port=5500)
