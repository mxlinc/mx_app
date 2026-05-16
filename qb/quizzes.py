"""Quiz management routes — CRUD, preview, wizard, list."""

import logging

from flask import render_template, request, jsonify, redirect, url_for
from flask_login import login_required

from db import db
from models import AUnit, QBank, Quiz, FormatHelper, MyWorkList
from qb.db_utils import quiz_code
from qb.routes import qb_bp, get_handler

logger = logging.getLogger(__name__)


# ==================== SHARED HELPER ==================== #

def build_questions_json(question_ids: list) -> list:
    """Fetch questions from q_bank in one query and generate HTML for each.

    Returns the prepared list suitable for storing in quiz.questions_json
    and passing directly to the execution template.
    """
    if not question_ids:
        return []
    int_ids = [int(i) for i in question_ids]
    rows = QBank.query.filter(QBank.id.in_(int_ids)).all()
    by_id = {q.id: q for q in rows}

    result = []
    for qid in int_ids:
        q = by_id.get(qid)
        if not q:
            continue
        handler = get_handler(q.type)
        prepared = handler.prepare_html(q.json) if handler else dict(q.json)
        prepared['id'] = q.id
        result.append(prepared)
    return result


def rebuild_quizzes_for_question(question_id: int) -> None:
    """After a question is edited, rebuild questions_json for every quiz that contains it.

    Uses a simple LIKE scan — acceptable because quiz count is small and
    this is an admin-only operation.
    """
    affected = Quiz.query.filter(
        Quiz.question_ids.like(f'%{question_id}%')
    ).all()
    for quiz in affected:
        ids = [i.strip() for i in (quiz.question_ids or '').split(',') if i.strip()]
        # Confirm this quiz actually contains the question (avoid false LIKE matches)
        if str(question_id) not in ids:
            continue
        quiz.questions_json = build_questions_json(ids)
        logger.info("[QUIZ_REBUILD] quiz=%s after edit of question=%s", quiz.id, question_id)


# ==================== RESYNC ==================== #

@qb_bp.route("/api/resync-quizzes/count", methods=["GET"])
@login_required
def resync_pending_count():
    """Return the number of questions that have sync_required=True."""
    try:
        count = QBank.query.filter(QBank.sync_required == True).count()
        return jsonify({"ok": True, "pending": count})
    except Exception as e:
        logger.exception(e)
        return jsonify({"ok": False, "error": str(e)}), 500


@qb_bp.route("/api/resync-quizzes", methods=["POST"])
@login_required
def resync_quizzes():
    """Rebuild questions_json for all quizzes affected by dirty questions.

    Processes one dirty question at a time: rebuild all its quizzes, clear its
    flag, commit, then move to the next. A failure on one question is logged
    and skipped so the rest of the batch still completes.
    """
    dirty = QBank.query.filter(QBank.sync_required == True).all()
    if not dirty:
        return jsonify({"ok": True, "message": "Nothing to sync.", "synced": 0})

    synced = 0
    errors = []
    for q in dirty:
        try:
            rebuild_quizzes_for_question(q.id)
            q.sync_required = False
            db.session.commit()
            synced += 1
            logger.info("[RESYNC] question=%s synced successfully", q.id)
        except Exception as e:
            db.session.rollback()
            errors.append(q.id)
            logger.error("[RESYNC] failed for question=%s: %s", q.id, e)

    message = f"Synced {synced} question(s)."
    if errors:
        message += f" Failed for question IDs: {errors}."
    return jsonify({"ok": not errors, "message": message, "synced": synced, "failed": errors})


# ==================== TOPICS ==================== #

@qb_bp.route("/api/topics", methods=["GET"])
@login_required
def get_topics():
    try:
        topics = (db.session.query(QBank.topic)
                  .distinct()
                  .filter(QBank.topic.isnot(None))
                  .order_by(QBank.topic)
                  .all())
        return jsonify({"ok": True, "topics": [t[0] for t in topics if t[0]]})
    except Exception as e:
        logger.exception(e)
        return jsonify({"ok": False, "error": str(e)}), 400


