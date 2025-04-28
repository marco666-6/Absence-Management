import os
from datetime import timedelta

class Config:
    # Secret key untuk keamanan aplikasi
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'kunci-rahasia-zenith-utama-mandiri'
    
    # Konfigurasi database
    SQLALCHEMY_DATABASE_URI = 'mysql://root:@localhost/absence_valdo'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Konfigurasi sesi
    PERMANENT_SESSION_LIFETIME = timedelta(hours=12)
    
    # Pengaturan upload file
    UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), 'static/uploads')
    MAX_CONTENT_LENGTH = 5 * 1024 * 1024  # Max 5MB uploads
    
    # Konfigurasi timezone
    TIMEZONE = 'Asia/Jakarta'