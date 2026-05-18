"""Quiz execution routes — render, submit answers, results."""

import json as json_lib
import logging

from flask import render_template, request, jsonify
from flask_login import login_required, current_user

from db import db
from models import Quiz, QBank, QuizExecution, UserTable, MyWorkList, UserStreak
from qb.db_utils import quiz_code
from qb.routes import qb_bp

logger = logging.getLogger(__name__)


@qb_bp.route("/execute", methods=["GET"])
@login_required
def execute_quiz():
    """Render the quiz execution page.

    Query params:
        user  — user_id of the student
        quiz  — quiz_id to execute
    """
    user_id = request.args.get('user', type=int)
    quiz_id = request.args.get('quiz', type=int)

    if not user_id or not quiz_id:
        return "Missing required parameters: user and quiz", 400

    quiz = Quiz.query.get(quiz_id)
    if not quiz:
        return "Quiz not found", 404

    questions = quiz.questions_json
    if not questions:
        return "Quiz has no questions", 404

    # Resume support — find the first unanswered question
    answered_ids = {
        ex.question_id
        for ex in QuizExecution.query.filter_by(user_id=user_id, quiz_id=quiz_id).all()
    }
    already_complete = len(questions) > 0 and answered_ids.issuperset(q['id'] for q in questions)
    starting_index = 0
    if not already_complete:
        for idx, q in enumerate(questions):
            if q['id'] not in answered_ids:
                starting_index = idx
                break
        else:
            starting_index = max(len(questions) - 1, 0)

    logger.info(
        "[EXECUTE_QUIZ] user=%s quiz=%s questions=%d starting=%d already_complete=%s",
        user_id, quiz_id, len(questions), starting_index, already_complete,
    )

    # Increment view counter when a student opens the quiz (reliable server-side
    # alternative to sendBeacon which is dropped on same-tab navigation).
    if current_user.user_role in ('student_new', 'new'):
        q_code = quiz_code(quiz_id)
        mwl = MyWorkList.query.filter_by(
            user=current_user.username, item_code=q_code
        ).first()
        if mwl:
            mwl.views = (mwl.views or 0) + 1
            try:
                db.session.commit()
            except Exception:
                db.session.rollback()

    streak_row    = UserStreak.query.get(user_id)
    initial_streak = streak_row.streak if streak_row else 0

    return render_template(
        "quiz_execution.html",
        quiz=quiz,
        questions=questions,
        user_id=user_id,
        quiz_id=quiz_id,
        starting_index=starting_index,
        answered_question_ids=list(answered_ids),
        already_complete=already_complete,
        initial_streak=initial_streak,
    )


@qb_bp.route("/admin-return", methods=["GET"])
@login_required
def admin_return():
    return render_template("quiz-admin-return.html")


