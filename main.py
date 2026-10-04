from flask import Flask, abort
from datetime import timedelta
from flask_login import LoginManager, current_user
from flask_wtf.csrf import CSRFProtect
from functools import wraps
import os
from dotenv import load_dotenv
from models import db, User
from flask import Flask
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

load_dotenv()

app = Flask(__name__)
limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=["200 per day", "50 per hour"], 
    storage_uri="memory://" 
)
csrf = CSRFProtect(app)
app.secret_key = os.getenv('SECRET_KEY', 'default_secret_tomori')
app.config['REMEMBER_COOKIE_DURATION'] = timedelta(days=30)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///inventaris_job_tomori.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Middleware hak akses dipindah ke sini
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if current_user.role != 'Admin':
            abort(403)
        return f(*args, **kwargs)
    return decorated_function

# Registrasi semua pecahan rute dari dalam folder 'routes'
from routes import routes_main, routes_inventory, routes_consumable, routes_karyawan