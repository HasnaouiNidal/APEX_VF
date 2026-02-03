#head of brain : 
    # check if it good !? 
# Standard library imports
import os
import re
import json
from datetime import datetime
from functools import wraps

# Flask framework imports
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify

# Database and Security imports
from flask_mysqldb import MySQL
import MySQLdb.cursors
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from email_validator import validate_email, EmailNotValidError

# -------------------------------------------------
# Application Initialization
# -------------------------------------------------
app = Flask(__name__)

# Set the secret key for session management
app.secret_key = os.environ.get('SECRET_KEY', 'local_secret_key')

# -------------------------------------------------
# Database Configuration
# -------------------------------------------------
# Configure MySQL connection settings for local development
app.config['MYSQL_HOST'] = '127.0.0.1'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = ''
app.config['MYSQL_DB'] = 'apex'
app.config['MYSQL_PORT'] = 3306
app.config['MYSQL_CURSORCLASS'] = 'DictCursor'

# Configure SSL options if connecting to a remote database
if os.environ.get('MYSQL_HOST') and os.environ.get('MYSQL_HOST') != 'localhost':
    app.config['MYSQL_CUSTOM_OPTIONS'] = {
        "ssl": {
            "ssl_mode": "REQUIRED",
            "fake_option_to_trigger_ssl": True
        }
    }

# Initialize MySQL extension
mysql = MySQL(app)

# -------------------------------------------------
# File Upload Configuration
# -------------------------------------------------
# Define paths for uploading user profiles and content images
app.config['PROFILE_UPLOAD_FOLDER'] = 'static/uploads/profiles'
app.config['IMAGE_UPLOAD_FOLDER'] = 'static/uploads/images'

