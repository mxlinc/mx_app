"""Question Bank (QB) routes for managing quiz questions."""

from flask import Blueprint, render_template, request, jsonify, send_file, redirect
from flask_login import login_required
import logging
from models import QBank
from db import db
from qb.handlers.mcq import MCQHandler
from qb.handlers.mr import MRHandler
from qb.handlers.fill import FILLHandler
from qb.validators import validate_question_json, order_question_json
from qb.handlers.common import generate_question_html

logger = logging.getLogger(__name__)

qb_bp = Blueprint("qb", __name__, url_prefix="/quiz")


@qb_bp.errorhandler(Exception)
def qb_error_handler(error):
    logger.exception(error)
    response = jsonify({"ok": False, "errors": [str(error)]})
    response.status_code = 500
    return response


# ==================== HANDLER MAPPING ==================== #

def get_handler(question_type):
    """Get the appropriate handler for a question type."""
    handlers = {
        "mcq": MCQHandler,
        "mr": MRHandler,
        "fill": FILLHandler
    }
    return handlers.get(question_type.lower() if question_type else None)


# ==================== BUILDER ==================== #

@qb_bp.route("/builder", methods=["GET"])
@login_required
def builder_page():
    return render_template("quiz_builder.html")


@qb_bp.route("/edit/<int:question_id>", methods=["GET"])
@login_required
def edit_question_redirect(question_id):
    """Redirect to appropriate builder based on question type."""
    q = QBank.query.get(question_id)
    if not q:
        return jsonify({"ok": False, "errors": ["Question not found"]}), 404
    
    question_type = q.type.lower() if q.type else 'mcq'
    return redirect(f"/quiz/builder?id={question_id}&type={question_type}")


@qb_bp.route("/preview", methods=["POST"])
@login_required
def preview_question():
    data = request.get_json()
    question_type = data.get('type', 'mcq').lower()
    handler = get_handler(question_type)
    
    if not handler:
        return jsonify({"ok": False, "errors": [f"Unknown question type: {question_type}"]}), 400
    
    question = handler.prepare_html(data['question'])
    if 'image_data_url' in data and data['image_data_url']:
        question['image'] = question.get('image', {})
        question['image']['src'] = data['image_data_url']
    return jsonify({"ok": True, "question": question, "errors": []})


@qb_bp.route("/save", methods=["POST"])
@login_required
def save_question():
    data = request.get_json()
    question_type = data.get('type', 'mcq').lower()
    data['type'] = question_type  # Normalize type in data
    handler = get_handler(question_type)
    
    if not handler:
        return jsonify({"ok": False, "errors": [f"Unknown question type: {question_type}"]}), 400
    
    q, error = handler.save_question(data)
    if error:
        return jsonify({"ok": False, "errors": [error]}), 400
    
    return jsonify({
        "ok": True,
        "question_id": q.id,
        "message": "Question saved.",
        "question": q.json
    })


# ==================== DISPLAY ==================== #

@qb_bp.route("/display/<int:question_id>", methods=["GET"])
@login_required
def display_question(question_id):
    q = QBank.query.get(question_id)
    if not q:
        return "Question not found", 404
    return render_template("quiz_display.html", question_id=question_id)


@qb_bp.route("/get-display/<int:question_id>", methods=["GET"])
@login_required
def get_display_question(question_id):
    q = QBank.query.get(question_id)
    if not q:
        return jsonify({"ok": False, "errors": ["Question not found"]}), 404
    
    handler = get_handler(q.type.lower() if q.type else 'mcq')
    if not handler:
        return jsonify({"ok": False, "errors": [f"Unknown question type: {q.type}"]}), 400
    
    question = handler.prepare_html(q.json)
    ordered_question = handler.order_json(question)
    return jsonify({
        "ok": True, 
        "question": ordered_question,
        "question_id": q.id,
        "type": q.type.lower() if q.type else 'mcq',
        "topic": q.topic,
        "subtopic": q.subtopic,
        "level": q.level
    })


# ==================== PDF ==================== #

@qb_bp.route("/print/<int:question_id>", methods=["GET"])
@login_required
def print_question(question_id):
    """Generate and download PDF of question."""
    q = QBank.query.get(question_id)
    if not q:
        return jsonify({"ok": False, "errors": ["Question not found"]}), 404
    
    handler = get_handler(q.type.lower() if q.type else 'mcq')
    if not handler:
        return jsonify({"ok": False, "errors": [f"Unknown question type: {q.type}"]}), 400
    
    question = handler.prepare_html(q.json)
    question_data = {
        "question": question,
        "question_id": q.id,
        "type": q.type,
        "topic": q.topic,
        "subtopic": q.subtopic,
        "level": q.level
    }
    
    pdf_buffer = handler.generate_pdf(question_data, question_id)
    
    return send_file(
        pdf_buffer,
        mimetype='application/pdf',
        as_attachment=True,
        download_name=f'question_{question_id}.pdf'
    )


