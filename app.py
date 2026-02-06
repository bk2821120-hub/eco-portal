from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
import os
from datetime import datetime
import mimetypes

mimetypes.add_type('text/css', '.css')
mimetypes.add_type('application/javascript', '.js')

app = Flask(__name__, static_url_path='/static', static_folder='static', template_folder='templates')
app.config['SECRET_KEY'] = 'your-secret-key-change-this'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Models
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(100), nullable=False)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)

class Issue(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    location = db.Column(db.String(100), nullable=False)
    issue_type = db.Column(db.String(50), nullable=False)
    description = db.Column(db.Text, nullable=False)
    image_filename = db.Column(db.String(100), nullable=True)
    date_reported = db.Column(db.DateTime, default=datetime.utcnow)

class ContactMessage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), nullable=False)
    subject = db.Column(db.String(100), nullable=False)
    message = db.Column(db.Text, nullable=False)
    date_sent = db.Column(db.DateTime, default=datetime.utcnow)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Routes
@app.route('/')
def home():
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter((User.username == username) | (User.email == username)).first()
        
        if user and check_password_hash(user.password_hash, password):
            login_user(user)
            return redirect(url_for('home'))
        else:
            flash('Invalid username or password', 'error')
            
    return render_template('login.html')

import csv
import os
from datetime import datetime

# ... (Imports)

# Local "Sheet" Setup (CSV)
def add_user_to_sheet(full_name, email, username):
    file_exists = os.path.isfile('user_records.csv')
    
    try:
        with open('user_records.csv', 'a', newline='') as f:
            writer = csv.writer(f)
            # Write header if new file
            if not file_exists:
                writer.writerow(['Full Name', 'Email', 'Username', 'Signup Date'])
            
            # Write user data
            writer.writerow([full_name, email, username, datetime.now().strftime("%Y-%m-%d %H:%M:%S")])
        return True
    except Exception as e:
        print(f"Error saving to CSV: {e}")
        return False

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        full_name = request.form.get('full_name')
        email = request.form.get('email')
        username = request.form.get('username')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        
        if password != confirm_password:
            flash('Passwords do not match', 'error')
            return redirect(url_for('signup'))
            
        if User.query.filter_by(username=username).first() or User.query.filter_by(email=email).first():
            flash('Username or Email already exists', 'error')
            return redirect(url_for('signup'))
            
        new_user = User(
            full_name=full_name,
            email=email,
            username=username,
            password_hash=generate_password_hash(password)
        )
        db.session.add(new_user)
        db.session.commit()
        
        # Save to Local Record Sheet
        add_user_to_sheet(full_name, email, username)
        
        flash('Account created successfully! Please login.', 'success')
        return redirect(url_for('login'))
        
    return render_template('signup.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/news')
def news():
    # Mock data for news
    news_items = [
        {
            'title': 'Global Summit on Climate Change Reaches New Agreement',
            'date': '2023-10-25',
            'description': 'World leaders have agreed to cut carbon emissions by 40%...',
            'image': 'climate_summit.jpg',
            'category': 'Climate Change'
        },
        {
            'title': 'New Ocean Cleaning Technology Deployed',
            'date': '2023-10-22',
            'description': 'A massive floating barrier is set to clean up the Great Pacific Garbage Patch...',
            'image': 'ocean_cleanup.jpg',
            'category': 'Pollution Control'
        },
        {
            'title': 'Endangered Tiger Population Sees Increase',
            'date': '2023-10-20',
            'description': 'Conservation efforts have led to a 10% rise in the wild tiger population...',
            'image': 'tiger.jpg',
            'category': 'Wildlife Protection'
        },
        {
            'title': 'Solar Power Adoption Hits Record High',
            'date': '2023-10-18',
            'description': 'Renewable energy sources are now providing more power than coal...',
            'image': 'solar_panels.jpg',
            'category': 'Renewable Energy'
        },
        {
            'title': 'City Bans Single-Use Plastics',
            'date': '2023-10-15',
            'description': 'Major metropolitan area implements strict ban on plastic bags and straws...',
            'image': 'plastic_ban.jpg',
            'category': 'Pollution'
        }
    ]
    return render_template('news.html', news=news_items)

@app.route('/report', methods=['GET', 'POST'])
@login_required
def report():
    if request.method == 'POST':
        location = request.form.get('location')
        issue_type = request.form.get('issue_type')
        description = request.form.get('description')
        # Image handling would go here (saving file)
        
        new_issue = Issue(
            user_id=current_user.id,
            location=location,
            issue_type=issue_type,
            description=description
        )
        db.session.add(new_issue)
        db.session.commit()
        flash('Issue reported successfully. Thank you for your contribution!', 'success')
        return redirect(url_for('home')) # Or redirect to a 'my reports' page
        
    return render_template('report.html')

@app.route('/my-reports')
@login_required
def my_reports():
    user_reports = Issue.query.filter_by(user_id=current_user.id).order_by(Issue.date_reported.desc()).all()
    return render_template('my_reports.html', reports=user_reports)


@app.route('/contact', methods=['GET', 'POST'])
def contact():
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        subject = request.form.get('subject')
        message = request.form.get('message')
        
        new_msg = ContactMessage(
            name=name,
            email=email,
            subject=subject,
            message=message
        )
        db.session.add(new_msg)
        db.session.commit()
        flash('Message sent successfully! We will get back to you soon.', 'success')
        return redirect(url_for('contact'))
        
    return render_template('contact.html')

@app.route('/climate')
def climate():
    return render_template('climate.html')

@app.route('/pollution')
def pollution():
    return render_template('pollution.html')

@app.route('/wildlife')
def wildlife():
    return render_template('wildlife.html')

with app.app_context():
    db.create_all()

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