# ==================== FORMAT HELPER ==================== #

@qb_bp.route("/api/format-snippets", methods=["GET"])
@login_required
def get_format_snippets():
    try:
        snippets = FormatHelper.query.order_by(FormatHelper.sort_order).all()
        return jsonify({"ok": True, "snippets": [
            {"item": s.item, "snippet": s.latex_snippet} for s in snippets
        ]})
    except Exception as e:
        logger.exception(e)
        return jsonify({"ok": False, "error": str(e)}), 500


# ==================== CREATE ==================== #

@qb_bp.route("/create-quiz", methods=["GET"])
@login_required
def create_quiz_page():
    return render_template("create_quiz.html")


@qb_bp.route("/create-quiz", methods=["POST"])
@login_required
def create_quiz():
    data = request.get_json()
    ids_str = data.get('question_ids', '').strip()
    question_ids = [qid.strip() for qid in ids_str.split(',') if qid.strip()] if ids_str else []
    quiz = Quiz(
        title=data.get('title', ''), description=data.get('description', ''),
        topic=data.get('topic', ''), subtopic=data.get('subtopic', ''),
        question_ids=','.join(question_ids), question_count=len(question_ids),
        questions_json=build_questions_json(question_ids)
    )
    db.session.add(quiz)
    db.session.commit()
    quiz.quiz_code = quiz_code(quiz.id)
    db.session.commit()
    return jsonify({'ok': True, 'quiz_id': quiz.id, 'message': 'Quiz created successfully'}), 201


@qb_bp.route("/api/create-quiz", methods=["POST"])
@login_required
def create_quiz_api():
    """API: create quiz from a list of question IDs."""
    try:
        data = request.get_json()
        if not data.get('title'):
            return jsonify({"ok": False, "error": "Quiz title is required"}), 400
        question_ids = data.get('question_ids') or []
        if not question_ids:
            return jsonify({"ok": False, "error": "At least one question must be selected"}), 400
        existing = QBank.query.filter(QBank.id.in_(question_ids)).count()
        if existing != len(question_ids):
            return jsonify({"ok": False, "error": "One or more selected questions do not exist"}), 400
        str_ids = [str(qid) for qid in question_ids]
        quiz = Quiz(
            title=data['title'], description=data.get('description', ''),
            topic=data.get('topic', ''), subtopic=data.get('subtopic', ''),
            question_ids=','.join(str_ids),
            question_count=len(str_ids),
            questions_json=build_questions_json(str_ids)
        )
        db.session.add(quiz)
        db.session.commit()
        quiz.quiz_code = quiz_code(quiz.id)
        db.session.commit()
        logger.info(f"Quiz created: ID={quiz.id}, quiz_code={quiz.quiz_code}, title={quiz.title}")
        return jsonify({"ok": True, "quiz_id": quiz.id,
                        "message": f"Quiz created with {len(str_ids)} question(s)"})
    except Exception as e:
        db.session.rollback()
        logger.exception(e)
        return jsonify({"ok": False, "error": str(e)}), 500


# ==================== LIST ==================== #

@qb_bp.route("/list", methods=["GET"])
@login_required
def quiz_list_page():
    return render_template("quiz_list.html")


