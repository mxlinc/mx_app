"""Quiz assignment routes — /quiz/assign and /quiz/api/direct-assign."""

import logging

from flask import render_template, request, jsonify
from flask_login import login_required, current_user

from db import db
from models import UserTable, Quiz, MyWorkList
from qb.routes import qb_bp

logger = logging.getLogger(__name__)


@qb_bp.route("/assign", methods=["GET"])
def assign_page():
    """Display quiz assignment page."""
    return render_template("quiz_assign.html")


@qb_bp.route("/api/users-for-assignment", methods=["GET"])
@login_required
def get_users_for_assignment():
    """Users eligible for quiz assignment (role='student_new')."""
    try:
        users = UserTable.query.filter_by(user_role='student_new').all()
        users_data = sorted(
            [{'id': u.id, 'full_name': u.full_name or u.username, 'username': u.username} for u in users],
            key=lambda x: x['full_name']
        )
        return jsonify({'ok': True, 'users': users_data})
    except Exception as e:
        logger.exception(e)
        return jsonify({'ok': False, 'error': str(e)}), 500


@qb_bp.route("/api/direct-assign", methods=["POST"])
@login_required
def direct_assign_quizzes():
    """Two-phase assignment.

    First call (force=False): checks for existing my_work_list rows matching
    any (user, item_code) pair and returns conflicts without writing.
    Second call (force=True): creates new rows, skipping exact duplicates
    (same user + au_name + item_code).
    """
    if current_user.user_role not in ('admin', 'admin_new'):
        return jsonify({'ok': False, 'error': 'Forbidden'}), 403

    data     = request.get_json(force=True)
    user_ids = data.get('user_ids', [])
    quiz_ids = data.get('quiz_ids', [])
    au_name  = (data.get('au_name') or '').strip()
    force    = data.get('force', False)

    if not user_ids or not quiz_ids:
        return jsonify({'ok': False, 'error': 'user_ids and quiz_ids are required'}), 400
    if not au_name:
        return jsonify({'ok': False, 'error': 'Unit name is required'}), 400

    quizzes  = Quiz.query.filter(Quiz.id.in_(quiz_ids)).all()
    quiz_map = {q.id: q for q in quizzes}
    codes    = {q.id: q.quiz_code for q in quizzes}
    users    = UserTable.query.filter(UserTable.id.in_(user_ids)).all()
    user_map = {u.id: u for u in users}

    if not force:
        conflicts = []
        for uid in user_ids:
            user = user_map.get(uid)
            if not user:
                continue
            for qid in quiz_ids:
                qcode = codes.get(qid)
                if not qcode:
                    continue
                existing = MyWorkList.query.filter_by(user=user.username, item_code=qcode).first()
                if existing:
                    conflicts.append({
                        'user_id':          uid,
                        'full_name':        user.full_name or user.username,
                        'quiz_id':          qid,
                        'quiz_code':        qcode,
                        'title':            quiz_map[qid].title,
                        'existing_au_name': existing.au_name,
                        'existing_status':  existing.status,
                    })
        if conflicts:
            return jsonify({'ok': True, 'conflicts': conflicts, 'created': 0})

    created = skipped = 0
    for uid in user_ids:
        user = user_map.get(uid)
        if not user:
            continue
        for qid in quiz_ids:
            qcode = codes.get(qid)
            if not qcode:
                continue
            exists = MyWorkList.query.filter_by(
                user=user.username, au_name=au_name, item_code=qcode
            ).first()
            if exists:
                skipped += 1
                continue
            db.session.add(MyWorkList(
                user=user.username,
                au_name=au_name,
                item_code=qcode,
                item_detail=None,
                views=0,
                status='assigned',
                user_id=uid,
            ))
            created += 1

    db.session.commit()
    msg = f'Assigned {created} quiz(zes).'
    if skipped:
        msg += f' Skipped {skipped} exact duplicate(s).'
    logger.info('Direct quiz assignment: au_name=%r created=%s skipped=%s by=%s',
                au_name, created, skipped, current_user.username)
    return jsonify({'ok': True, 'conflicts': [], 'created': created,
                    'skipped': skipped, 'message': msg})