@qb_bp.route("/api/check-expr-equiv", methods=["POST"])
@login_required
def check_expr_equiv():
    """Check algebraic equivalence of two expressions using sympy.

    Evaluation chain (short-circuit, fastest first):
        1. Identical after parsing              → True  (instant)
        2. expand(diff) == 0                    → True  (microseconds, handles school algebra)
        3. cancel(diff) == 0                    → True  (rational expressions)
        4. trigsimp(diff) == 0                  → True  (trig identities)
        5. simplify(diff) == 0 (3 s timeout)    → True/False or timeout→False
    """
    import threading
    from sympy.parsing.sympy_parser import (
        parse_expr, standard_transformations,
        implicit_multiplication_application, convert_xor,
    )
    from sympy import expand, cancel, trigsimp, simplify, Symbol, S
    from sympy.core.sympify import SympifyError

    data        = request.get_json(force=True, silent=True) or {}
    user_str    = (data.get('user_expr')    or '').strip()
    correct_str = (data.get('correct_expr') or '').strip()
    variables   = data.get('variables') or []
    logger.info("check_expr_equiv request: user=%r  correct=%r  vars=%r", user_str, correct_str, variables)

    if not user_str or not correct_str:
        return jsonify({'equivalent': False, 'error': 'empty input'})

    try:
        TRANSFORMS = standard_transformations + (
            implicit_multiplication_application,
            convert_xor,
        )
        local_dict = {name: Symbol(name) for name in variables}

        # ── Equation mode ────────────────────────────────────────────────────
        # Both strings contain '=': treat as equations A=B.
        # Two equations are equivalent when (A-B) = ±(C-D), i.e. they express
        # the same constraint up to flipping sides / rearranging terms.
        # e.g.  2x+8=3x-2  ≡  3x-2=8+2x  ≡  x=10
        if '=' in user_str and '=' in correct_str:
            def _parse_eq(s):
                lhs, rhs = s.split('=', 1)
                return (parse_expr(lhs.strip(), local_dict=local_dict, transformations=TRANSFORMS),
                        parse_expr(rhs.strip(), local_dict=local_dict, transformations=TRANSFORMS))
            u_lhs, u_rhs = _parse_eq(user_str)
            c_lhs, c_rhs = _parse_eq(correct_str)
            d_user    = u_lhs - u_rhs
            d_correct = c_lhs - c_rhs
            logger.info("check_expr_equiv equation mode: d_user=%r  d_correct=%r", d_user, d_correct)
            if expand(d_user - d_correct) == S.Zero: return jsonify({'equivalent': True})
            if expand(d_user + d_correct) == S.Zero: return jsonify({'equivalent': True})
            return jsonify({'equivalent': False})

        # One side is an equation, the other is a bare expression — reject
        if '=' in user_str or '=' in correct_str:
            return jsonify({'equivalent': False})

        # ── Expression mode (original behaviour) ─────────────────────────────
        e1 = parse_expr(user_str,    local_dict=local_dict, transformations=TRANSFORMS)
        e2 = parse_expr(correct_str, local_dict=local_dict, transformations=TRANSFORMS)
        logger.info("check_expr_equiv: e1=%r  e2=%r", e1, e2)

        diff = e1 - e2
        logger.info("check_expr_equiv: diff=%r  expand(diff)=%r", diff, expand(diff))
        if diff == S.Zero:         return jsonify({'equivalent': True})
        if expand(diff) == S.Zero: return jsonify({'equivalent': True})
        try:
            if cancel(diff) == S.Zero: return jsonify({'equivalent': True})
        except Exception:
            pass
        try:
            if trigsimp(diff) == S.Zero: return jsonify({'equivalent': True})
        except Exception:
            pass

        # Slow path: simplify with thread-based timeout (cross-platform)
        result = [None]

        def _run():
            try:
                result[0] = simplify(diff) == S.Zero
            except Exception:
                result[0] = False

        t = threading.Thread(target=_run, daemon=True)
        t.start()
        t.join(timeout=3)
        if t.is_alive():
            logger.warning("check_expr_equiv: simplify timed out for %r", user_str)
            return jsonify({'equivalent': False, 'timeout': True})

        return jsonify({'equivalent': bool(result[0])})

    except (SympifyError, NameError, SyntaxError) as exc:
        logger.info("check_expr_equiv: parse error for user=%r correct=%r — %s", user_str, correct_str, exc)
        return jsonify({'equivalent': False, 'error': str(exc)})
    except Exception:
        logger.exception("check_expr_equiv unexpected error")
        return jsonify({'equivalent': False})


