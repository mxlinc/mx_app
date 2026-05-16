"""MCQ (Multiple Choice Question) specific handler."""

from qb.validators import validate_question_json, order_question_json
from qb.latex_utils import generate_latex_template, compile_latex_to_pdf
from qb.handlers.common import generate_question_html
from qb.db_utils import save_question_to_db


class MCQHandler:
    """Handler for MCQ question type operations."""
    
    @staticmethod
    def validate(question_json):
        """Validate MCQ question against schema."""
        return validate_question_json(question_json)
    
    @staticmethod
    def order_json(question_json):
        """Reorder MCQ question JSON fields."""
        return order_question_json(question_json)
    
    @staticmethod
    def prepare_html(question):
        """Generate HTML representation of question."""
        return generate_question_html(question)
    
    @staticmethod
    def save_question(data):
        """Save MCQ question to database using safe pattern."""
        try:
            question_type = data['type']
            topic = data['topic']
            subtopic = data['subtopic']
            level = data['level']
            # Prepare question JSON
            question = MCQHandler.prepare_html(data['question'])
            final_json = MCQHandler.order_json(question)

            q, error = save_question_to_db(question_type, topic, subtopic, level, final_json, data)

            if error:
                return None, error
            
            # Validate after save (ID is now in q.json)
            valid, error_msg = MCQHandler.validate(q.json)
            if not valid:
                return None, error_msg
            
            return q, None
            
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.exception("Error saving MCQ question")
            return None, str(e)
    
    @staticmethod
    def generate_pdf(question_data, question_id):
        """Generate PDF for MCQ question."""
        latex_source = generate_latex_template(question_data, question_id)
        pdf_buffer = compile_latex_to_pdf(latex_source)
        return pdf_buffer
