"""OHS (One HotSpot) question handler."""

from jsonschema import ValidationError, validate
from qb.latex_utils import generate_latex_template, compile_latex_to_pdf
from qb.handlers.common import generate_question_html
from qb.db_utils import save_question_to_db


class OHSHandler:
    """Handler for OHS (One HotSpot) question type operations."""
    
    @staticmethod
    def validate(question_json):
        """Validate OHS question against OHS_SCHEMA."""
        from schemas import OHS_SCHEMA
        try:
            validate(instance=question_json, schema=OHS_SCHEMA)
            return True, None
        except ValidationError as e:
            error_msg = f"Schema Validation Error: {e.message}"
            if e.path:
                error_msg += f" at '{'.'.join(str(p) for p in e.path)}'"
            return False, error_msg
    
    @staticmethod
    def order_json(question_json):
        """Reorder OHS question JSON fields."""
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
        """Save OHS question to database using safe pattern."""
        import logging
        logger = logging.getLogger(__name__)
        
        try:
            question_type = data['type']
            topic = data['topic']
            subtopic = data['subtopic']
            level = data['level']
            # Prepare question JSON
            question = OHSHandler.prepare_html(data['question'])
            final_json = OHSHandler.order_json(question)

            q, error = save_question_to_db(question_type, topic, subtopic, level, final_json, data)

            if error:
                return None, error

            # Validate after save (ID is now in q.json)
            valid, error_msg = OHSHandler.validate(q.json)
            if not valid:
                return None, error_msg
            
            return q, None
            
        except Exception as e:
            logger.exception("Error saving OHS question")
            return None, str(e)
    
    @staticmethod
    def generate_pdf(question_data, question_id):
        """Generate PDF for OHS question."""
        latex_source = generate_latex_template(question_data, question_id)
        pdf_buffer = compile_latex_to_pdf(latex_source)
        return pdf_buffer