@qb_bp.route("/api/complete-quiz", methods=["POST"])
@login_required
def complete_quiz():
    """Mark a MyWorkList quiz item as done and record score/incorrect."""
    try:
        data    = request.get_json()
        user_id = data.get('user_id')
        quiz_id = data.get('quiz_id')
        if not user_id or not quiz_id:
            return jsonify({'ok': False, 'error': 'Missing user_id or quiz_id'}), 400

        # Read all execution rows for this quiz attempt
        rows = (QuizExecution.query
                .filter_by(user_id=user_id, quiz_id=quiz_id)
                .order_by(QuizExecution.question_sequence)
                .all())
        total   = len(rows)
        correct = sum(1 for r in rows if r.is_correct)
        wrong_seqs = [r.question_sequence + 1 for r in rows if not r.is_correct]

        score_str     = f"{correct} of {total}"
        incorrect_str = "All Correct" if not wrong_seqs else "Q: " + ", ".join(str(n) for n in wrong_seqs)

        # Update MyWorkList row (look up by user_id + item_code directly)
        item_code = quiz_code(quiz_id)
        mwl = (MyWorkList.query
               .filter_by(user_id=user_id, item_code=item_code)
               .first())
        if mwl:
            mwl.status    = 'done'
            mwl.score     = score_str
            mwl.incorrect = incorrect_str
            db.session.commit()
        else:
            logger.warning("[COMPLETE_QUIZ] MyWorkList row not found for user_id=%s item_code=%s", user_id, item_code)
            db.session.commit()

        return jsonify({'ok': True, 'correct': correct, 'total': total})
    except Exception as e:
        db.session.rollback()
        logger.exception(e)
        return jsonify({'ok': False, 'error': str(e)}), 500


@qb_bp.route("/api/reset-execution", methods=["POST"])
@login_required
def reset_execution():
    """Delete all quiz_execution rows for a user+quiz so it can be retaken."""
    try:
        data = request.get_json()
        user_id = data.get('user_id')
        quiz_id = data.get('quiz_id')
        if not user_id or not quiz_id:
            return jsonify({'ok': False, 'error': 'Missing user_id or quiz_id'}), 400
        QuizExecution.query.filter_by(user_id=user_id, quiz_id=quiz_id).delete()
        # Also reset MyWorkList so the quiz appears as re-assignable
        item_code = quiz_code(quiz_id)
        mwl = (MyWorkList.query
               .filter_by(user_id=user_id, item_code=item_code)
               .first())
        if mwl:
            mwl.status             = 'assigned'
            mwl.score              = None
            mwl.incorrect          = None
            mwl.questions_answered = 0
        db.session.commit()
        return jsonify({'ok': True})
    except Exception as e:
        db.session.rollback()
        logger.exception(e)
        return jsonify({'ok': False, 'error': str(e)}), 500


@qb_bp.route("/api/submit-answer", methods=["POST"])
@login_required
def submit_answer():
    """Record a student's answer for one question (upsert)."""
    try:
        data = request.get_json()
        user_id        = data.get('user_id')
        quiz_id        = data.get('quiz_id')
        question_id    = data.get('question_id')
        question_seq   = data.get('question_sequence')
        user_answer    = data.get('user_answer')
        correct_answer = data.get('correct_answer')
        is_correct     = data.get('is_correct', False)

        if not all([user_id is not None, quiz_id is not None, question_id is not None, question_seq is not None]):
            return jsonify({'ok': False, 'error': 'Missing required fields'}), 400

        is_new = False
        ex = QuizExecution.query.get((user_id, quiz_id, question_id))
        if ex:
            ex.user_answer    = user_answer
            ex.correct_answer = correct_answer
            ex.is_correct     = is_correct
        else:
            is_new = True
            ex = QuizExecution(
                user_id=user_id,
                quiz_id=quiz_id,
                question_id=question_id,
                question_sequence=question_seq,
                user_answer=user_answer,
                correct_answer=correct_answer,
                is_correct=is_correct,
            )
            db.session.add(ex)

        # Increment questions_answered on first submission only
        if is_new:
            item_code = quiz_code(quiz_id)
            (db.session.query(MyWorkList)
             .filter_by(user_id=user_id, item_code=item_code)
             .update({'questions_answered': MyWorkList.questions_answered + 1},
                     synchronize_session=False))

            # Update correct streak
            streak_row = UserStreak.query.get(user_id)
            if streak_row:
                new_streak = streak_row.streak + 1 if is_correct else 0
                streak_row.streak = new_streak
            else:
                new_streak = 1 if is_correct else 0
                db.session.add(UserStreak(user_id=user_id, streak=new_streak))
        else:
            streak_row = UserStreak.query.get(user_id)
            new_streak = streak_row.streak if streak_row else 0

        db.session.commit()
        return jsonify({'ok': True, 'streak': new_streak}), 201

    except Exception as e:
        db.session.rollback()
        logger.exception(e)
        return jsonify({'ok': False, 'error': str(e)}), 500