# ==================== RETRIEVE ==================== #

@qb_bp.route("/question/<int:question_id>", methods=["GET"])
@login_required
def get_question(question_id):
    q = QBank.query.get(question_id)
    if not q:
        return jsonify({"ok": False, "errors": ["Question not found"]}), 404
    return jsonify({
        "ok": True,
        "id": q.id,
        "type": q.type,
        "topic": q.topic,
        "subtopic": q.subtopic,
        "level": q.level,
        "question": q.json
    })


@qb_bp.route("/questions", methods=["GET"])
@login_required
def list_questions():
    query = QBank.query
    if request.args.get('type'):
        query = query.filter_by(type=request.args['type'])
    if request.args.get('topic'):
        query = query.filter_by(topic=request.args['topic'])
    if request.args.get('subtopic'):
        query = query.filter_by(subtopic=request.args['subtopic'])
    if request.args.get('level'):
        query = query.filter_by(level=request.args['level'])
    items = []
    for q in query.all():
        items.append({
            "id": q.id,
            "type": q.type,
            "topic": q.topic,
            "subtopic": q.subtopic,
            "level": q.level,
            "stem_latex": q.json['stem']['latex'],
            "image": q.json.get('image')
        })
    return jsonify({"ok": True, "items": items})


# ==================== PLAY/QUIZ ==================== #

@qb_bp.route("/play/<int:question_id>", methods=["GET"])
@login_required
def play_question(question_id):
    q = QBank.query.get(question_id)
    if not q:
        return "Question not found", 404
    return render_template("quiz_play.html", question=q.json)


@qb_bp.route("/play-preview", methods=["POST"])
@login_required
def play_preview():
    data = request.get_json()
    question = MCQHandler.prepare_html(data['question'])
    if 'image_data_url' in data and data['image_data_url']:
        question['image']['src'] = data['image_data_url']
    return render_template("quiz_play.html", question=question)


# ==================== QUIZ MANAGEMENT ==================== #

@qb_bp.route("/create-quiz", methods=["GET"])
@login_required
def create_quiz_page():
    """Display create quiz form."""
    return render_template("create_quiz.html")


@qb_bp.route("/create-quiz", methods=["POST"])
@login_required
def create_quiz():
    """Save a new quiz."""
    from models import Quiz
    
    data = request.get_json()
    
    # Parse question_ids
    question_ids_str = data.get('question_ids', '').strip()
    question_ids = [qid.strip() for qid in question_ids_str.split(',') if qid.strip()] if question_ids_str else []
    
    quiz = Quiz(
        title=data.get('title', ''),
        description=data.get('description', ''),
        topic=data.get('topic', ''),
        subtopic=data.get('subtopic', ''),
        question_ids=','.join(question_ids) if question_ids else '',
        question_count=len(question_ids)
    )
    
    db.session.add(quiz)
    db.session.commit()
    
    return jsonify({
        'ok': True,
        'quiz_id': quiz.id,
        'message': 'Quiz created successfully'
    }), 201


@qb_bp.route("/quiz/<int:quiz_id>/preview", methods=["GET"])
@login_required
def preview_quiz(quiz_id):
    """Display quiz preview with all questions."""
    from models import Quiz
    
    quiz = Quiz.query.get(quiz_id)
    if not quiz:
        return "Quiz not found", 404
    
    # Parse question IDs
    question_ids = [int(qid.strip()) for qid in quiz.question_ids.split(',') if qid.strip()] if quiz.question_ids else []
    
    # Fetch all questions in order
    questions = []
    for qid in question_ids:
        q = QBank.query.get(qid)
        if q:
            questions.append(q.json)
    
    return render_template("quiz_preview.html", quiz=quiz, questions=questions)


@qb_bp.route("/quiz/<int:quiz_id>/questions", methods=["GET"])
@login_required
def get_quiz_questions(quiz_id):
    """Get quiz questions as JSON."""
    from models import Quiz
    
    quiz = Quiz.query.get(quiz_id)
    if not quiz:
        return jsonify({'ok': False, 'error': 'Quiz not found'}), 404
    
    # Parse question IDs
    question_ids = [int(qid.strip()) for qid in quiz.question_ids.split(',') if qid.strip()] if quiz.question_ids else []
    
    # Fetch all questions in order
    questions = []
    for qid in question_ids:
        q = QBank.query.get(qid)
        if q:
            questions.append({'id': q.id, 'json': q.json})
    
    return jsonify({
        'ok': True,
        'quiz': {
            'id': quiz.id,
            'title': quiz.title,
            'description': quiz.description,
            'topic': quiz.topic,
            'subtopic': quiz.subtopic,
            'question_count': quiz.question_count
        },
        'questions': questions
    })


# ==================== WIZARD MODE ==================== #

