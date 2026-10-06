"""Latest completed quizzes and short-lived student session presence."""

import logging
import re
from datetime import datetime, timedelta, timezone
from uuid import uuid4
from zoneinfo import ZoneInfo

import click
from flask import flash, jsonify, render_template, request, session, url_for
from flask_login import current_user, login_required
from sqlalchemy.dialects.postgresql import insert as postgres_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.exc import SQLAlchemyError

from db import db
from lms.routes import lms_bp
from models import MyWorkList, StudentPresence, UserTable

logger = logging.getLogger(__name__)
STUDENT_ROLES = ('student', 'student_new', 'new')
PRESENCE_WINDOW = timedelta(minutes=5)
REPORT_TIMEZONE = ZoneInfo('America/New_York')


def utc_now():
    return datetime.now(timezone.utc).replace(tzinfo=None)


def user_label(user, username=None):
    username = username or user.username
    if user and user.full_name:
        return f'{user.full_name} ({username})'
    return username


def online_students(now):
    users = (
        UserTable.query.join(StudentPresence, StudentPresence.user_id == UserTable.id)
        .filter(
            UserTable.is_active.is_(True),
            UserTable.user_role.in_(STUDENT_ROLES),
            StudentPresence.last_seen >= now - PRESENCE_WINDOW,
            StudentPresence.last_seen <= now,
        )
        .distinct()
        .order_by(UserTable.full_name, UserTable.username)
        .all()
    )
    return [user_label(user) for user in users]


@lms_bp.route('/latest-report')
@login_required
def latest_report():
    if current_user.user_role not in ('admin', 'admin_new'):
        return 'Forbidden', 403

    now = utc_now()
    max_days = (now - datetime.min).days
    raw_days = request.args.get('days', '7')
    days = None
    error = None
    status = 200
    # Bound the string before int() so huge inputs cannot exceed Python's digit limit.
    normalized = raw_days.lstrip('0')
    if (not re.fullmatch(r'[0-9]+', raw_days)
            or not normalized or len(normalized) > len(str(max_days))):
        error = f'Enter a whole number of days between 1 and {max_days}.'
    else:
        days = int(normalized)
        if days > max_days:
            error = f'Enter a whole number of days between 1 and {max_days}.'
    if error:
        status = 400

    records = []
    students = []
    presence_error = None
    try:
        students = online_students(now)
        if not error:
            rows = (
                db.session.query(MyWorkList, UserTable)
                .outerjoin(UserTable, MyWorkList.user == UserTable.username)
                .filter(
                    MyWorkList.item_code.like('Q-%'),
                    MyWorkList.status == 'done',
                    MyWorkList.last_updated >= now - timedelta(days=days),
                    MyWorkList.last_updated <= now,
                )
                .order_by(MyWorkList.last_updated.desc(), MyWorkList.id.desc())
                .all()
            )
            records = [
                {
                    'user': user_label(user, work.user),
                    'item_code': work.item_code,
                    'score': work.score,
                    'updated': work.last_updated.replace(tzinfo=timezone.utc)
                    .astimezone(REPORT_TIMEZONE).strftime('%d %b %H:%M'),
                }
                for work, user in rows
            ]
    except SQLAlchemyError:
        db.session.rollback()
        logger.exception('Unable to load latest report')
        error = 'Unable to load the report. Please try again or contact an administrator.'
        presence_error = 'Unable to load currently logged in users.'
        status = 503

    response = render_template(
        'latest_report.html', records=records, online_users=students,
        days=raw_days, max_days=max_days, error=error, presence_error=presence_error,
    )
    return response, status, {'Cache-Control': 'private, no-store'}


@lms_bp.route('/api/student-presence', methods=['POST'])
def student_presence():
    if not current_user.is_authenticated or not current_user.is_active:
        return jsonify(error='Your login has expired. Please sign in again.'), 401
    if current_user.user_role not in STUDENT_ROLES:
        return jsonify(error='Student access required.'), 403
    if request.headers.get('X-MX-Presence') != '1':
        return jsonify(error='Invalid presence request.'), 400

    token = session.setdefault('presence_session', uuid4().hex)
    now = utc_now()
    try:
        dialect = db.engine.dialect.name
        if dialect == 'postgresql':
            insert = postgres_insert
        elif dialect == 'sqlite':
            insert = sqlite_insert
        else:
            raise RuntimeError(f'Presence storage does not support {dialect}')
        statement = insert(StudentPresence).values(
            session_id=token, user_id=current_user.id, last_seen=now,
        )
        db.session.execute(statement.on_conflict_do_update(
            index_elements=[StudentPresence.session_id],
            set_={'user_id': current_user.id, 'last_seen': now},
        ))
        StudentPresence.query.filter(
            StudentPresence.last_seen < now - PRESENCE_WINDOW,
        ).delete(synchronize_session=False)
        db.session.commit()
    except SQLAlchemyError:
        db.session.rollback()
        logger.exception('Unable to update student presence')
        return jsonify(error='Unable to update your online status. Please try again.'), 503
    return '', 204


@lms_bp.route('/api/latest-report/online-users')
@login_required
def latest_report_online_users():
    if current_user.user_role not in ('admin', 'admin_new'):
        return jsonify(error='Admin access required.'), 403
    try:
        return jsonify(users=online_students(utc_now())), 200, {
            'Cache-Control': 'private, no-store',
        }
    except SQLAlchemyError:
        db.session.rollback()
        logger.exception('Unable to load student presence')
        return jsonify(error='Unable to load currently logged in users.'), 503


def init_report_features(app):
    @app.cli.command('init-report-presence')
    def init_presence_table():
        """Create the additive presence table in APP_SCHEMA."""
        StudentPresence.__table__.create(db.engine, checkfirst=True)
        click.echo('Student presence table is ready.')

    @app.before_request
    def clear_presence_on_logout():
        if request.endpoint != 'lms.logout':
            return
        token = session.pop('presence_session', None)
        if token and current_user.is_authenticated:
            try:
                StudentPresence.query.filter_by(
                    session_id=token, user_id=current_user.id,
                ).delete(synchronize_session=False)
                db.session.commit()
            except SQLAlchemyError:
                db.session.rollback()
                logger.exception('Unable to clear student presence on logout')
                flash('Signed out, but your online status may remain for up to 5 minutes.', 'warning')

    @app.after_request
    def add_student_heartbeat(response):
        # Standalone quiz and legacy pages do not all extend the shared base template.
        if (response.status_code != 200 or response.mimetype != 'text/html'
                or response.is_streamed or response.direct_passthrough
                or response.headers.get('Content-Disposition')
                or not current_user.is_authenticated
                or not current_user.is_active
                or current_user.user_role not in STUDENT_ROLES):
            return response
        html = response.get_data(as_text=True)
        closing_body = re.search(r'</body\s*>', html, re.IGNORECASE)
        if not closing_body:
            return response
        session.setdefault('presence_session', uuid4().hex)
        script = (
            f'<script src="{url_for("static", filename="js/student_presence.js")}" '
            f'data-presence-url="{url_for("lms.student_presence")}" defer></script>'
        )
        response.set_data(html[:closing_body.start()] + script + html[closing_body.start():])
        response.headers['Cache-Control'] = 'private, no-store'
        return response
