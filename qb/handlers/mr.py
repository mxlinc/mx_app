"""MR (Multiple Response) question handler."""

from jsonschema import ValidationError, validate
from qb.latex_utils import generate_latex_template, compile_latex_to_pdf
from qb.handlers.common import generate_question_html
from qb.db_utils import save_question_to_db


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
        """Save MR question to database using safe pattern."""
        try:
            question_type = data['type']
            topic = data['topic']
            subtopic = data['subtopic']
            level = data['level']
            # Prepare question JSON
            question = MRHandler.prepare_html(data['question'])
            final_json = MRHandler.order_json(question)

            q, error = save_question_to_db(question_type, topic, subtopic, level, final_json, data)

            if error:
                return None, error
            
            # Validate after save (ID is now in q.json)
            valid, error_msg = MRHandler.validate(q.json)
            if not valid:
                return None, error_msg
            
            return q, None
            
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.exception("Error saving MR question")
            return None, str(e)
    
    @staticmethod
    def generate_pdf(question_data, question_id):
        """Generate PDF for MR question."""
        latex_source = generate_latex_template(question_data, question_id)
        pdf_buffer = compile_latex_to_pdf(latex_source)
        return pdf_buffer