@qb_bp.route("/quiz/<int:quiz_id>/builder", methods=["GET"])
@login_required
def quiz_wizard_builder(quiz_id):
    """Builder in wizard mode for a specific quiz."""
    from models import Quiz
    
    quiz = Quiz.query.get(quiz_id)
    if not quiz:
        return "Quiz not found", 404
    
    return render_template("quiz_builder.html", quiz_id=quiz_id, wizard_mode=True, quiz_title=quiz.title)


@qb_bp.route("/quiz/<int:quiz_id>/append-question", methods=["POST"])
@login_required
def append_question_to_quiz(quiz_id):
    """Save a question in wizard mode and append to quiz."""
    from models import Quiz
    
    data = request.get_json()
    question_type = data.get('type', '').lower()
    
    handler = get_handler(question_type)
    if not handler:
        return jsonify({'ok': False, 'error': f'Unknown question type: {question_type}'}), 400
    
    # Save the question
    question_obj, error = handler.save_question(data)
    if error:
        return jsonify({'ok': False, 'error': error}), 400
    
    # Get the quiz
    quiz = Quiz.query.get(quiz_id)
    if not quiz:
        return jsonify({'ok': False, 'error': 'Quiz not found'}), 404
    
    # Append question ID to quiz
    existing_ids = [qid.strip() for qid in quiz.question_ids.split(',') if qid.strip()] if quiz.question_ids else []
    existing_ids.append(str(question_obj.id))
    
    quiz.question_ids = ','.join(existing_ids)
    quiz.question_count = len(existing_ids)
    quiz.updated_at = db.func.now()
    
    db.session.commit()
    
    return jsonify({
        'ok': True,
        'question_id': question_obj.id,
        'quiz_id': quiz_id,
        'question_count': quiz.question_count,
        'message': f'Question {question_obj.id} added to quiz'
    }), 201


# ==================== QUIZ PREVIEW & EXECUTION ==================== #

@qb_bp.route("/quiz/<int:quiz_id>/execute", methods=["GET"])
@login_required
def execute_quiz(quiz_id):
    """Display quiz execution with sequential navigation."""
    from models import Quiz
    from flask import current_user
    
    quiz = Quiz.query.get(quiz_id)
    if not quiz:
        return "Quiz not found", 404
    
    # Parse question IDs
    question_ids = [int(qid.strip()) for qid in quiz.question_ids.split(',') if qid.strip()] if quiz.question_ids else []
    
    # Fetch all questions in order and prepare with HTML
    questions = []
    for qid in question_ids:
        q = QBank.query.get(qid)
        if q:
            question_type = q.type.lower() if q.type else 'mcq'
            handler = get_handler(question_type)
            if handler:
                prepared = handler.prepare_html(q.json)
                questions.append(prepared)
            else:
                questions.append(q.json)
    
    return render_template(
        "quiz_execution.html", 
        quiz=quiz, 
        questions=questions,
        user_id=current_user.id
    )


@qb_bp.route("/admin-return", methods=["GET"])
@login_required
def admin_return():
    """Return page after quiz completion."""
    return render_template("quiz-admin-return.html")


@qb_bp.route("/submit-answer", methods=["POST"])
@login_required
def submit_answer():
    """Submit an answer during quiz execution and store result."""
    from models import UserQuiz, Quiz
    from flask import current_user
    import json as json_lib
    
    try:
        data = request.get_json()
        
        quiz_id = data.get('quiz_id')
        question_id = data.get('question_id')
        user_answer = data.get('user_answer')
        is_correct = data.get('is_correct', False)
        feedback = data.get('feedback', '')
        
        # Validate required fields
        if not all([quiz_id, question_id]):
            return jsonify({'ok': False, 'error': 'Missing required fields'}), 400
        
        # Get or create user_quiz record
        user_quiz = UserQuiz.query.filter_by(
            user_id=current_user.id,
            quiz_id=quiz_id
        ).first()
        
        if not user_quiz:
            user_quiz = UserQuiz(
                user_id=current_user.id,
                quiz_id=quiz_id,
                status='in_progress'
            )
            db.session.add(user_quiz)
            db.session.flush()
        
        # Store the answer
        # Store responses as JSON string in user_quiz.responses field
        responses = {}
        if user_quiz.responses:
            try:
                responses = json_lib.loads(user_quiz.responses) if isinstance(user_quiz.responses, str) else user_quiz.responses
            except:
                responses = {}
        
        responses[str(question_id)] = {
            'answer': user_answer,
            'is_correct': is_correct,
            'feedback': feedback
        }
        
        user_quiz.responses = json_lib.dumps(responses)
        
        # Update score if tracking
        if is_correct:
            user_quiz.score = (user_quiz.score or 0) + 1
        
        db.session.commit()
        
        return jsonify({
            'ok': True,
            'message': 'Answer submitted successfully',
            'user_quiz_id': user_quiz.id
        }), 201
        
    except Exception as e:
        logger.exception(e)
        return jsonify({'ok': False, 'error': str(e)}), 500