@qb_bp.route("/api/quizzes-page", methods=["GET"])
@login_required
def get_quizzes_page():
    try:
        page = request.args.get('page', 1, type=int)
        topic = request.args.get('topic', '', type=str).strip()
        status = request.args.get('status', '', type=str).strip()
        title = request.args.get('title', '', type=str).strip()
        unused = request.args.get('unused', '0') == '1'
        per_page = 50

        query = Quiz.query
        if topic:   query = query.filter_by(topic=topic)
        if status:  query = query.filter_by(status=status)
        if title:   query = query.filter(Quiz.title.ilike(f"%{title}%"))
        if unused:
            used_codes = set()
            for row in AUnit.query.with_entities(AUnit.au_content).all():
                if row.au_content:
                    for code in row.au_content.split('|'):
                        code = code.strip()
                        if code:
                            used_codes.add(code)
            query = query.filter(
                db.or_(Quiz.quiz_code == None, ~Quiz.quiz_code.in_(used_codes))
            )

        total = query.count()
        paginated = query.paginate(page=page, per_page=per_page, error_out=False)
        items = [{
            'id': q.id, 'quiz_code': q.quiz_code or '', 'title': q.title, 'description': q.description,
            'topic': q.topic, 'subtopic': q.subtopic,
            'question_count': q.question_count, 'status': q.status or 'draft',
            'question_ids': q.question_ids or ''
        } for q in paginated.items]

        return jsonify({
            'ok': True, 'items': items, 'total': total, 'page': page,
            'pages': paginated.pages, 'has_prev': paginated.has_prev, 'has_next': paginated.has_next
        })
    except Exception as e:
        logger.exception(e)
        return jsonify({'ok': False, 'error': str(e)}), 500


# ==================== UPDATE / DELETE ==================== #

@qb_bp.route("/api/update-quizzes", methods=["POST"])
@login_required
def update_quizzes():
    """Bulk-update quizzes and propagate topic/subtopic/level to their questions."""
    try:
        data = request.get_json()
        quiz_ids = data.get('quiz_ids', [])
        topic, subtopic, level = data.get('topic'), data.get('subtopic'), data.get('level')
        if not quiz_ids:
            return jsonify({'ok': False, 'error': 'No quizzes selected'}), 400

        updated_count = 0
        for quiz_id in quiz_ids:
            quiz = Quiz.query.get(quiz_id)
            if not quiz:
                continue
            if topic is not None:    quiz.topic = topic
            if subtopic is not None: quiz.subtopic = subtopic
            if quiz.question_ids:
                ids = [i.strip() for i in quiz.question_ids.split(',') if i.strip()]
                for q_id in [int(i) for i in ids]:
                    q = QBank.query.get(q_id)
                    if q:
                        if topic is not None:    q.topic = topic
                        if subtopic is not None: q.subtopic = subtopic
                        if level:                q.level = level
                # Rebuild cached HTML since question metadata may have changed
                quiz.questions_json = build_questions_json(ids)
            updated_count += 1

        db.session.commit()
        return jsonify({'ok': True, 'message': f'Updated {updated_count} quiz(zes)', 'updated_count': updated_count})
    except Exception as e:
        db.session.rollback()
        logger.exception(e)
        return jsonify({'ok': False, 'error': str(e)}), 500


@qb_bp.route("/api/delete-quizzes", methods=["POST"])
@login_required
def delete_quizzes():
    try:
        data = request.get_json()
        quiz_ids = data.get('quiz_ids', [])
        confirm_expire = data.get('confirm_expire', False)
        if not quiz_ids:
            return jsonify({'ok': False, 'error': 'No quizzes selected'}), 400

        quizzes = Quiz.query.filter(Quiz.id.in_(quiz_ids)).all()

        # Build per-quiz status report
        results = []
        any_blocked = False
        for q in quizzes:
            mwl_rows    = MyWorkList.query.filter_by(item_code=q.quiz_code).all()
            blocking    = [r for r in mwl_rows if r.status in ('assigned', 'future')]
            auto_expire = [r for r in mwl_rows if r.status == 'done']
            if blocking:
                any_blocked = True
            results.append({
                'quiz_id':     q.id,
                'quiz_code':   q.quiz_code,
                'title':       q.title,
                'blocking':    [{'user': r.user, 'status': r.status} for r in blocking],
                'auto_expire': [{'user': r.user, 'score': r.score or '\u2014'} for r in auto_expire],
            })

        # Dry-run: return the report without touching the database
        if not confirm_expire:
            return jsonify({'ok': True, 'dry_run': True,
                            'results': results, 'any_blocked': any_blocked})

        # Execute — refuse if anything is still blocking
        if any_blocked:
            return jsonify({'ok': False,
                            'error': 'Some quizzes have active/future assignments.',
                            'results': results}), 400

        # Auto-expire done rows, then hard-delete the quiz (cascade handles quiz_execution)
        deleted_count = 0
        for q in quizzes:
            MyWorkList.query.filter_by(item_code=q.quiz_code, status='done').update(
                {'status': 'expired'}, synchronize_session=False
            )
            db.session.delete(q)
            deleted_count += 1

        db.session.commit()
        return jsonify({'ok': True, 'deleted_count': deleted_count,
                        'message': f'Deleted {deleted_count} quiz(zes)'})
    except Exception as e:
        db.session.rollback()
        logger.exception(e)
        return jsonify({'ok': False, 'error': str(e)}), 500


