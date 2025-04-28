from app import db
from datetime import datetime
import pytz
import uuid
from config import Config

class Employee(db.Model):
    __tablename__ = 'employees'
    
    id = db.Column(db.Integer, primary_key=True)
    nik = db.Column(db.String(20), unique=True, nullable=False)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    phone = db.Column(db.String(20))
    position = db.Column(db.String(50))
    department = db.Column(db.String(50))
    team_leader_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    qr_token = db.Column(db.String(64), unique=True, default=lambda: str(uuid.uuid4()))
    profile_pic = db.Column(db.String(255), nullable=True)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(pytz.timezone(Config.TIMEZONE)))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(pytz.timezone(Config.TIMEZONE)), 
                          onupdate=lambda: datetime.now(pytz.timezone(Config.TIMEZONE)))
    
    # Relationships
    team_leader = db.relationship('User', backref=db.backref('employees', lazy=True))
    attendances = db.relationship('Attendance', backref='employee', lazy=True)
    leaves = db.relationship('Leave', backref='employee', lazy=True)
    
    def __repr__(self):
        return f'<Employee {self.name}>'