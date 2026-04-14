"""MR (Multiple Response) question handler."""

from jsonschema import ValidationError, validate
from qb.latex_utils import generate_latex_template, compile_latex_to_pdf
from qb.handlers.common import save_image_from_data_url, generate_question_html
from models import QBank
from db import db


class MRHandler:
    """Handler for MR (Multiple Response) question type operations."""
    
    @staticmethod
    def validate(question_json):
        """Validate MR question against MR_SCHEMA."""
        from schemas import MR_SCHEMA
        try:
            validate(instance=question_json, schema=MR_SCHEMA)
            return True, None
        except ValidationError as e:
            error_msg = f"Schema Validation Error: {e.message}"
            if e.path:
                error_msg += f" at '{'.'.join(str(p) for p in e.path)}'"
            return False, error_msg
    
    @staticmethod
    def order_json(question_json):
        """Reorder MR question JSON fields."""
        ordered = {}
        field_order = ["id", "type", "stem", "image", "input", "answer", "topic", "subtopic", "level"]
        
        for field in field_order:
            if field in question_json:
                ordered[field] = question_json[field]
        
        return ordered
    
    @staticmethod
    def prepare_html(question):
        """Generate HTML representation of question."""
        return generate_question_html(question)
    
    @staticmethod
    def save_question(data):
        """Save MR question to database."""
        if data.get('id'):
            # ===== EDITING EXISTING =====
            q = QBank.query.get(data['id'])
            if not q:
                return None, "Question not found"
            q.type = data['type']
            q.topic = data['topic']
            q.subtopic = data['subtopic']
            q.level = data['level']
            question_id = q.id
        else:
            # ===== CREATE NEW: SKELETON FIRST TO GET ID =====
            q = QBank(
                type=data['type'],
                topic=data['topic'],
                subtopic=data['subtopic'],
                level=data['level'],
                json={}
            )
            db.session.add(q)
            db.session.flush()
            question_id = q.id

        # ===== HANDLE IMAGE =====
        image_path = None
        if 'image_data_url' in data and data['image_data_url']:
            filename = f"{question_id}.png"
            image_path = save_image_from_data_url(data['image_data_url'], filename, subdir="qimage")
        elif data.get('id') and q.json and q.json.get('image'):
            image_path = q.json['image']['src']

        # ===== BUILD COMPLETE QUESTION JSON =====
        question = MRHandler.prepare_html(data['question'])
        
        if image_path:
            question['image'] = {"src": image_path, "alt": ""}

        question['id'] = question_id
        final_json = MRHandler.order_json(question)

        # ===== VALIDATE =====
        valid, error_msg = MRHandler.validate(final_json)
        if not valid:
            return None, error_msg

        # ===== SAVE =====
        q.json = final_json
        db.session.commit()
        return q, None
    
    @staticmethod
    def generate_pdf(question_data, question_id):
        """Generate PDF for MR question."""
        latex_source = generate_latex_template(question_data, question_id)
        pdf_buffer = compile_latex_to_pdf(latex_source)
        return pdf_buffer