# ==================== PREVIEW ==================== #

@qb_bp.route("/play/<int:question_id>", methods=["GET"])
@login_required
def play_question(question_id):
    q = QBank.query.get(question_id)
    if not q:
        return "Question not found", 404
    return render_template("quiz_play.html", question=q.json)


@qb_bp.route("/<int:quiz_id>/preview", methods=["GET"])
@login_required
def preview_quiz(quiz_id):
    quiz = Quiz.query.get(quiz_id)
    if not quiz:
        return "Quiz not found", 404
    question_ids = [int(qid.strip()) for qid in quiz.question_ids.split(',') if qid.strip()] if quiz.question_ids else []
    questions = []
    for qid in question_ids:
        q = QBank.query.get(qid)
        if q:
            handler = get_handler(q.type.lower() if q.type else 'mcq')
            prepared = handler.prepare_html(q.json) if handler else q.json
            prepared['id'] = q.id
            questions.append(prepared)
    return render_template("quiz_preview.html", quiz=quiz, questions=questions)


@qb_bp.route("/<int:quiz_id>/questions", methods=["GET"])
@login_required
def get_quiz_questions(quiz_id):
    quiz = Quiz.query.get(quiz_id)
    if not quiz:
        return jsonify({'ok': False, 'error': 'Quiz not found'}), 404
    question_ids = [int(qid.strip()) for qid in quiz.question_ids.split(',') if qid.strip()] if quiz.question_ids else []
    questions = [{'id': q.id, 'json': q.json} for qid in question_ids if (q := QBank.query.get(qid))]
    return jsonify({
        'ok': True,
        'quiz': {'id': quiz.id, 'title': quiz.title, 'description': quiz.description,
                 'topic': quiz.topic, 'subtopic': quiz.subtopic, 'question_count': quiz.question_count},
        'questions': questions
    })


# ==================== WIZARD ==================== #

@qb_bp.route("/<int:quiz_id>/builder", methods=["GET"])
@login_required
def quiz_wizard_builder(quiz_id):
    quiz = Quiz.query.get(quiz_id)
    if not quiz:
        return "Quiz not found", 404
    return render_template("quiz_builder.html", quiz_id=quiz_id, wizard_mode=True, quiz_title=quiz.title)


@qb_bp.route("/<int:quiz_id>/append-question", methods=["POST"])
@login_required
def append_question_to_quiz(quiz_id):
    data = request.get_json()
    question_type = data.get('type', '').lower()
    handler = get_handler(question_type)
    if not handler:
        return jsonify({'ok': False, 'error': f'Unknown question type: {question_type}'}), 400
    question_obj, error = handler.save_question(data)
    if error:
        return jsonify({'ok': False, 'error': error}), 400
    quiz = Quiz.query.get(quiz_id)
    if not quiz:
        return jsonify({'ok': False, 'error': 'Quiz not found'}), 404
    existing_ids = [qid.strip() for qid in quiz.question_ids.split(',') if qid.strip()] if quiz.question_ids else []
    existing_ids.append(str(question_obj.id))
    quiz.question_ids = ','.join(existing_ids)
    quiz.question_count = len(existing_ids)
    quiz.updated_at = db.func.now()
    db.session.commit()
    return jsonify({'ok': True, 'question_id': question_obj.id, 'quiz_id': quiz_id,
                    'question_count': quiz.question_count,
                    'message': f'Question {question_obj.id} added to quiz'}), 201
