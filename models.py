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


class Quiz(db.Model):
    """Quiz - collection of questions organized sequentially."""
    __tablename__ = 'quiz'
    __table_args__ = {'schema': CURRENT_SCHEMA}
    
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(300), nullable=False)
    description = db.Column(db.Text)
    topic = db.Column(db.String(100))
    subtopic = db.Column(db.String(100))
    question_ids = db.Column(db.String(5000))  # Comma-separated question IDs from q_bank
    question_count = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=db.func.now())
    updated_at = db.Column(db.DateTime, default=db.func.now(), onupdate=db.func.now())


class UserQuiz(db.Model):
    """User quiz execution tracking - stores user attempts and responses."""
    __tablename__ = 'user_quiz'
    __table_args__ = {'schema': CURRENT_SCHEMA}
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey(f'{CURRENT_SCHEMA}.user_table.id'), nullable=False)
    quiz_id = db.Column(db.Integer, db.ForeignKey(f'{CURRENT_SCHEMA}.quiz.id'), nullable=False)
    status = db.Column(db.String(50), default='in_progress')  # in_progress, completed, abandoned
    score = db.Column(db.Integer, default=0)
    responses = db.Column(db.Text)  # JSON string storing all responses {question_id: {answer, is_correct, feedback}}
    started_at = db.Column(db.DateTime, default=db.func.now())
    completed_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=db.func.now())
    updated_at = db.Column(db.DateTime, default=db.func.now(), onupdate=db.func.now())


# ==================== MONTESSORI SYSTEM (Separate from LMS) ==================== #

class MUser(db.Model):
    """Montessori student users - separate from LMS user_table."""
    __tablename__ = 'muser'
    __table_args__ = {'schema': CURRENT_SCHEMA}
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    token = db.Column(db.String(50), unique=True, nullable=False)
    created_at = db.Column(db.DateTime, default=db.func.now())


class MontessoriPackage(db.Model):
    """Montessori learning material packages."""
    __tablename__ = 'montessori_package'
    __table_args__ = {'schema': CURRENT_SCHEMA}
    
    id = db.Column(db.Integer, primary_key=True)
    subject = db.Column(db.String(200), nullable=False)
    topic = db.Column(db.String(300), nullable=False)
    work = db.Column(db.String(300), nullable=False)
    link = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=db.func.now())
    updated_at = db.Column(db.DateTime, default=db.func.now(), onupdate=db.func.now())
    is_deleted = db.Column(db.Boolean, default=False)


class MUserPackage(db.Model):
    """Assignment of packages to Montessori students with tracking."""
    __tablename__ = 'muser_package'
    __table_args__ = {'schema': CURRENT_SCHEMA}
    
    id = db.Column(db.Integer, primary_key=True)
    muser_id = db.Column(db.Integer, db.ForeignKey(f'{CURRENT_SCHEMA}.muser.id'), nullable=False)
    package_id = db.Column(db.Integer, db.ForeignKey(f'{CURRENT_SCHEMA}.montessori_package.id'), nullable=False)
    assigned_date = db.Column(db.DateTime, default=db.func.now())
    click_count = db.Column(db.Integer, default=0)
    last_accessed = db.Column(db.DateTime)
