from flask import render_template, redirect, url_for, flash, request, session
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import check_password_hash
from app import app, db
from models.user import User

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
        
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        user = User.query.filter_by(username=username).first()
        
        if user and check_password_hash(user.password, password) and user.is_active:
            login_user(user)
            next_page = request.args.get('next')
            flash('Login berhasil!', 'success')
            return redirect(next_page or url_for('index'))
        else:
            flash('Login gagal. Periksa username dan password Anda', 'danger')
    
    return render_template('auth/login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Anda telah keluar dari sistem', 'success')
    return redirect(url_for('login'))