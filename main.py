import os
from flask import Flask, render_template, request, redirect, session, url_for
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from werkzeug.security import check_password_hash, generate_password_hash
from datetime import datetime

app_name = 'School'  # Change this to your desired app name, e.g., 'University' or 'Your Company Name'
currency_symbol = '€'  # Change this to your desired currency symbol, e.g., '$' or '£'

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
    prename = db.Column(db.String(50))
    name = db.Column(db.String(50))
    nfc_tag_id = db.Column(db.String(100), unique=True)
    barcode = db.Column(db.String(100), unique=True)
    balance = db.Column(db.Float, default=0.0)


class TransactionsPOS(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('students.id'), nullable=True)
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
    student_id = db.Column(db.Integer, db.ForeignKey('students.id'), nullable=False)
    seller_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    transaction_date = db.Column(db.DateTime, default=datetime.utcnow)


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
        return redirect(url_for('index'))
    session_user = db.session.get(User, session['user_id'])
    return render_template('user.html', user_name=session_user.username, app_name=app_name)


@app.route('/dashboard', methods=['GET', 'POST'])
def dashboard():
    if 'username' not in session:
        return redirect(url_for('index'))
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
    products = Product.query.all()
    if request.method == 'POST':
        cart = []
        for product in products:
            if f'product_{product.id}' in request.form:
                quantity = int(request.form.get(f'quantity_{product.id}', 1))
                cart.append({'product_id': product.id, 'quantity': quantity})
        session['cart'] = cart
        return redirect(url_for('checkout'))
    return render_template('kiosk.html', app_name=app_name, currency_symbol=currency_symbol,
                           user_name=session_user.username, products=products)


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
        return redirect(url_for('login',
                                error="You do not have permission to access the admin dashboard. Please login as an admin."))
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


@app.route('/student', methods=['GET', 'POST'])
def student():
    if request.method == 'POST':
        barcode_or_nfc = request.form.get('barcode_or_nfc')
        requested_student = Students.query.filter_by(barcode=barcode_or_nfc).first()
        if not requested_student:
            requested_student = Students.query.filter_by(nfc_tag_id=barcode_or_nfc).first()
        if requested_student:
            return redirect(url_for('student_options', id=requested_student.id))
        else:
            return render_template('student.html', error="Student not found", app_name=app_name)
    return render_template('student.html', app_name=app_name)


@app.route('/student/options/<int:id>', methods=['GET', 'POST'])
def student_options(id):
    requested_student = db.session.get(Students, id)
    if requested_student:
        transactions = db.session.query(TransactionsPOS).filter_by(student_id=requested_student.id).all()
        transactions_with_items = []
        for transaction in transactions:
            transaction_items = db.session.query(TransactionItems).filter_by(transaction_id=transaction.id).all()
            transactions_with_items.append({
                'transaction': transaction,
                'transaction_items': [{'product': db.session.get(Product, item.product_id), 'quantity': item.quantity}
                                      for item in transaction_items]
            })

        return render_template('student_options.html',
                               student_name=requested_student.prename + " " + requested_student.name,
                               balance=requested_student.balance, transactions=transactions_with_items,
                               app_name=app_name, currency_symbol=currency_symbol)
    else:
        return render_template('student_options.html', error="Student not found", app_name=app_name,
                               currency_symbol=currency_symbol)


@app.route('/student/list', methods=['GET', 'POST'])
def students_list():
    if not check_permissions(['isAdmin']):
        return redirect(
            url_for('login', error="You do not have permission to view or edit students. Please login as an admin."))
    students = Students.query.all()
    if request.method == 'POST':
        for student in students:
            student.prename = request.form.get(f'prename_{student.id}')
            student.name = request.form.get(f'name_{student.id}')
            student.barcode = request.form.get(f'barcode_{student.id}')
            student.nfc_tag_id = request.form.get(f'nfc_tag_id_{student.id}')
        db.session.commit()
        return redirect(url_for('students_list'))
    return render_template('student_list.html', students=students, app_name=app_name, currency_symbol=currency_symbol)


@app.route('/student/add', methods=['GET', 'POST'])
def add_students():
    if not check_permissions(['isAdmin']):
        return redirect(url_for('login', error="You do not have permission to add students. Please login as an admin."))
    if request.method == 'POST':
        prename = request.form.get('prename')
        name = request.form.get('name')
        nfc_tag_id = request.form.get('nfc_tag_id')
        barcode = request.form.get('barcode')
        balance = 0
        new_student = Students(prename=prename, name=name, nfc_tag_id=nfc_tag_id, barcode=barcode, balance=balance)
        db.session.add(new_student)
        db.session.commit()
        return redirect(url_for('admin_dashboard'))
    return render_template('add_students.html', app_name=app_name)


