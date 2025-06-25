from datetime import datetime
from app import db
from flask_login import UserMixin
from sqlalchemy import LargeBinary, func
import pickle

def get_current_datetime():
    return datetime.utcnow()

def get_current_date():
    return datetime.utcnow().date()

def get_current_time():
    return datetime.utcnow().time()

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(20), nullable=False, default='supervisor')  # 'superuser', 'supervisor'
    full_name = db.Column(db.String(100), nullable=False)
    created_at = db.Column(db.DateTime, default=get_current_datetime)
    is_active = db.Column(db.Boolean, default=True)
    
    # Relationships
    categories = db.relationship('JobCategory', backref='creator', lazy=True, cascade='all, delete-orphan')
    supervisor_profile = db.relationship('Supervisor', backref='user', uselist=False, cascade='all, delete-orphan')

class CompanyProfile(db.Model):
    __tablename__ = 'company_profile'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False, default='Company Name')
    logo_filename = db.Column(db.String(255))
    about = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=get_current_datetime)
    updated_at = db.Column(db.DateTime, default=get_current_datetime, onupdate=get_current_datetime)

class JobCategory(db.Model):
    __tablename__ = 'job_categories'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    created_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=get_current_datetime)
    
    # Relationships
    job_titles = db.relationship('JobTitle', backref='category', lazy=True, cascade='all, delete-orphan')

class JobTitle(db.Model):
    __tablename__ = 'job_titles'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey('job_categories.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=get_current_datetime)
    
    # Relationships
    employees = db.relationship('Employee', backref='job_title', lazy=True)

class Supervisor(db.Model):
    __tablename__ = 'supervisors'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, unique=True)
    full_name = db.Column(db.String(100), nullable=False)
    created_at = db.Column(db.DateTime, default=get_current_datetime)
    
    # Relationships
    employees = db.relationship('Employee', backref='supervisor', lazy=True)
    attendance_records = db.relationship('Attendance', backref='marked_by_supervisor', lazy=True)

class Employee(db.Model):
    __tablename__ = 'employees'
    
    id = db.Column(db.Integer, primary_key=True)
    employee_number = db.Column(db.String(50), unique=True, nullable=False)
    name = db.Column(db.String(100), nullable=False)
    job_title_id = db.Column(db.Integer, db.ForeignKey('job_titles.id'))
    address = db.Column(db.Text)
    contact_number = db.Column(db.String(20))
    email = db.Column(db.String(120))
    supervisor_id = db.Column(db.Integer, db.ForeignKey('supervisors.id'))
    face_encoding = db.Column(LargeBinary)  # Store face encoding as binary data
    created_at = db.Column(db.DateTime, default=get_current_datetime)
    is_active = db.Column(db.Boolean, default=True)
    
    # Relationships
    attendance_records = db.relationship('Attendance', backref='employee', lazy=True)
    
    def set_face_encoding(self, encoding):
        """Store face encoding as binary data"""
        if encoding is not None:
            self.face_encoding = pickle.dumps(encoding)
    
    def get_face_encoding(self):
        """Retrieve face encoding from binary data"""
        if self.face_encoding:
            return pickle.loads(self.face_encoding)
        return None

class Attendance(db.Model):
    __tablename__ = 'attendance'
    
    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey('employees.id'), nullable=False)
    date = db.Column(db.Date, nullable=False, default=get_current_date)
    time = db.Column(db.Time, nullable=False, default=get_current_time)
    datetime = db.Column(db.DateTime, nullable=False, default=get_current_datetime)
    latitude = db.Column(db.Float)
    longitude = db.Column(db.Float)
    marked_by_id = db.Column(db.Integer, db.ForeignKey('supervisors.id'))
    created_at = db.Column(db.DateTime, default=get_current_datetime)
    
    # Add constraint to prevent duplicate attendance per day
    __table_args__ = (db.UniqueConstraint('employee_id', 'date', name='unique_daily_attendance'),)

# Association table for supervisor-category access
supervisor_categories = db.Table('supervisor_categories',
    db.Column('supervisor_id', db.Integer, db.ForeignKey('supervisors.id'), primary_key=True),
    db.Column('category_id', db.Integer, db.ForeignKey('job_categories.id'), primary_key=True)
)

# Add many-to-many relationship
Supervisor.allowed_categories = db.relationship('JobCategory', secondary=supervisor_categories, backref='supervisors')