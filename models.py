"""SQLAlchemy models for the application."""

from flask_login import UserMixin
from sqlalchemy.dialects.postgresql import JSON
from db import db
from config import CURRENT_SCHEMA


class UserTable(db.Model, UserMixin):
    __tablename__ = 'user_table'
    __table_args__ = {'schema': CURRENT_SCHEMA}
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String, unique=True)
    full_name = db.Column(db.String)
    user_role = db.Column(db.String)   # admin / teacher / student
    password_hash = db.Column(db.String)  # for demo only, use hashing in prod
    is_active = db.Column(db.Boolean, default=True)
    # Controls whether the user should appear on assignment lists
    can_assign_work = db.Column(db.Boolean, default=True)

    def get_id(self):
        return str(self.id)
    

class MXWorks(db.Model):
    __tablename__ = 'mx_works'
    __table_args__ = {'schema': CURRENT_SCHEMA}
    work_id = db.Column(db.Integer, primary_key=True)
    work_name = db.Column(db.Text, nullable=False)
    old_work_id = db.Column(db.String(20))
    work_level = db.Column(db.String(20))
    work_filename = db.Column(db.String(120))
    work_link = db.Column(db.Text, nullable=False)
    topic = db.Column(db.String(100))
    subtopic = db.Column(db.String(200))
    work_comments = db.Column(db.Text)


class MXWorkPacks(db.Model):
    __tablename__ = 'mx_work_packs'
    __table_args__ = {'schema': CURRENT_SCHEMA}
    pack_id = db.Column(db.Integer, primary_key=True)
    pack_desc = db.Column(db.Text)
    pack_contents = db.Column(db.Text)
    broad_area = db.Column(db.String(200))
    is_deleted = db.Column(db.Boolean, default=False)
    last_updated = db.Column(db.DateTime)


class UserWorks(db.Model):
    __tablename__ = 'user_works'
    __table_args__ = {'schema': CURRENT_SCHEMA}

    username = db.Column(db.String(20), primary_key=True)
    pack_id = db.Column(db.Integer, primary_key=True)
    work_id = db.Column(db.Integer, primary_key=True)

    work_level = db.Column(db.Text)
    work_name = db.Column(db.Text)
    work_link = db.Column(db.Text)
    work_rank = db.Column(db.Integer)
    pack_desc = db.Column(db.Text)
    work_score = db.Column(db.String(20))
    incorrect = db.Column(db.String(100))
    work_views = db.Column(db.Integer)
    work_status = db.Column(db.String(100), default='future', nullable=False)
    last_updated = db.Column(db.DateTime)


class EmailMessage(db.Model):
    __tablename__ = 'emails'
    __table_args__ = {'schema': CURRENT_SCHEMA}
    id = db.Column(db.Integer, primary_key=True)
    sender = db.Column(db.String)
    subject = db.Column(db.String)
    body = db.Column(db.Text)
    parsed = db.Column(JSON)


class DonePacks(db.Model):
    __tablename__ = 'done_packs'
    __table_args__ = {'schema': CURRENT_SCHEMA}
    
    username = db.Column(db.String(20), primary_key=True)
    pack_id = db.Column(db.Integer, primary_key=True)
    completed_at = db.Column(db.DateTime(timezone=True), default=db.func.now())


class ContactSubmission(db.Model):
    __tablename__ = 'contact_submissions'
    __table_args__ = {'schema': CURRENT_SCHEMA}

    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, server_default=db.func.now())
    ip_address = db.Column(db.String(100))
    sms_sent = db.Column(db.Boolean, default=False)
    sms_sent_at = db.Column(db.DateTime)


class QBank(db.Model):
    __tablename__ = 'q_bank'
    __table_args__ = {'schema': CURRENT_SCHEMA}
    id = db.Column(db.Integer, primary_key=True)
    type = db.Column(db.String(20), nullable=False)
    json = db.Column(JSON, nullable=False)
    topic = db.Column(db.String(100))
    subtopic = db.Column(db.String(100))
    level = db.Column(db.String(1))
    created_at = db.Column(db.DateTime, default=db.func.now())
    updated_at = db.Column(db.DateTime, default=db.func.now(), onupdate=db.func.now())
