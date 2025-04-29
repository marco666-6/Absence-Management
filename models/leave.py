from app import db
from datetime import datetime
import pytz
from config import Config

class Leave(db.Model):
    __tablename__ = 'leaves'
    
    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey('employees.id'), nullable=False)
    leave_type = db.Column(db.String(20), nullable=False)  # 'sakit', 'cuti', 'izin'
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    reason = db.Column(db.Text, nullable=False)
    document_url = db.Column(db.String(255), nullable=True)  # For attaching doctor's note, etc.
    status = db.Column(db.String(20), default='pending')  # 'pending', 'approved', 'rejected'
    approved_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    approval_date = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(pytz.timezone(Config.TIMEZONE)))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(pytz.timezone(Config.TIMEZONE)), 
                          onupdate=lambda: datetime.now(pytz.timezone(Config.TIMEZONE)))
    
    # Relationships
    approver = db.relationship('User', backref=db.backref('approved_leaves', lazy=True))
    
    def __repr__(self):
        return f'<Leave {self.employee_id} from {self.start_date} to {self.end_date}>'