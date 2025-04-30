from flask import Flask, render_template, redirect, url_for, flash, request, session, jsonify, send_file
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from functools import wraps
from datetime import datetime, timedelta
import pytz
import os
import qrcode
import uuid
import io
import base64
from PIL import Image
from config import Config

app = Flask(__name__)
app.config.from_object(Config)

# Pastikan direktori upload ada
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Inisialisasi database
db = SQLAlchemy(app)

# Inisialisasi login manager
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Import models setelah inisialisasi db
from models.user import User
from models.employee import Employee
from models.attendance import Attendance
from models.leave import Leave

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Decorator untuk membatasi akses berdasarkan role
def role_required(roles):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated or current_user.role not in roles:
                flash('Anda tidak memiliki akses ke halaman ini', 'danger')
                return redirect(url_for('login'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator

# Import routes setelah semua inisialisasi
from controllers.auth_controller import *
from controllers.admin_controller import *
from controllers.team_leader_controller import *
from controllers.employee_controller import *

# Route utama
@app.route('/')
def index():
    if current_user.is_authenticated:
        if current_user.role == 'admin':
            return redirect(url_for('admin_dashboard'))
        elif current_user.role == 'team_leader':
            return redirect(url_for('team_leader_dashboard'))
    return redirect(url_for('login'))

# Error handlers
@app.errorhandler(404)
def page_not_found(e):
    return render_template('shared/404.html'), 404

@app.errorhandler(500)
def internal_server_error(e):
    return render_template('shared/500.html'), 500

if __name__ == '__main__':
    with app.app_context():
        db.create_all()  # Buat tabel jika belum ada
        
        # Buat user admin jika belum ada
        admin_exists = User.query.filter_by(username='admin').first()
        if not admin_exists:
            admin = User(
                username='admin',
                email='admin@zenith.com',
                name='admin',
                password=generate_password_hash('admin123'),
                role='admin',
                is_active=True
            )
            db.session.add(admin)
            db.session.commit()
            print("Admin user created!")
    
    app.run(debug=True)