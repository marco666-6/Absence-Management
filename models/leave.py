from app import db
from datetime import datetime
import pytz
from config import Config

class Attendance(db.Model):
    __tablename__ = 'attendances'
    
    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey('employees.id'), nullable=False)
    date = db.Column(db.Date, nullable=False)
    check_in = db.Column(db.DateTime, nullable=True)
    check_out = db.Column(db.DateTime, nullable=True)
    status = db.Column(db.String(20), default='present')  # 'present', 'late', 'absent'
    notes = db.Column(db.Text, nullable=True)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(pytz.timezone(Config.TIMEZONE)))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(pytz.timezone(Config.TIMEZONE)), 
                          onupdate=lambda: datetime.now(pytz.timezone(Config.TIMEZONE)))
    
    # Relationships
    creator = db.relationship('User', backref=db.backref('created_attendances', lazy=True))
    
    def __repr__(self):
        return f'<Attendance {self.employee_id} on {self.date}>'