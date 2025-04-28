from app import db
from flask_login import UserMixin
from datetime import datetime
import pytz
from config import Config

class User(db.Model, UserMixin):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False)  # 'admin' or 'team_leader'
    name = db.Column(db.String(100))
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(pytz.timezone(Config.TIMEZONE)))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(pytz.timezone(Config.TIMEZONE)), 
                          onupdate=lambda: datetime.now(pytz.timezone(Config.TIMEZONE)))
    
    def __repr__(self):
        return f'<User {self.username}>'