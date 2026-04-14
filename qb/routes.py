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
