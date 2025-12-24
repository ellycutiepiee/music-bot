import os
from flask import Flask, redirect, url_for, render_template, request, flash, session
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from requests_oauthlib import OAuth2Session
from models import db, User, SongHistory
from werkzeug.utils import secure_filename
from threading import Thread

# Allow HTTP for OAuth locally
os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('FLASK_SECRET_KEY', 'super_secret_key_change_me')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///music_bot.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB max upload

db.init_app(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# Discord OAuth Config
CLIENT_ID = os.getenv('DISCORD_CLIENT_ID')
CLIENT_SECRET = os.getenv('DISCORD_CLIENT_SECRET')
REDIRECT_URI = os.getenv('DISCORD_REDIRECT_URI', 'http://127.0.0.1:8080/callback')
AUTHORIZATION_BASE_URL = 'https://discord.com/api/oauth2/authorize'
TOKEN_URL = 'https://discord.com/api/oauth2/token'
API_BASE_URL = 'https://discord.com/api'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(user_id)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login')
def login():
    if not CLIENT_ID or not CLIENT_SECRET:
        flash('OAuth credentials not configured on server.')
        return redirect(url_for('index'))
    
    discord = OAuth2Session(CLIENT_ID, redirect_uri=REDIRECT_URI, scope=['identify'])
    authorization_url, state = discord.authorization_url(AUTHORIZATION_BASE_URL)
    session['oauth_state'] = state
    return redirect(authorization_url)

@app.route('/callback')
def callback():
    if not CLIENT_ID or not CLIENT_SECRET:
        return redirect(url_for('index'))
        
    discord = OAuth2Session(CLIENT_ID, redirect_uri=REDIRECT_URI, state=session.get('oauth_state'))
    try:
        token = discord.fetch_token(TOKEN_URL, client_secret=CLIENT_SECRET, authorization_response=request.url)
        session['oauth_token'] = token
        
        discord = OAuth2Session(CLIENT_ID, token=token)
        user_info = discord.get(f'{API_BASE_URL}/users/@me').json()
        
        user_id = user_info['id']
        username = user_info['username']
        avatar_url = f"https://cdn.discordapp.com/avatars/{user_id}/{user_info['avatar']}.png"

        user = User.query.get(user_id)
        if not user:
            user = User(id=user_id, username=username, avatar_url=avatar_url)
            db.session.add(user)
        else:
            user.username = username
            user.avatar_url = avatar_url
        
        db.session.commit()
        login_user(user)
        return redirect(url_for('dashboard'))
    except Exception as e:
        flash(f'Authentication failed: {e}')
        return redirect(url_for('index'))

@app.route('/dashboard')
@login_required
def dashboard():
    history = SongHistory.query.filter_by(user_id=current_user.id).order_by(SongHistory.played_at.desc()).limit(50).all()
    files = os.listdir(app.config['UPLOAD_FOLDER'])
    return render_template('dashboard.html', history=history, files=files)

@app.route('/upload', methods=['POST'])
@login_required
def upload_file():
    if 'file' not in request.files:
        flash('No file part')
        return redirect(url_for('dashboard'))
    
    file = request.files['file']
    if file.filename == '':
        flash('No selected file')
        return redirect(url_for('dashboard'))
    
    if file:
        filename = secure_filename(file.filename)
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        flash(f'File {filename} uploaded successfully')
        return redirect(url_for('dashboard'))

@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('index'))

# Helper function for the bot to add history
def add_history(user_id, title, url, platform):
    with app.app_context():
        # Ensure user exists (in case they haven't logged into web yet)
        # Note: If user hasn't logged in, we might not have their username, so we create a placeholder or skip
        user = User.query.get(user_id)
        if not user:
            # We can create a placeholder user
            user = User(id=str(user_id), username="Unknown User", avatar_url="")
            db.session.add(user)
        
        history = SongHistory(user_id=str(user_id), title=title, url=url, platform=platform)
        db.session.add(history)
        db.session.commit()

def run():
    # Create DB if not exists
    with app.app_context():
        db.create_all()
    
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run)
    t.start()