# Ensure upload directories exist
os.makedirs(app.config['PROFILE_UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['IMAGE_UPLOAD_FOLDER'], exist_ok=True)

# -------------------------------------------------
# Database Management Decorator
# -------------------------------------------------
def db_task(f):
    """
    Decorator to handle database connections automatically.
    Injects a cursor into the function and handles commit/rollback.
    Prevents infinite loops if the DB fails on the home page.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        cursor = None
        try:
            # Open a dictionary cursor
            cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
            
            # Inject the cursor into the function arguments
            kwargs['cursor'] = cursor
            result = f(*args, **kwargs)
            
            # Commit transaction (useful for INSERT/UPDATE, harmless for SELECT)
            mysql.connection.commit()
            return result
            
        except Exception as e:
            # Rollback transaction on error
            if cursor:
                mysql.connection.rollback()
            
            print(f"❌ DATABASE ERROR: {e}")
            flash("An error occurred with the database connection.", "danger")
            
            # SAFETY CHECK: Prevent infinite redirect loop
            if request.endpoint == 'home':
                return "Critical Error: Database is unavailable. Please try again later.", 500
            
            return redirect(url_for('home'))
            
        finally:
            # Always close the cursor to prevent leaks
            if cursor:
                cursor.close()
            
    return decorated_function

def is_strong_password(password):
    """
    Validates password strength.
    Requires: 8+ chars, 1 uppercase, 1 lowercase, 1 digit.
    """
    if len(password) < 8: return False, "Password must be at least 8 characters long."
    if not re.search(r"[A-Z]", password): return False, "Missing uppercase letter."
    if not re.search(r"[a-z]", password): return False, "Missing lowercase letter."
    if not re.search(r"[0-9]", password): return False, "Missing digit."
    return True, ""

# end of head !

# -------------------------------------------------
# Application Routes
# -------------------------------------------------


# -------------------------------------------------
# HOME ROUTE 
# -------------------------------------------------
@app.route('/')
@db_task
def home(cursor):
    """
    Renders the home page.
    Fetches recent events for display.
    """
    # Fetch Recent Events (Safe execution)
    try:
        cursor.execute("SELECT * FROM events ORDER BY id DESC LIMIT 3")
        recent_events = cursor.fetchall()
    except Exception as e:
        print(f"⚠️ Error fetching events: {e}")
        recent_events = [] # Fallback to empty list so page still loads

    # Render template (No articles passed)
    return render_template('index.html', recent_events=recent_events)


# -------------------------------------------------
# Authentication System
# -------------------------------------------------

#LOGIN ROUTE : 
@app.route('/login', methods=['GET', 'POST'])
@db_task
def login(cursor):
    """Handles user login."""
    if 'user_id' in session:
        return redirect(url_for('profile'))

    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')

        cursor.execute('SELECT * FROM users WHERE email = %s', (email,))
        user = cursor.fetchone()

        if user and check_password_hash(user['password'], password):
            session['loggedin'] = True
            session['user_id'] = user['id'] 
            session['username'] = user['first_name']
            session['email'] = user['email'] 
            flash('You logged in successfully!', 'success')
            return redirect(url_for('profile'))
        else:
            flash('Email or password is not correct', 'danger')
            return redirect(url_for('login'))

    return render_template('login.html')

# REGISTER ROUTE :
@app.route('/register', methods=['GET', 'POST'])
@db_task
def register(cursor):
    """Handles new user registration."""
    if 'user_id' in session:
        return redirect(url_for('profile'))

    if request.method == 'POST':
        first_name = request.form.get('first_name', '').strip()
        last_name = request.form.get('last_name', '').strip()
        phone_number = request.form.get('phone_number', '').strip()
        email = request.form.get('email', '').strip()
        # Retrieve branch from form
        branch = request.form.get('branch') 
        
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')

        try:
            valid = validate_email(email, check_deliverability=True)
            email = valid.normalized 
        except EmailNotValidError as e:
            flash(f'Invalid email: {str(e)}', 'danger')
            return redirect(url_for('register'))

        if password != confirm_password:
            flash('Passwords do not match!', 'danger')
            return redirect(url_for('register'))

        is_strong, msg = is_strong_password(password)
        if not is_strong:
            flash(f'Weak Password: {msg}', 'warning')
            return redirect(url_for('register'))

        cursor.execute('SELECT * FROM users WHERE email = %s', (email,))
        if cursor.fetchone():
            flash('Email already used! Please login.', 'warning')
            return redirect(url_for('register'))

        hashed_password = generate_password_hash(password)
        
        # Insert new user with branch information
        cursor.execute('''
            INSERT INTO users (first_name, last_name, email, phone_number, password, role, team, branch, profile_image) 
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        ''', (first_name, last_name, email, phone_number, hashed_password, 'Member', None, branch, 'profile.jpg'))

        flash('Account created successfully! Please login.', 'success')
        return redirect(url_for('login'))

    return render_template('register.html')

#LOGOUT ROUTE
@app.route('/logout')
def logout():
    """Logs out the current user."""
    session.clear() 
    flash('You have been logged out!', 'info')
    return redirect(url_for('login'))


# -------------------------------------------------
# Events System
# -------------------------------------------------

#EVENTE PAGE : 
@app.route('/events')
@db_task
def events(cursor):
    """Displays all events."""
    cursor.execute("SELECT * FROM events ORDER BY id DESC")
    events_data = cursor.fetchall()
    return render_template('events.html', events=events_data)

#ADD_EVENTE :
@app.route('/add_event', methods=['GET', 'POST'])
@db_task
def add_event(cursor):
    """Admin-only route to publish new events."""
    if 'user_id' not in session:
        return redirect(url_for('login'))

    ALLOWED_ADMINS = ['nidalhasnaoui04@gmail.com', 'khalidouisnaf@gmail.com']
    if session.get('email') not in ALLOWED_ADMINS:
        flash("Access Denied!", "danger")
        return redirect(url_for('home')) 

    if request.method == 'POST':
        title = request.form.get('title')
        raw_date = request.form.get('date_str')
        category = request.form.get('category')
        description = request.form.get('description')
        content = request.form.get('content')
        
        try:
            date_obj = datetime.strptime(raw_date, '%Y-%m-%d')
            formatted_date = date_obj.strftime('%B %d, %Y')
        except:
            formatted_date = raw_date 
        
        filename = 'default_event.jpg'
        if 'event_image' in request.files:
            file = request.files['event_image']
            if file.filename != '':
                filename = secure_filename(file.filename)
                file.save(os.path.join(app.root_path, app.config['IMAGE_UPLOAD_FOLDER'], filename))

        cursor.execute('''
            INSERT INTO events (title, date_str, category, description, content, image)
            VALUES (%s, %s, %s, %s, %s, %s)
        ''', (title, formatted_date, category, description, content, filename))

        flash('Event published successfully!', 'success')
        return redirect(url_for('events'))

    return render_template('add_event.html')

#EVENT DETAIL
@app.route('/event/<int:id>')
@db_task
def event_detail(cursor, id):
    """Displays details for a specific event."""
    cursor.execute("SELECT * FROM events WHERE id = %s", (id,))
    event_data = cursor.fetchone()
    
    if event_data:
        return render_template('event_detail.html', event=event_data)
    else:
        flash("Event not found!", "danger")
        return redirect(url_for('events'))

# -------------------------------------------------
# Articles System
# -------------------------------------------------

#ARTICLES : 
@app.route('/articles')
@db_task
def articles(cursor):
    """Displays all articles."""
    cursor.execute("SELECT * FROM articles ORDER BY created_at DESC")
    articles_data = cursor.fetchall()
    return render_template('articles.html', articles=articles_data)

#ARTICLES DETAILES : 
@app.route('/article/<int:id>')
@db_task
def article_detail_dynamic(cursor, id):
    """Displays details for a specific article."""
    cursor.execute("SELECT * FROM articles WHERE id = %s", (id,))
    article = cursor.fetchone()
    
    if article:
        return render_template('article_detail.html', article=article)
    else:
        flash("Article not found!", "danger")
        return redirect(url_for('articles'))

#ADD ARTICLES : 
@app.route('/add_article', methods=['GET', 'POST'])
@db_task
def add_article(cursor):
    """Admin-only route to publish new articles."""
    if 'user_id' not in session:
        flash("Login required.", "warning")
        return redirect(url_for('login'))

    ALLOWED_ADMINS = ['nidalhasnaoui04@gmail.com', 'khalidouisnaf@gmail.com']
    if session.get('email') not in ALLOWED_ADMINS:
        flash("Access Denied!", "danger")
        return redirect(url_for('articles'))

    if request.method == 'POST':
        title = request.form.get('title')
        author = request.form.get('author')
        subject = request.form.get('subject')
        summary = request.form.get('summary')
        content = request.form.get('content')
        created_at = datetime.now() 

        filename = 'default_article.jpg'
        if 'article_image' in request.files:
            file = request.files['article_image']
            if file.filename != '':
                filename = secure_filename(file.filename)
                file.save(os.path.join(app.root_path, app.config['IMAGE_UPLOAD_FOLDER'], filename))

        cursor.execute('''
            INSERT INTO articles (title, author, subject, image, summary, content, created_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        ''', (title, author, subject, filename, summary, content, created_at))

        flash('Article published successfully!', 'success')
        return redirect(url_for('articles'))

    return render_template('add_article.html')



# -------------------------------------------------
# Lost & Found System
# -------------------------------------------------

@app.route('/lost-found')
@db_task
def lost_found(cursor):
    """Displays the Lost & Found Hub."""
    # Fetch active items, newest first
    cursor.execute("""
        SELECT lf.*, u.first_name, u.last_name, u.profile_image 
        FROM lost_found lf 
        JOIN users u ON lf.user_id = u.id 
        WHERE lf.status = 'active' 
        ORDER BY lf.created_at DESC
    """)
    items = cursor.fetchall()
    return render_template('lost_found.html', items=items)

@app.route('/add-lost-found', methods=['GET', 'POST'])
@db_task
def add_lost_found(cursor):
    """Allows students to post lost or found items."""
    if 'user_id' not in session:
        flash("Please login to post an item.", "warning")
        return redirect(url_for('login'))

    if request.method == 'POST':
        type_ = request.form.get('type') # 'lost' or 'found'
        title = request.form.get('title')
        category = request.form.get('category')
        location = request.form.get('location')
        contact = request.form.get('contact_info')
        description = request.form.get('description')
        
        filename = 'default_item.jpg'
        if 'item_image' in request.files:
            file = request.files['item_image']
            if file.filename != '':
                filename = secure_filename(file.filename)
                # Ensure you use your configured upload folder
                file.save(os.path.join(app.root_path, app.config['IMAGE_UPLOAD_FOLDER'], filename))

        cursor.execute('''
            INSERT INTO lost_found (user_id, type, title, category, location, contact_info, description, image)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        ''', (session['user_id'], type_, title, category, location, contact, description, filename))

        flash('Item posted successfully!', 'success')
        return redirect(url_for('lost_found'))

    return render_template('add_lost_found.html')

@app.route('/resolve-item/<int:id>')
@db_task
def resolve_item(cursor, id):
    """Mark an item as found/returned (Archive it)."""
    if 'user_id' not in session: return redirect(url_for('login'))
    
    # Only allow the owner or admin to delete/resolve
    cursor.execute("SELECT user_id FROM lost_found WHERE id = %s", (id,))
    item = cursor.fetchone()
    
    if item and (item['user_id'] == session['user_id'] or session.get('email') in ['nidalhasnaoui04@gmail.com', 'khalidouisnaf@gmail.com']):
        cursor.execute("UPDATE lost_found SET status = 'resolved' WHERE id = %s", (id,))
        flash("Item marked as resolved!", "success")
    else:
        flash("Unauthorized action.", "danger")
        
    return redirect(url_for('lost_found'))

# -------------------------------------------------
# Housing System
# -------------------------------------------------

@app.route('/housing')
@db_task
def housing(cursor):
    """Displays the Housing & Roommate Finder."""
    # Fetch active listings, newest first
    cursor.execute("""
        SELECT h.*, u.first_name, u.last_name, u.profile_image 
        FROM housing h 
        JOIN users u ON h.user_id = u.id 
        WHERE h.status = 'active' 
        ORDER BY h.created_at DESC
    """)
    listings = cursor.fetchall()
    return render_template('housing.html', listings=listings)

@app.route('/add-housing', methods=['GET', 'POST'])
@db_task
def add_housing(cursor):
    """Allows students to post a housing offer or request."""
    if 'user_id' not in session:
        flash("Please login to post a listing.", "warning")
        return redirect(url_for('login'))

    if request.method == 'POST':
        type_ = request.form.get('type') # 'offer' or 'request'
        title = request.form.get('title')
        location = request.form.get('location')
        price = request.form.get('price')
        gender_pref = request.form.get('gender_pref')
        contact = request.form.get('contact_info')
        description = request.form.get('description')
        
        filename = 'default_house.jpg'
        if 'housing_image' in request.files:
            file = request.files['housing_image']
            if file.filename != '':
                filename = secure_filename(file.filename)
                file.save(os.path.join(app.root_path, app.config['IMAGE_UPLOAD_FOLDER'], filename))

        cursor.execute('''
            INSERT INTO housing (user_id, type, title, location, price, gender_pref, contact_info, description, image)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        ''', (session['user_id'], type_, title, location, price, gender_pref, contact, description, filename))

        flash('Housing listing posted successfully!', 'success')
        return redirect(url_for('housing'))

    return render_template('add_housing.html')

@app.route('/delete-housing/<int:id>')
@db_task
def delete_housing(cursor, id):
    """Mark a listing as taken/deleted."""
    if 'user_id' not in session: return redirect(url_for('login'))
    
    # Check ownership
    cursor.execute("SELECT user_id FROM housing WHERE id = %s", (id,))
    item = cursor.fetchone()
    
    if item and (item['user_id'] == session['user_id'] or session.get('email') in ['nidalhasnaoui04@gmail.com', 'khalidouisnaf@gmail.com']):
        cursor.execute("UPDATE housing SET status = 'taken' WHERE id = %s", (id,))
        flash("Listing removed!", "success")
    else:
        flash("Unauthorized action.", "danger")
        
    return redirect(url_for('housing'))


# -------------------------------------------------
# Donation / Charity System
# -------------------------------------------------

@app.route('/donations')
@db_task
def donations(cursor):
    """Displays the Donation Corner."""
    # Fetch available items, newest first
    cursor.execute("""
        SELECT d.*, u.first_name, u.last_name, u.profile_image 
        FROM donations d 
        JOIN users u ON d.user_id = u.id 
        WHERE d.status = 'available' 
        ORDER BY d.created_at DESC
    """)
    items = cursor.fetchall()
    return render_template('donations.html', items=items)

@app.route('/add-donation', methods=['GET', 'POST'])
@db_task
def add_donation(cursor):
    """Allows students to post items for free donation."""
    if 'user_id' not in session:
        flash("Please login to donate an item.", "warning")
        return redirect(url_for('login'))

    if request.method == 'POST':
        title = request.form.get('title')
        category = request.form.get('category')
        condition = request.form.get('condition')
        contact = request.form.get('contact_info')
        description = request.form.get('description')
        
        filename = 'default_donation.jpg'
        if 'donation_image' in request.files:
            file = request.files['donation_image']
            if file.filename != '':
                filename = secure_filename(file.filename)
                file.save(os.path.join(app.root_path, app.config['IMAGE_UPLOAD_FOLDER'], filename))

        cursor.execute('''
            INSERT INTO donations (user_id, title, category, item_condition, contact_info, description, image)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        ''', (session['user_id'], title, category, condition, contact, description, filename))

        flash('Thank you for your generosity! Item listed.', 'success')
        return redirect(url_for('donations'))

    return render_template('add_donation.html')

@app.route('/claim-donation/<int:id>')
@db_task
def claim_donation(cursor, id):
    """Mark a donation as taken (Archive it)."""
    if 'user_id' not in session: return redirect(url_for('login'))
    
    # Check ownership
    cursor.execute("SELECT user_id FROM donations WHERE id = %s", (id,))
    item = cursor.fetchone()
    
    if item and (item['user_id'] == session['user_id'] or session.get('email') in ['nidalhasnaoui04@gmail.com', 'khalidouisnaf@gmail.com']):
        cursor.execute("UPDATE donations SET status = 'taken' WHERE id = %s", (id,))
        flash("Item marked as gifted!", "success")
    else:
        flash("Unauthorized action.", "danger")
        
    return redirect(url_for('donations'))



# -------------------------------------------------
# Members System
# -------------------------------------------------

@app.route('/members')
@db_task
def members(cursor):
    """Displays a list of all team members."""
    query = "SELECT * FROM users WHERE team IS NOT NULL ORDER BY team, role"
    cursor.execute(query)
    all_members = cursor.fetchall()
    return render_template('members.html', members=all_members)

@app.route('/add_member', methods=['GET', 'POST'])
@db_task
def add_member(cursor):
    """Admin-only route to add new team members."""
    if 'user_id' not in session:
        return redirect(url_for('login'))

    ALLOWED_ADMINS = ['nidalhasnaoui04@gmail.com', 'khalidouisnaf@gmail.com']
    if session.get('email') not in ALLOWED_ADMINS:
        flash("Access Denied!", "danger")
        return redirect(url_for('members'))

    if request.method == 'POST':
        first_name = request.form.get('first_name')
        last_name = request.form.get('last_name')
        email = request.form.get('email')
        phone = request.form.get('phone_number')
        role = request.form.get('role')
        team = request.form.get('team')
        password = generate_password_hash("12345678")
        
        filename = 'default_profile.jpg'
        if 'profile_image' in request.files:
            file = request.files['profile_image']
            if file.filename != '':
                filename = secure_filename(file.filename)
                file.save(os.path.join(app.root_path, app.config['PROFILE_UPLOAD_FOLDER'], filename))

        cursor.execute('SELECT id FROM users WHERE email=%s', (email,))
        if cursor.fetchone():
             flash('Error! This email exists.', 'danger')
        else:
            cursor.execute('''
                INSERT INTO users (first_name, last_name, email, phone_number, password, role, team, profile_image) 
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            ''', (first_name, last_name, email, phone, password, role, team, filename))
            flash(f'Member {first_name} added successfully!', 'success')
        
        return redirect(url_for('add_member'))

    return render_template('add_member.html')




# -------------------------------------------------
# User Profile System
# -------------------------------------------------

@app.route('/profile')
@db_task
def profile(cursor):
    """Displays the user's profile."""
    if 'user_id' not in session:
        flash('Please login to view your profile', 'warning')
        return redirect(url_for('login'))
    
    cursor.execute("SELECT * FROM users WHERE id = %s", (session['user_id'],))
    user_data = cursor.fetchone()
    
    if user_data:
        return render_template('profile.html', user=user_data)
    else:
        session.clear()
        return redirect(url_for('login'))

@app.route('/edit_profile', methods=['GET', 'POST'])
@db_task
def edit_profile(cursor):
    """Allows users to edit their profile information."""
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    user_id = session['user_id']

    if request.method == 'POST':
        first_name = request.form.get('first_name')
        last_name = request.form.get('last_name')
        phone = request.form.get('phone_number')
        bio = request.form.get('bio')
        
        # Retrieve branch from form
        branch = request.form.get('branch')
        
        if 'profile_image' in request.files:
            file = request.files['profile_image']
            if file.filename != '':
                filename = secure_filename(file.filename)
                file.save(os.path.join(app.root_path, app.config['PROFILE_UPLOAD_FOLDER'], filename))
                cursor.execute("UPDATE users SET profile_image=%s WHERE id=%s", (filename, user_id))

        # Update user details including branch
        cursor.execute("""
            UPDATE users 
            SET first_name=%s, last_name=%s, phone_number=%s, bio=%s, branch=%s
            WHERE id=%s
        """, (first_name, last_name, phone, bio, branch, user_id))
        
        session['username'] = first_name
        flash('Profile updated successfully!', 'success')
        return redirect(url_for('profile'))

    cursor.execute("SELECT * FROM users WHERE id = %s", (user_id,))
    user = cursor.fetchone()
    return render_template('edit_profile.html', user=user)




# -------------------------------------------------
# Academic System
# -------------------------------------------------

MATH_PROGRAM = {
    'S1': {
        'Analysis 1': [
            {'title': 'Chapter 1: Real Numbers',             'filename': 'analysis1_chap1.pdf'},
            {'title': 'Chapter 2: Real Sequences',           'filename': 'analysis1_chap2.pdf'},
            {'title': 'Chapter 3: Functions of a real variable', 'filename': 'analysis1_chap3.pdf'},
            {'title': 'TD Series 1',                         'filename': 'analysis1_td1.pdf'},
            {'title': 'TD Series 2',                         'filename': 'analysis1_td2.pdf'},
            {'title': 'TD Series 3',                         'filename': 'analysis1_td3.pdf'}
        ],
        'Algebra 1': [
            {'title': 'Chapter 1: Logic & Sets',             'filename': 'algebra1_chap1.pdf'},
            {'title': 'Chapter 2: Basic Language of Set Theory', 'filename': 'algebra1_chap2.pdf'},
            {'title': 'Chapter 3: Mappings and Relations',   'filename': 'algebra1_chap3.pdf'},
            {'title': 'Chapter 4: Mappings and Relations',   'filename': 'algebra1_chap4.pdf'},
            {'title': 'TD Series 1',                         'filename': 'algebra1_td1.pdf'},
            {'title': 'TD Series 2',                         'filename': 'algebra1_td2.pdf'},
            {'title': 'TD Series 3',                         'filename': 'algebra1_td3.pdf'}
        ],
        'Algebra 2': [
            {'title': 'Chapter 1: Groups',                   'filename': 'algebra2_chap1.pdf'},
            {'title': 'Chapter 2: Polynomials',              'filename': 'algebra2_chap2.pdf'},
            {'title': 'TD Series 1',                         'filename': 'algebra2_td1.pdf'},
            {'title': 'TD Series 2',                         'filename': 'algebra2_td2.pdf'}
        ],
        'Statistics': [
            {'title': 'Chapter 1: Chapitre 01',              'filename': 'stats_chap1.pdf'},
            {'title': 'Chapter 2: Chapitre 02',              'filename': 'stats_chap2.pdf'},
            {'title': 'TD Series 1',                         'filename': 'stats_td1.pdf'},
            {'title': 'TD Series 2',                         'filename': 'stats_td2.pdf'}
        ],
        'Thermodynamics': [
            {'title': 'Chapter 1: Chapitre 1',               'filename': 'thermo_chap1.pdf'},
            {'title': 'Chapter 2: Chapitre 2',               'filename': 'thermo_chap2.pdf'},
            {'title': 'Chapter 3: chapitre 03',              'filename': 'thermo_chap3.pdf'},
            {'title': 'Chapter 4: Chapite 4',                'filename': 'thermo_chap4.pdf'},
            {'title': 'TD Series 1',                         'filename': 'thermo_td1.pdf'},
            {'title': 'TD Series 2',                         'filename': 'thermo_td2.pdf'},
            {'title': 'TD Series 3',                         'filename': 'thermo_td3.pdf'},
            {'title': 'TD Series 4',                         'filename': 'thermo_td4.pdf'}
        ],
        'Informatique': [
            {'title': 'Chapter 1: Chapitre 1 and Chpater 02', 'filename': 'info_chap1.pdf'},
            {'title': 'Chapter 3: chapitre 03',              'filename': 'info_chap3.pdf'},
            {'title': 'Chapter 4: Chapite 4',                'filename': 'info_chap4.pdf'},
            {'title': 'TD Series 1',                         'filename': 'info_td1.pdf'}
        ]
    },
    # Placeholders for future semesters (S2 - S6)
    'S2': {
        'Analysis 2': [
             {'title': 'analysis 2 Full Course',             'filename': 'analysis2.pdf'},
             {'title': 'TD Series 1',                         'filename': 'analysis2_td1.pdf'},
             {'title': 'TD Series 2',                         'filename': 'analysis2_td2.pdf'},
             {'title': 'TD Series 3',                         'filename': 'analysis2_td3.pdf'},
            ],
        'Analysis 3': [
            {'title': 'analysis 3 Full Course',             'filename': 'analysis3.pdf'},
            {'title': 'TD Series 1',                         'filename': 'analysis3_td1.pdf'},
        ] , 
        'Algebra 3': [
            {'title': 'Algebra 3 Full Course',             'filename': 'Algebra3.pdf'},
            {'title': 'TD Series 1',                         'filename': 'algebra3_td1.pdf'},
        ],
        'Informatique 2': [
            {'title': 'Informatique Full Course', 'filename': 'info2.pdf'},
            {'title': 'TD Series 1', 'filename': 'info2_td1.pdf'}, 
            {'title': 'TD Series 2', 'filename': 'info2_td2.pdf'}, 
            {'title': 'TD Series 3', 'filename': 'info2_td3.pdf'}, 
            {'title': 'TD Series 4', 'filename': 'info2_td4.pdf'}, 
        ]
    },
    'S3': {
        'Analysis 3': ['Series', 'Topology'],
        'Probabilities': ['Random Variables', 'Distributions']
    },
    'S4': {
        'Analysis 4': ['Complex Analysis'],
        'Algebra 4': ['Reduction of Endomorphisms']
    },
    'S5': {
        'Topology': ['Metric Spaces'],
        'Integration': ['Measure Theory']
    },
    'S6': {
        'Differential Calculus': ['Differentiability'],
        'Graduation Project': ['PFE Guidelines']
    }
}

# -------------------------------------------------
# Academic Routes
# -------------------------------------------------

@app.route('/academic_hub')
def courses_hub():
    """Renders the main academic hub page."""
    return render_template('courses_hub.html')

@app.route('/courses/math')
def math_semesters():
    """Displays available math semesters."""
    return render_template('math_semesters.html', semesters=MATH_PROGRAM.keys())

@app.route('/courses/math/<semester>')
def semester_content(semester):
    """Displays content for a specific semester."""
    modules = MATH_PROGRAM.get(semester, {})
    return render_template('semester_content.html', semester=semester, modules=modules)




# -------------------------------------------------
# Focus & Productivity System
# -------------------------------------------------

@app.route('/focus')
@db_task
def focus_dashboard(cursor):
    """
    Renders the main focus dashboard.
    Displays user stats and daily study progress.
    """
    if 'user_id' not in session: return redirect(url_for('login'))
    user_id = session['user_id']
    
    # Retrieve user statistics
    cursor.execute("SELECT xp, level, first_name, last_name FROM users WHERE id = %s", (user_id,))
    user_stats = cursor.fetchone()

    # Validate user existence
    if not user_stats:
        session.clear()
        return redirect(url_for('login'))

    # Calculate total study minutes for the current day
    cursor.execute("""
        SELECT SUM(duration) as today_min 
        FROM study_sessions 
        WHERE user_id = %s AND DATE(completed_at) = CURDATE()
    """, (user_id,))
    result = cursor.fetchone()
    today_progress = result['today_min'] or 0
    
    return render_template('focus/dashboard.html', stats=user_stats, today_progress=today_progress)

@app.route('/focus/tasks')
@db_task
def focus_tasks(cursor):
    """
    Renders the Kanban-style task board.
    Separates tasks into Todo, In Progress, and Done.
    """
    if 'user_id' not in session: return redirect(url_for('login'))
    user_id = session['user_id']
    
    cursor.execute("SELECT xp, level, first_name FROM users WHERE id = %s", (user_id,))
    user_stats = cursor.fetchone()

    # Fetch tasks by status
    cursor.execute("SELECT * FROM tasks WHERE user_id = %s AND status = 'pending' ORDER BY priority DESC, id DESC", (user_id,))
    todo = cursor.fetchall()

    cursor.execute("SELECT * FROM tasks WHERE user_id = %s AND status = 'in_progress' ORDER BY priority DESC, id DESC", (user_id,))
    progress = cursor.fetchall()

    cursor.execute("SELECT * FROM tasks WHERE user_id = %s AND status = 'completed' ORDER BY id DESC LIMIT 10", (user_id,))
    done = cursor.fetchall()

    return render_template('focus/tasks.html', stats=user_stats, todo=todo, progress=progress, done=done)

@app.route('/focus/analytics')
@db_task
def focus_analytics(cursor):
    """
    Renders the analytics page with charts.
    Shows total study hours and task distribution by category.
    """
    if 'user_id' not in session: return redirect(url_for('login'))
    user_id = session['user_id']
    
    cursor.execute("SELECT xp, level, first_name FROM users WHERE id = %s", (user_id,))
    user_stats = cursor.fetchone()

    # Calculate total study hours
    cursor.execute("SELECT SUM(duration) as total_min FROM study_sessions WHERE user_id = %s", (user_id,))
    res = cursor.fetchone()
    total_hours = round((res['total_min'] or 0) / 60, 1)

    # Prepare data for charts
    cursor.execute("SELECT category, COUNT(*) as count FROM tasks WHERE user_id = %s AND status = 'completed' GROUP BY category", (user_id,))
    subject_data = cursor.fetchall()
    
    chart_labels = [row['category'] for row in subject_data] if subject_data else ['General']
    chart_data = [row['count'] for row in subject_data] if subject_data else [1]

    return render_template('focus/analytics.html', 
                           stats=user_stats, 
                           total_hours=total_hours,
                           chart_labels=json.dumps(chart_labels), 
                           chart_data=json.dumps(chart_data))

@app.route('/focus/leaderboard')
@db_task
def focus_leaderboard(cursor):
    """
    Renders the leaderboard showing top users by XP.
    """
    if 'user_id' not in session: return redirect(url_for('login'))
    
    cursor.execute("SELECT xp, level, first_name FROM users WHERE id = %s", (session['user_id'],))
    user_stats = cursor.fetchone()

    # Fetch top 10 users
    cursor.execute("SELECT first_name, last_name, xp, level, profile_image FROM users ORDER BY xp DESC LIMIT 10")
    leaders = cursor.fetchall()

    return render_template('focus/leaderboard.html', stats=user_stats, leaders=leaders)

# -------------------------------------------------
# Focus Actions (API Endpoints)
# -------------------------------------------------

@app.route('/focus/add_task', methods=['POST'])
@db_task
def add_task(cursor):
    """API endpoint to add a new task."""
    if 'user_id' not in session: return jsonify({'status': 'error'})

    title = request.form.get('title')
    category = request.form.get('category')
    est_time = request.form.get('estimated_time')
    
    cursor.execute("INSERT INTO tasks (user_id, title, category, estimated_time, status) VALUES (%s, %s, %s, %s, 'pending')", 
                   (session['user_id'], title, category, est_time))
    
    return redirect(url_for('focus_tasks'))

@app.route('/focus/start_task/<int:task_id>')
@db_task
def start_task(cursor, task_id):
    """API endpoint to move a task to 'in_progress'."""
    if 'user_id' not in session: return redirect(url_for('login'))
    cursor.execute("UPDATE tasks SET status = 'in_progress' WHERE id = %s AND user_id = %s", (task_id, session['user_id']))
    return redirect(url_for('focus_tasks'))

@app.route('/focus/complete_task/<int:task_id>')
@db_task
def complete_task(cursor, task_id):
    """API endpoint to mark a task as 'completed' and award XP."""
    if 'user_id' not in session: return redirect(url_for('login'))
    cursor.execute("UPDATE tasks SET status = 'completed' WHERE id = %s AND user_id = %s", (task_id, session['user_id']))
    cursor.execute("UPDATE users SET xp = xp + 50 WHERE id = %s", (session['user_id'],))
    return redirect(url_for('focus_tasks'))

@app.route('/focus/save_session', methods=['POST'])
@db_task
def save_session(cursor):
    """API endpoint to save a completed study session and award XP."""
    if 'user_id' not in session: return {'status': 'error'}, 401
    data = request.json
    duration = data.get('duration')
    mode = data.get('mode')
    cursor.execute("INSERT INTO study_sessions (user_id, duration, mode) VALUES (%s, %s, %s)", (session['user_id'], duration, mode))
    xp_gained = duration * 10
    cursor.execute("UPDATE users SET xp = xp + %s WHERE id = %s", (xp_gained, session['user_id']))
    return {'status': 'success', 'xp_gained': xp_gained}



if __name__ == '__main__':
    app.run(debug=True)
