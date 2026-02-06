from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
import os
from datetime import datetime
import mimetypes
import logging
import feedparser
import re
import csv
logging.basicConfig(level=logging.DEBUG)

app = Flask(__name__, static_url_path='/static', static_folder='static', template_folder='templates')
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'default-key-for-dev')
# Use absolute path for database to avoid issues in production
basedir = os.path.abspath(os.path.dirname(__file__))
if not os.path.exists(os.path.join(basedir, 'instance')):
    os.makedirs(os.path.join(basedir, 'instance'))

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'instance', 'database.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

@app.errorhandler(500)
def handle_500(e):
    return f"Internal Server Error: {str(e)}", 500

@app.route('/debug-info')
def debug_info():
    return {
        "cwd": os.getcwd(),
        "instance_exists": os.path.exists('instance'),
        "db_uri": app.config['SQLALCHEMY_DATABASE_URI']
    }

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
    # Elite Educational Sources for EcoPortal
    feeds = [
        ("https://feeds.bbci.co.uk/news/science_and_environment/rss.xml", "Climate Change"),
        ("https://www.sciencedaily.com/rss/earth_climate/environmental_science.xml", "Green Tech"),
        ("https://news.google.com/rss/search?q=pollution+awareness+india&hl=en-IN&gl=IN&ceid=IN:en", "Pollution"),
        ("https://news.google.com/rss/search?q=wildlife+conservation+India&hl=en-IN&gl=IN&ceid=IN:en", "Wildlife")
    ]
    
    educational_news = []
    
    # Category-based learning data
    learning_repo = {
        "Climate Change": {
            "exp": "Climate change is caused by the increase of greenhouse gases like CO2 in our atmosphere, which trap heat and warm the planet. This leads to melting ice caps and rising sea levels.",
            "impact": "Global warming disrupts weather patterns, causing extreme heatwaves, floods, and droughts that threaten food security and human health.",
            "tip": "Reduce your carbon footprint by using public transport, saving electricity, and planting local trees."
        },
        "Pollution": {
            "exp": "Pollution occurs when harmful substances (pollutants) are introduced into our environment. This can affect the air we breathe, the water we drink, and the soil where we grow food.",
            "impact": "Pollution causes respiratory diseases in humans and destroys aquatic life. Plastic waste in oceans takes hundreds of years to decompose.",
            "tip": "Say no to single-use plastics, dispose of electronic waste properly, and support 'Swachh Bharat' initiatives."
        },
        "Wildlife": {
            "exp": "Wildlife conservation is the practice of protecting animal species and their habitats. Biodiversity is essential for a healthy and balanced ecosystem.",
            "impact": "Loss of species can lead to ecosystem collapse, affecting everything from pollination of crops to natural pest control.",
            "tip": "Avoid products made from endangered animals, support local wildlife sanctuaries, and keep your surroundings eco-friendly."
        },
        "Green Tech": {
            "exp": "Green technology involves using science and technology to create products and services that are environmentally friendly and sustainable.",
            "impact": "Switching to solar and wind energy reduces our dependence on fossil fuels, significantly cutting down on air pollution and carbon emissions.",
            "tip": "Switch to LED bulbs at home, use solar water heaters, and choose energy-efficient appliances."
        }
    }

    for url, category in feeds:
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries[:2]:
                summary = entry.summary if 'summary' in entry else ""
                raw_text = re.sub('<[^<]+?>', '', summary) if summary else entry.title
                
                # Fetch category data or use default
                edu = learning_repo.get(category, {
                    "exp": "This environmental update highlights the ongoing shifts in our planetary boundaries.",
                    "impact": "Changes in our environment affect ecological stability and community health.",
                    "tip": "Stay informed and participate in local environmental awareness programs."
                })

                educational_news.append({
                    'title': entry.title,
                    'intro': raw_text[:250] + "...",
                    'explanation': edu['exp'],
                    'impact': edu['impact'],
                    'awareness': edu['tip'],
                    'conclusion': "Together, stay informed and act responsibly for a sustainable future.",
                    'category': category,
                    'date': datetime.now().strftime("%d %B %Y"),
                    'location': 'India' if 'India' in entry.title or 'India' in raw_text else 'International'
                })
        except Exception as e:
            app.logger.error(f"Educational Feed Error for {url}: {e}")
            
    # Fallback if feeds fail
    if not educational_news:
        educational_news.append({
            'title': "Welcome to EcoPortal Education",
            'intro': "We are currently updating our daily news feed. Please check back in a few minutes.",
            'explanation': "EcoPortal aims to provide students with updated knowledge about climate action.",
            'impact': "Environmental literacy is the foundation of a sustainable lifestyle.",
            'awareness': "Explore our other sections like 'Report Issue' to help your local community.",
            'conclusion': "Every small action for nature counts.",
            'category': "Awareness",
            'date': datetime.now().strftime("%d %B %Y"),
            'location': "Global"
        })
            
    return render_template('news.html', news=educational_news)

@app.route('/news/<int:news_id>')
def news_detail(news_id):
    # This would normally pull from a cache/DB, but for now, we'll simulate the internal reading experience
    return "Detail View - Staying within EcoPortal as requested."

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
