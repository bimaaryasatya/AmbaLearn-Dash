from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime
import uuid

db = SQLAlchemy()

# Note: These models must match the AmbaLearn-Engine models exactly

class SystemSetting(db.Model):
    __tablename__ = 'system_settings'
    key = db.Column(db.String(50), primary_key=True)
    value = db.Column(db.Text, nullable=True)

class Organization(db.Model):
    __tablename__ = 'organizations'
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = db.Column(db.String(120), nullable=False)
    description = db.Column(db.Text, nullable=True)
    manager_id = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=True)
    registered_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    invitation_code = db.Column(db.String(6), unique=True, nullable=False)

    manager = db.relationship('User', backref='managed_organization', foreign_keys=[manager_id])

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    username = db.Column(db.String(80), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=True)
    google_id = db.Column(db.String(128), unique=True, nullable=True)
    picture = db.Column(db.String(255), nullable=True)
    birthday = db.Column(db.Date, nullable=True)
    registered_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    last_login = db.Column(db.DateTime, nullable=True)
    organization_id = db.Column(db.String(36), db.ForeignKey('organizations.id'), nullable=True)
    role = db.Column(db.String(20), nullable=False, default='user')  # user, manager, admin

    organization = db.relationship('Organization', backref='users', foreign_keys=[organization_id])

class ActiveUser(db.Model):
    __tablename__ = 'active_users'
    date = db.Column(db.Date, primary_key=True)
    amount = db.Column(db.Integer, nullable=False, default=0)

class Feedback(db.Model):
    __tablename__ = 'feedbacks'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=False)
    comment = db.Column(db.Text, nullable=False)
    course_id = db.Column(db.String(36), nullable=False)
    course_name = db.Column(db.String(255), nullable=False)
    sentiment = db.Column(db.String(20), nullable=False, default='unknown')
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    user = db.relationship('User', backref='feedbacks')

class PromptStat(db.Model):
    __tablename__ = 'prompts_stat'
    date = db.Column(db.Date, primary_key=True)
    amount = db.Column(db.Integer, nullable=False, default=0)

class ExamScore(db.Model):
    __tablename__ = 'exam_scores'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=False)
    exam_id = db.Column(db.String(36), nullable=False)
    exam_title = db.Column(db.String(255), nullable=False)
    score = db.Column(db.Integer, nullable=False)
    exam_date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    user = db.relationship('User', backref='exam_scores')

class CourseMetadata(db.Model):
    __tablename__ = 'course_metadata'
    uid = db.Column(db.String(36), primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, nullable=True)
    owner_id = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=True) # For user courses
    organization_id = db.Column(db.String(36), db.ForeignKey('organizations.id'), nullable=True) # For org courses
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
