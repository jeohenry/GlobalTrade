from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
from flask_mail import Mail, Message
from itsdangerous import URLSafeTimedSerializer, SignatureExpired, BadSignature
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
from sqlalchemy import func
import requests
import uuid
from werkzeug.utils import secure_filename
import os
from dotenv import load_dotenv

# load environment variables
 
load_dotenv()

# Initialize Flask app

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')


# set up database 
app.config['UPLOAD_FOLDER'] = 'static/upload'
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
app.config['MAX_CONTENT_LENGTH'] = 2 * 1024 * 1024  # 2MB max file size
db_url = os.getenv("DATABASE_URL", "sqlite:///investment.db")
app.config['SQLALCHEMY_DATABASE_URI'] = db_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = os.getenv('MAIL_USERNAME')
app.config['MAIL_PASSWORD'] = os.getenv('MAIL_PASSWORD')
app.config['MAIL_DEFAULT_SENDER'] = os.getenv('MAIL_USERNAME')

db = SQLAlchemy(app)
mail = Mail(app)
s = URLSafeTimedSerializer(app.secret_key)

#-------------------- MODELS --------------------

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(100), nullable=False)
    username = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    country = db.Column(db.String(100))
    gender = db.Column(db.String(20))
    age = db.Column(db.Integer)
    password = db.Column(db.String(255), nullable=False)
    confirmed = db.Column(db.Boolean, default=False)
    profile_image = db.Column(db.String(255), default='default.jpg')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Investment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    investment_type = db.Column(db.String(100))
    amount = db.Column(db.Float)
    status = db.Column(db.String(50), default='pending')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Transaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    amount = db.Column(db.Float)
    payment_status = db.Column(db.String(50), default='unpaid')
    flutterwave_tx_ref = db.Column(db.String(100))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Withdrawal(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    user = db.relationship('User', backref='withdrawals')  # ← Add this line
    amount = db.Column(db.Float)
    method = db.Column(db.String(50))
    wallet = db.Column(db.String(100))
    status = db.Column(db.String(50), default='pending')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

#----CREATE TABLES AUTOMATICALLY---

@app.before_first_request
def create_tables():
    with app.app_context():
        db.create_all()
        print("✅ Tables created.")
#-------------------- ROUTES --------------------

@app.route('/')
def home():
    return render_template("base.html")

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        existing_user = User.query.filter_by(email=request.form['email']).first()
        if existing_user:
            flash("Email already registered.", "danger")
            return redirect(url_for('register'))

        hashed_pw = generate_password_hash(request.form['password'])  
        user = User(  
            full_name=request.form['full_name'],  
            username=request.form['username'],  
            email=request.form['email'],  
            country=request.form['country'],  
            gender=request.form['gender'], 
            age=int(request.form['age']),
            password=hashed_pw,  
            confirmed=False  
        )  
        db.session.add(user)  
        db.session.commit()  

        token = s.dumps(user.email, salt='email-confirm')  
        confirm_url = url_for('confirm_email', token=token, _external=True)  
        html = render_template('email_confirmation.html', confirm_url=confirm_url)  
        msg = Message("Confirm Your Email", recipients=[user.email], html=html)  
        mail.send(msg)  

        flash("Check your email to confirm registration.", "info")  
        return redirect(url_for('home'))  
    return render_template('register.html')

@app.route('/confirm/<token>')
def confirm_email(token):
    try:
        email = s.loads(token, salt='email-confirm', max_age=3600)
        user = User.query.filter_by(email=email).first()
        if user:
            user.confirmed = True
            db.session.commit()
            session['user_id'] = user.id
            session['username'] = user.username
            session['email'] = user.email
            flash("Email confirmed successfully!", "success")
            return redirect(url_for('profile'))
    except SignatureExpired:
        flash("Confirmation link expired.", "warning")
    except BadSignature:
        flash("Invalid confirmation token.", "danger")
    return redirect(url_for('register'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        user = User.query.filter_by(email=email).first()

        if user and check_password_hash(user.password, password):  
            if not user.confirmed:  
                flash("Please confirm your email before logging in.", "warning")  
                return redirect(url_for('login'))  
            session['user_id'] = user.id  
            session['username'] = user.username  
            session['email'] = user.email  
            flash("Login successful!", "success")  
            return redirect(url_for('profile'))  
        else:  
            flash("Invalid email or password.", "danger")  
            return redirect(url_for('login'))  

    return render_template('login.html')

@app.route('/profile')
def profile():
    if 'user_id' not in session:
        return redirect(url_for('register'))
    user = User.query.get(session['user_id'])
    investments = Investment.query.filter_by(user_id=user.id).all()
    transactions = Transaction.query.filter_by(user_id=user.id).all()
    withdrawals = Withdrawal.query.filter_by(user_id=user.id).all()
    return render_template('profile.html', user=user, investments=investments, transactions=transactions, withdrawals=withdrawals)

@app.route('/edit-profile', methods=['GET', 'POST'])
def edit_profile():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user = User.query.get(session['user_id'])  

    if request.method == 'POST':  
        user.full_name = request.form['full_name']  
        user.username = request.form['username']  
        user.country = request.form['country']  
        user.gender = request.form['gender']  
        user.age = request.form['age']  
# Optional: Handle password change
    if   request.form.get('password'):
        user.password = generate_password_hash(request.form['password'])
        if 'profile_image' in request.files:  
            image = request.files['profile_image']  
            if image.filename != '':  
                filename = secure_filename(image.filename)  
                ext = filename.split('.')[-1]  
                unique_name = f"{uuid.uuid4().hex}.{ext}"  
                image.save(os.path.join(app.config['UPLOAD_FOLDER'], unique_name))  
                user.profile_image = unique_name  

        db.session.commit()  
        flash('Profile updated successfully.', 'success')  
        return redirect(url_for('profile'))  

    return render_template('edit_profile.html', user=user)

@app.route('/upload-profile-pic', methods=['POST'])
def upload_profile_pic():
    if 'user_id' not in session:
        flash("Login required.", "danger")
        return redirect(url_for('login'))

    user = User.query.get(session['user_id'])

    if 'profile_image' in request.files:
        image = request.files['profile_image']
        if image and image.filename != '':
            filename = secure_filename(image.filename)
            ext = filename.split('.')[-1]
            unique_name = f"{uuid.uuid4().hex}.{ext}"
            image_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_name)
            image.save(image_path)
            user.profile_image = unique_name
            db.session.commit()
            flash("Profile image updated successfully.", "success")
        else:
            flash("No image selected.", "warning")
    else:
        flash("No file uploaded.", "danger")

    return redirect(url_for('profile'))

@app.route('/invest', methods=['POST'])
def invest():
    if 'user_id' not in session:
        return redirect(url_for('register'))

    investment = Investment(  
        user_id=session['user_id'],  
        investment_type=request.form['investment_type'],  
        amount=float(request.form['amount']),
        status='pending'  
    )  
    db.session.add(investment)  
    db.session.commit()  
    flash("Investment created successfully.", "success")  
    return redirect(url_for('profile'))

@app.route('/pay', methods=['POST'])
def pay():
    if 'user_id' not in session:
        return redirect(url_for('register'))

    user = User.query.get(session['user_id'])  
    amount = float(request.form['amount'])  
    tx_ref = f"INVEST-{datetime.utcnow().timestamp()}"  

    transaction = Transaction(  
        user_id=user.id,  
        amount=amount,  
        flutterwave_tx_ref=tx_ref,  
        payment_status='unpaid'  
    )  
    db.session.add(transaction)  
    db.session.commit()  

    payload = {  
        "tx_ref": tx_ref,  
        "amount": amount,  
        "currency": "USD",  
        "redirect_url": url_for('payment_callback', _external=True),  
        "payment_options": "card,banktransfer",  
        "customer": { "email": user.email },  
        "customizations": {
            "title": "Global Trade Options",
            "description": "Investment Payment"
        }  
    }  

    headers = {
        "Authorization": f"Bearer {os.getenv('FLUTTERWAVE_SECRET_KEY')}",
        "Content-Type": "application/json"
    }  

    response = requests.post('https://api.flutterwave.com/v3/payments', json=payload, headers=headers)  
    if response.status_code == 200:
        return redirect(response.json()['data']['link'])  
    flash("Payment initiation failed.", "danger")  
    return redirect(url_for('profile'))

@app.route('/payment/callback')
def payment_callback():
    tx_ref = request.args.get('tx_ref')
    status = request.args.get('status')
    if status == 'successful':
        tx = Transaction.query.filter_by(flutterwave_tx_ref=tx_ref).first()
        if tx:
            tx.payment_status = 'paid'
            db.session.commit()
            flash("Payment successful!", "success")
    else:
        flash("Payment failed or cancelled.", "warning")
    return redirect(url_for('profile'))

@app.route('/withdraw', methods=['POST'])
def withdraw():
    if 'user_id' not in session:
        return redirect(url_for('register'))

    user_id = session['user_id']  
    try:  
        amount = float(request.form['amount'])  
    except ValueError:  
        flash("Invalid amount.", "danger")  
        return redirect(url_for('profile'))  

    method = request.form['method']  
    wallet = request.form['wallet']  

    total_paid = db.session.query(func.sum(Transaction.amount)).filter_by(user_id=user_id, payment_status='paid').scalar() or 0.0  
    total_withdrawn = db.session.query(func.sum(Withdrawal.amount)).filter_by(user_id=user_id).scalar() or 0.0  
    available = total_paid - total_withdrawn  

    if amount > available:  
        flash("Withdrawal exceeds available balance.", "danger")  
        return redirect(url_for('profile'))  

    withdrawal = Withdrawal(user_id=user_id, amount=amount, method=method, wallet=wallet)  
    db.session.add(withdrawal)  
    db.session.commit()  

    user = User.query.get(user_id)  
    msg = Message('Withdrawal Request', recipients=['admin@yourdomain.com'])  
    msg.body = f"{user.username} requested a withdrawal of ${amount} via {method}."  
    mail.send(msg)  

    flash("Withdrawal request submitted.", "info")  
    return redirect(url_for('profile'))

@app.route('/calculate-returns')
def calculate_returns():
    now = datetime.utcnow()
    completed_txs = Transaction.query.filter_by(payment_status='paid').all()
    results = []
    for tx in completed_txs:
        if (now - tx.created_at).days >= 7:
            return_amount = round(tx.amount * 1.3, 2)
            user = User.query.get(tx.user_id)
            results.append({'username': user.username, 'amount': tx.amount, 'return': return_amount})
    return {"returns": results}

@app.route('/admin')
def admin():
    if not session.get('admin'):
        return redirect(url_for('admin_login'))
    users = User.query.all()
    transactions = Transaction.query.all()
    investments = Investment.query.all()
    withdrawals = Withdrawal.query.all()
    return render_template('admin.html', users=users, transactions=transactions, investments=investments, withdrawals=withdrawals)

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        if request.form['username'] == os.getenv('ADMIN_USERNAME') and request.form['password'] == os.getenv('ADMIN_PASSWORD'):
            session['admin'] = True
            flash("Admin login successful!", "success")
            return redirect(url_for('admin'))
        flash("Invalid credentials", "danger")
    return render_template('admin_login.html')

@app.route('/admin/approve-withdrawal/<int:withdrawal_id>', methods=['POST'])
def approve_withdrawal(withdrawal_id):
    withdrawal = Withdrawal.query.get(withdrawal_id)
    if withdrawal:
        withdrawal.status = 'approved'
        db.session.commit()
        user = User.query.get(withdrawal.user_id)
        msg = Message('Withdrawal Approved', recipients=[user.email])
        msg.body = f"Your withdrawal of ${withdrawal.amount} has been approved."
        mail.send(msg)
        flash("Withdrawal approved.", "success")
    return redirect(url_for('admin'))

@app.route('/admin/complete/<int:transaction_id>', methods=['POST'])
def mark_transaction_complete(transaction_id):
    tx = Transaction.query.get(transaction_id)
    if tx:
        tx.payment_status = 'paid'
        db.session.commit()
        flash("Transaction marked as paid.", "success")
    return redirect(url_for('admin'))

@app.route('/logout')
def logout():
    session.clear()
    flash("Logged out successfully.", "info")
    return redirect(url_for('home'))

#-------------------- INITIALIZER --------------------

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000)) 
    app.run(host='0.0.0.0', port=port, debug=False)

    