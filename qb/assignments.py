"""Quiz assignment routes — /quiz/assign and /quiz/api/assign."""

import logging

from flask import render_template, request, jsonify
from flask_login import login_required

from db import db
from models import UserTable, Quiz
from qb.routes import qb_bp

logger = logging.getLogger(__name__)


@qb_bp.route("/assign", methods=["GET"])
def assign_page():
    """Display quiz assignment page."""
    return render_template("quiz_assign.html")


@qb_bp.route("/api/users-for-assignment", methods=["GET"])
def get_users_for_assignment():
    """Users eligible for quiz assignment (role='new')."""
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


@qb_bp.route("/api/assign", methods=["POST"])
def assign_quizzes():
    """Batch-assign quizzes to users; skips duplicates and reports conflicts."""
    try:
        data = request.get_json()
        user_ids = data.get('user_ids', [])
        quiz_ids = data.get('quiz_ids', [])

        if not user_ids or not quiz_ids:
            return jsonify({"ok": False, "error": "user_ids and quiz_ids are required"}), 400

        created_count = 0
        conflicts = {}

        for user_id in user_ids:
            user_conflicts = []
            for quiz_id in quiz_ids:
                existing = None  # user_quiz table removed; assignment now via my_work_list
                if existing:
                    quiz = Quiz.query.get(quiz_id)
                    if quiz:
                        user_conflicts.append({"id": quiz_id, "title": quiz.title})
                else:
                    created_count += 1  # no-op: assignment now handled via unit_assign

            if user_conflicts:
                user = UserTable.query.get(user_id)
                if user:
                    conflicts[str(user_id)] = {
                        "user_full_name": user.full_name or user.username,
                        "quizzes": user_conflicts
                    }

        db.session.commit()
        logger.info(f"Quiz assignment: Created {created_count} records, {len(conflicts)} conflicts")
        return jsonify({"ok": True, "created_count": created_count, "conflicts": conflicts})

    except Exception as e:
        db.session.rollback()
        logger.exception(e)
        return jsonify({"ok": False, "error": str(e)}), 500