@app.route('/add_money', methods=['GET', 'POST'])
def add_money():
    if not check_permissions(['allow_sell']):
        return redirect(url_for('login', error="You do not have permission to sell. Please login as a seller."))
    if request.method == 'POST':
        tag_or_barcode = request.form.get('tag_or_barcode')
        amount = request.form.get('amount')
        if not amount:
            return render_template('add_money.html', error="Amount is required", app_name=app_name,
                                   currency_symbol=currency_symbol)
        try:
            amount = round(float(amount), 2)
            if amount <= 0:
                raise ValueError("Amount must be positive")
        except ValueError:
            return render_template('add_money.html', error="Invalid amount format", app_name=app_name,
                                   currency_symbol=currency_symbol)

        requested_student = Students.query.filter(
            (Students.nfc_tag_id == tag_or_barcode) | (Students.barcode == tag_or_barcode)).first()
        if requested_student:
            requested_student.balance = round(requested_student.balance + amount, 2)
            new_load_transaction = TransactionsLoadMoney(student_id=requested_student.id, seller_id=session['user_id'],
                                                         amount=amount)
            db.session.add(new_load_transaction)
            db.session.commit()
            return redirect(url_for('kiosk'))
        else:
            return render_template('add_money.html', error="Student not found", app_name=app_name,
                                   currency_symbol=currency_symbol)
    return render_template('add_money.html', app_name=app_name, currency_symbol=currency_symbol)


@app.route('/product/add', methods=['GET', 'POST'])
def add_product():
    if not check_permissions(['isAdmin']):
        return redirect(url_for('login', error="You do not have permission to add products. Please login as an admin."))
    if request.method == 'POST':
        name = request.form.get('name')
        price = request.form.get('price')
        try:
            price = round(float(price), 2)
            if price <= 0:
                raise ValueError("Price must be positive")
        except ValueError:
            return render_template('add_product.html', error="Invalid price format", app_name=app_name,
                                   currency_symbol=currency_symbol)
        new_product = Product(name=name, price=price)
        db.session.add(new_product)
        db.session.commit()
        return redirect(url_for('admin_dashboard'))
    return render_template('add_product.html', app_name=app_name, currency_symbol=currency_symbol)


@app.route('/product/list', methods=['GET', 'POST'])
def product_list():
    if not check_permissions(['isAdmin']):
        return redirect(
            url_for('login', error="You do not have permission to view or edit products. Please login as an admin."))
    products = Product.query.all()
    if request.method == 'POST':
        for product in products:
            product.name = request.form.get(f'name_{product.id}')
            product.price = request.form.get(f'price_{product.id}')
        db.session.commit()
        return redirect(url_for('product_list'))
    return render_template('product_list.html', products=products, app_name=app_name, currency_symbol=currency_symbol)


@app.route('/checkout', methods=['GET', 'POST'])
def checkout():
    if 'cart' not in session or not session['cart']:
        return redirect(url_for('kiosk'))

    cart = session['cart']
    product_ids = [item['product_id'] for item in cart]
    products = Product.query.filter(Product.id.in_(product_ids)).all()

    cart_products = []
    total_price = 0.0
    for item in cart:
        for product in products:
            if product.id == item['product_id']:
                cart_products.append({'product': product, 'quantity': item['quantity']})
                total_price += product.price * item['quantity']
    total_price = round(total_price, 2)

    if request.method == 'POST':
        payment_method = request.form.get('payment_method')
        barcode_or_nfc = request.form.get('barcode_or_nfc', '').strip()

        if payment_method == 'balance':
            student = Students.query.filter(
                (Students.barcode == barcode_or_nfc) | (Students.nfc_tag_id == barcode_or_nfc)).first()
            if student:
                if student.balance >= total_price:
                    student.balance = round(student.balance - total_price, 2)
                    new_transaction = TransactionsPOS(seller_id=session['user_id'], student_id=student.id,
                                                      pay_with_cash=False, total_amount=total_price)
                    db.session.add(new_transaction)
                    db.session.commit()

                    for item in cart:
                        new_item = TransactionItems(transaction_id=new_transaction.id, product_id=item['product_id'],
                                                    quantity=item['quantity'])
                        db.session.add(new_item)
                    db.session.commit()
                    session['cart'] = []
                    return redirect(url_for('kiosk'))
                else:
                    return render_template('checkout.html', error="Not enough balance", app_name=app_name,
                                           products=cart_products, total_price=total_price,
                                           currency_symbol=currency_symbol)
            else:
                return render_template('checkout.html', error="Student not found", app_name=app_name,
                                       products=cart_products, total_price=total_price, currency_symbol=currency_symbol)

        elif payment_method == 'cash':
            new_transaction = TransactionsPOS(seller_id=session['user_id'], student_id=None, pay_with_cash=True,
                                              total_amount=total_price)
            db.session.add(new_transaction)
            db.session.commit()

            for item in cart:
                new_item = TransactionItems(transaction_id=new_transaction.id, product_id=item['product_id'],
                                            quantity=item['quantity'])
                db.session.add(new_item)
            db.session.commit()
            session['cart'] = []
            return redirect(url_for('kiosk'))

    return render_template('checkout.html', app_name=app_name, products=cart_products, total_price=total_price,
                           currency_symbol=currency_symbol)


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
