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
import socket
import requests

# Set global timeout for socket operations
socket.setdefaulttimeout(10)
logging.basicConfig(level=logging.DEBUG)

app = Flask(__name__)
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
        "templates_exists": os.path.exists('templates'),
        "templates_content": os.listdir('templates') if os.path.exists('templates') else [],
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
    query = request.args.get('q', '')
    
    # Base feeds + dynamic search if query exists
    if query:
        # Search-specific feed
        search_query = f"{query} environment climate sustainability India"
        feeds = [(f"https://news.google.com/rss/search?q={search_query}&hl=en-IN&gl=IN&ceid=IN:en", "Search Result")]
    else:
        # Elite sources requested by you: The Hindu, NatGeo, UNEP, NASA, Indian Express
        feeds = [
            ("https://news.google.com/rss/search?q=site:thehindu.com+environment&hl=en-IN&gl=IN&ceid=IN:en", "India Environment"),
            ("https://news.google.com/rss/search?q=site:nationalgeographic.com+environment+wildlife&hl=en-US&gl=US&ceid=US:en", "Wildlife"),
            ("https://news.google.com/rss/search?q=site:unep.org+news&hl=en-US&gl=US&ceid=US:en", "Global Policy"),
            ("https://news.google.com/rss/search?q=site:climate.nasa.gov+news&hl=en-US&gl=US&ceid=US:en", "Climate Science"),
            ("https://news.google.com/rss/search?q=site:indianexpress.com+environment&hl=en-IN&gl=IN&ceid=IN:en", "India News")
        ]
    
    educational_news = []
    
    # Category-based learning database for educational expansion
    learning_repo = {
        "Climate Change": {
            "exp": "Climate change refers to long-term shifts in temperatures and weather patterns. Human activities, primarily the burning of fossil fuels, have been the main driver of these changes since the 1800s.",
            "impact": "The consequences of climate change now include intense droughts, water scarcity, severe fires, rising sea levels, flooding, melting polar ice, catastrophic storms and declining biodiversity.",
            "tip": "Sustainable solutions include shifting to renewable energy, improving energy efficiency, and protecting forests through reforestation."
        },
        "Pollution": {
            "exp": "Pollution is the introduction of contaminants into the natural environment that cause adverse change. It can take the form of chemical substances or energy, such as noise, heat or light.",
            "impact": "Pollution harms human health, causes global warming through greenhouse gases, and leads to the acidification of oceans and soil degradation.",
            "tip": "Practice the 3R's: Reduce, Reuse, and Recycle. Avoid plastics and support local pollution monitoring initiatives."
        },
        "Green Tech": {
            "exp": "Green technology, also known as clean technology, refers to products, equipment or systems used to conserve the natural environment and resources, which minimize and reduce the negative impact of human activities.",
            "impact": "It provides sustainable energy solutions (solar, wind), reduces waste, and improves efficiency in transportation and agriculture.",
            "tip": "Support companies that use green manufacturing and invest in energy-efficient technology for your home."
        },
        "India Environment": {
            "exp": "India faces unique environmental challenges due to its large population and diverse geography. Major issues include air pollution in cities and management of river ecosystems like the Ganga.",
            "impact": "Environmental health in India directly impacts agriculture, monsoon patterns, and the health of millions of citizens.",
            "tip": "Local action is vital. Participate in community cleaning drives and follow NGT (National Green Tribunal) guidelines."
        }
    }

    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
    
    for url, category in feeds:
        try:
            # Use requests for better timeout control
            response = requests.get(url, headers=headers, timeout=5)
            if response.status_code == 200:
                feed = feedparser.parse(response.content)
                
                # Take top 3 for search, or top 2 for default feeds
                limit = 3 if query else 2
                count = 0
                for entry in feed.entries:
                    if count >= limit: break
                    
                    summary = entry.summary if 'summary' in entry else ""
                    raw_text = re.sub('<[^<]+?>', '', summary) if summary else entry.title
                    
                    # Choose best educational content
                    category_key = category if category in learning_repo else ("Climate Change" if "climate" in entry.title.lower() else "India Environment")
                    edu = learning_repo.get(category_key, learning_repo["Climate Change"])

                    educational_news.append({
                        'title': entry.title,
                        'category': category_key,
                        'intro': raw_text[:200] + "...",
                        'explanation': edu['exp'],
                        'impact': edu['impact'],
                        'awareness': edu['tip'],
                        'conclusion': "Together, stay informed and take small steps toward a cleaner environment.",
                        'date': datetime.now().strftime("%d %B %Y"),
                        'location': 'India' if 'India' in entry.title or 'india' in entry.title.lower() else 'Global'
                    })
                    count += 1
            else:
                app.logger.warning(f"Feed error {response.status_code} for {url}")
        except Exception as e:
            app.logger.error(f"News Fetch Error for {url}: {e}")
            
    # Final Fallback if source is completely unavailable
    if not educational_news:
        educational_news.append({
            'title': "Welcome to EcoPortal Educator",
            'category': "Announcement",
            'intro': "We are currently updating our elite news feeds from The Hindu, NatGeo, and NASA.",
            'explanation': "EcoPortal Educator pulls real-time data from top environmental sources to provide student-friendly summaries.",
            'impact': "Our goal is to keep you informed about global policies and local issues without jargon.",
            'awareness': "While we refresh the feeds, you can use the search bar above to explore specific topics.",
            'conclusion': "Check back in a few minutes for the latest updates.",
            'date': datetime.now().strftime("%d %B %Y"),
            'location': "India"
        })
            
    return render_template('news.html', news=educational_news, search_query=query)

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
