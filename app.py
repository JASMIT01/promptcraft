import os
from flask import Flask, render_template, redirect, url_for, request, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_bcrypt import Bcrypt
from google import genai
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = 'dev-portfolio-key-123'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'

db = SQLAlchemy(app)
bcrypt = Bcrypt(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# Initialize AI Client
gemini_client = genai.Client(api_key=os.getenv('GEMINI_API_KEY'))

# --- CRITICAL: INITIALIZE DATABASE TABLES ---
with app.app_context():
    db.create_all()

# --- DATABASE MODELS ---
class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(20), unique=True, nullable=False)
    password = db.Column(db.String(60), nullable=False)
    contents = db.relationship('AIContent', backref='author', lazy=True)

class AIContent(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    prompt = db.Column(db.String(255), nullable=False)
    result = db.Column(db.Text, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# --- APPLICATION ROUTES ---

@app.route('/')
def home():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        if not username or not password:
            flash("Please fill all fields", "danger")
            return redirect(url_for('register'))
        hashed_pw = bcrypt.generate_password_hash(password).decode('utf-8')
        if User.query.filter_by(username=username).first():
            flash('Username already exists.', 'danger')
            return redirect(url_for('register'))
        new_user = User(username=username, password=hashed_pw)
        db.session.add(new_user)
        db.session.commit()
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()
        if user and bcrypt.check_password_hash(user.password, password):
            login_user(user)
            return redirect(url_for('dashboard'))
        flash('Login Unsuccessful.', 'danger')
    return render_template('login.html')

@app.route('/dashboard', methods=['GET', 'POST'])
@login_required
def dashboard():
    ai_response = None
    
    if request.method == 'POST':
        user_prompt = request.form.get('prompt')
        # This is where the AI works
        response = gemini_client.models.generate_content(
            model='gemini-1.5-flash', 
            contents=user_prompt
        )
        ai_response = response.text # The Chef puts the food on the plate
        
    # We just return the page, carrying the 'ai_response' plate with us
    return render_template('dashboard.html', ai_response=ai_response)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)