@qb_bp.route("/admin/student-history", methods=["GET"])
@login_required
def admin_student_history():
    """Admin page: select a student and see their completed quizzes."""
    if current_user.user_role not in ('admin', 'admin_new'):
        return "Forbidden", 403

    username = request.args.get('username', '').strip()
    students = (UserTable.query
                .filter(UserTable.user_role.in_(['student', 'student_new']))
                .filter(UserTable.is_active == True)
                .order_by(UserTable.full_name)
                .all())

    history = []
    selected_user_id = None
    if username:
        user_obj = UserTable.query.filter_by(username=username).first()
        selected_user_id = user_obj.id if user_obj else None
        rows = (MyWorkList.query
                .filter_by(user=username, status='done')
                .filter(MyWorkList.item_code.like('Q-%'))
                .order_by(MyWorkList.last_updated.desc())
                .all())
        quiz_codes = [r.item_code for r in rows]
        quiz_map = {}
        if quiz_codes:
            for q in Quiz.query.filter(Quiz.quiz_code.in_(quiz_codes)).all():
                quiz_map[q.quiz_code] = {'id': q.id, 'title': q.title}
        for row in rows:
            qinfo = quiz_map.get(row.item_code, {})
            history.append({
                'quiz_id':      qinfo.get('id'),
                'quiz_code':    row.item_code,
                'title':        qinfo.get('title', row.item_code),
                'score':        row.score or '—',
                'incorrect':    row.incorrect or '—',
                'completed_at': row.last_updated,
                'user_id':      selected_user_id,
            })

    return render_template('student_quiz_history.html',
                           students=students,
                           selected_username=username,
                           selected_user_id=selected_user_id,
                           history=history)


@qb_bp.route("/admin/quiz-review", methods=["GET"])
@login_required
def admin_quiz_review():
    """Admin page: show incorrect answers for a specific student + quiz."""
    if current_user.user_role not in ('admin', 'admin_new'):
        return "Forbidden", 403

    user_id = request.args.get('user_id', type=int)
    quiz_id = request.args.get('quiz_id', type=int)
    if not user_id or not quiz_id:
        return "Missing user_id or quiz_id", 400

    rows = (db.session.query(QuizExecution, QBank)
            .join(QBank, QBank.id == QuizExecution.question_id)
            .filter(QuizExecution.user_id == user_id,
                    QuizExecution.quiz_id == quiz_id,
                    QuizExecution.is_correct == False)
            .order_by(QuizExecution.question_sequence)
            .all())

    quiz     = Quiz.query.get(quiz_id)
    user_obj = UserTable.query.get(user_id)
    item_code = quiz_code(quiz_id)
    mwl = MyWorkList.query.filter_by(user_id=user_id, item_code=item_code).first()

    total_rows = QuizExecution.query.filter_by(user_id=user_id, quiz_id=quiz_id).count()

    questions = []
    for ex, qbank in rows:
        questions.append({
            'sequence':       ex.question_sequence + 1,
            'question':       qbank.json,
            'qtype':          (qbank.type or 'mcq').lower(),
            'correct_answer': ex.correct_answer or '—',
            'user_answer':    ex.user_answer or '—',
        })

    from qb.questions import generate_review_html
    html = generate_review_html(
        student_name = user_obj.full_name or user_obj.username if user_obj else 'Unknown',
        quiz_title   = quiz.title if quiz else item_code,
        score        = mwl.score if mwl else '—',
        completed_at = mwl.last_updated if mwl else None,
        total        = total_rows,
        questions    = questions,
    )
    from flask import Response
    return Response(html, mimetype='text/html')
