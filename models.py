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
    user_role = db.Column(db.String)   # admin / teacher / student_new / student
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


class Video(db.Model):
    __tablename__ = 'videos'
    __table_args__ = {'schema': CURRENT_SCHEMA}
    id           = db.Column(db.Integer, primary_key=True)
    lesson_code  = db.Column(db.Text, server_default=db.text(
        "('V-'::text || lpad(nextval('prod.videos_code_seq'::regclass)::text, 4, '0'::text))"
    ))
    last_updated = db.Column(db.DateTime, server_default=db.func.now())
    file_name    = db.Column(db.String(255), nullable=False)
    display_name = db.Column(db.String(255), nullable=False)
    broad_area   = db.Column(db.String(100))
    details      = db.Column(db.Text)


class Interaction(db.Model):
    __tablename__ = 'interactions'
    __table_args__ = {'schema': CURRENT_SCHEMA}
    id           = db.Column(db.Integer, primary_key=True)
    lesson_code  = db.Column(db.Text, server_default=db.text(
        "('I-'::text || lpad(nextval('prod.interactions_code_seq'::regclass)::text, 4, '0'::text))"
    ))
    last_updated = db.Column(db.DateTime, server_default=db.func.now())
    file_name    = db.Column(db.String(255), nullable=False)
    display_name = db.Column(db.String(255), nullable=False)
    broad_area   = db.Column(db.String(100))
    details      = db.Column(db.Text)


class AUnit(db.Model):
    __tablename__ = 'a_unit'
    __table_args__ = {'schema': CURRENT_SCHEMA}
    au_id        = db.Column(db.Integer, primary_key=True)
    au_area      = db.Column(db.String(100))
    au_name      = db.Column(db.String(255), nullable=False)
    au_topic     = db.Column(db.String(255))
    au_level     = db.Column(db.String(20))
    au_content   = db.Column(db.Text)
    last_updated = db.Column(db.DateTime, server_default=db.func.now())


class FormatHelper(db.Model):
    __tablename__ = 'format_helper'
    __table_args__ = {'schema': CURRENT_SCHEMA}
    id             = db.Column(db.Integer, primary_key=True)
    item           = db.Column(db.String(100), nullable=False)
    latex_snippet  = db.Column(db.Text, nullable=False)
    sort_order     = db.Column(db.Integer, default=0, nullable=False)


class QBank(db.Model):
    __tablename__ = 'q_bank'
    __table_args__ = {'schema': CURRENT_SCHEMA}
    id = db.Column(db.Integer, primary_key=True)
    type = db.Column(db.String(20), nullable=False)
    json = db.Column(JSON, nullable=False)
    topic = db.Column(db.String(100))
    subtopic = db.Column(db.String(100))
    level = db.Column(db.String(20))
    created_at = db.Column(db.DateTime, default=db.func.now())
    updated_at = db.Column(db.DateTime, default=db.func.now(), onupdate=db.func.now())
    sync_required = db.Column(db.Boolean, default=False, nullable=False, server_default='false')


class Quiz(db.Model):
    """Quiz - collection of questions organized sequentially."""
    __tablename__ = 'quiz'
    __table_args__ = {'schema': CURRENT_SCHEMA}
    
    id = db.Column(db.Integer, primary_key=True)
    quiz_code = db.Column(db.String(10))
    title = db.Column(db.String(300), nullable=False)
    description = db.Column(db.Text)
    topic = db.Column(db.String(100))
    subtopic = db.Column(db.String(100))
    level = db.Column(db.String(20))
    question_ids = db.Column(db.String(5000))  # Comma-separated question IDs from q_bank
    questions_json = db.Column(db.JSON)        # Pre-baked HTML question list; rebuilt on save/question-edit

    @property
    def question_count(self):
        if not self.question_ids:
            return 0
        return len([i for i in self.question_ids.split(',') if i.strip()])
    status = db.Column(db.String(20), default='draft')  # 'draft' or 'published'
    created_at = db.Column(db.DateTime, default=db.func.now())
    updated_at = db.Column(db.DateTime, default=db.func.now(), onupdate=db.func.now())



class QuizExecution(db.Model):
    """Per-question answer record for a quiz session."""
    __tablename__ = 'quiz_execution'
    __table_args__ = (
        db.PrimaryKeyConstraint('user_id', 'quiz_id', 'question_id'),
        {'schema': CURRENT_SCHEMA},
    )

    user_id           = db.Column(db.Integer, db.ForeignKey(f'{CURRENT_SCHEMA}.user_table.id', ondelete='CASCADE'), nullable=False)
    quiz_id           = db.Column(db.Integer, db.ForeignKey(f'{CURRENT_SCHEMA}.quiz.id',       ondelete='CASCADE'), nullable=False)
    question_id       = db.Column(db.Integer, db.ForeignKey(f'{CURRENT_SCHEMA}.q_bank.id',     ondelete='CASCADE'), nullable=False)
    question_sequence = db.Column(db.Integer, nullable=False)
    user_answer       = db.Column(db.String)
    correct_answer    = db.Column(db.String)
    is_correct        = db.Column(db.Boolean)
    created_at        = db.Column(db.DateTime, server_default=db.func.now())
    updated_at        = db.Column(db.DateTime, server_default=db.func.now(), onupdate=db.func.now())


class MyWorkList(db.Model):
    """Student work queue — one row per assigned item (quiz or video) per student."""
    __tablename__ = 'my_work_list'
    __table_args__ = {'schema': CURRENT_SCHEMA}

    id           = db.Column(db.Integer, primary_key=True)
    user         = db.Column(db.String(100), nullable=False)
    au_name      = db.Column(db.String(255), nullable=False)
    item_code    = db.Column(db.String(20),  nullable=False)
    item_detail  = db.Column(db.Text)
    views        = db.Column(db.Integer, nullable=False, default=0, server_default='0')
    status       = db.Column(db.String(20),  nullable=False, default='assigned', server_default='assigned')
    score        = db.Column(db.String(20))
    incorrect    = db.Column(db.Text)
    last_updated       = db.Column(db.DateTime, server_default=db.func.now(), onupdate=db.func.now())
    user_id            = db.Column(db.Integer, db.ForeignKey(f'{CURRENT_SCHEMA}.user_table.id', ondelete='SET NULL'), nullable=True)
    questions_answered = db.Column(db.Integer, nullable=False, default=0, server_default='0')


class UserStreak(db.Model):
    """Per-student running correct-answer streak counter."""
    __tablename__ = 'user_streak'
    __table_args__ = {'schema': CURRENT_SCHEMA}

    user_id    = db.Column(db.Integer, db.ForeignKey(f'{CURRENT_SCHEMA}.user_table.id', ondelete='CASCADE'), primary_key=True)
    streak     = db.Column(db.Integer, nullable=False, default=0, server_default='0')
    updated_at = db.Column(db.DateTime, server_default=db.func.now(), onupdate=db.func.now())
