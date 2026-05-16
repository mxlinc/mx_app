"""Fill in the Blank question handler."""

from jsonschema import ValidationError, validate
from qb.validators import validate_question_json, order_question_json
from qb.latex_utils import generate_latex_template, compile_latex_to_pdf
from qb.handlers.common import latex_to_html, generate_question_html
from qb.db_utils import save_question_to_db
from db import db
import logging

logger = logging.getLogger(__name__)


class FILLHandler:
    """Static methods for handling FILL (Fill in the Blank) question operations."""

    @staticmethod
    def validate(question_json):
        """Validate question against FILL_SCHEMA."""
        from schemas import FILL_SCHEMA
        try:
            validate(instance=question_json, schema=FILL_SCHEMA)
            return True, None
        except ValidationError as e:
            error_msg = f"Schema Validation Error: {e.message}"
            if e.path:
                error_msg += f" at '{'.'.join(str(p) for p in e.path)}'"
            return False, error_msg

    @staticmethod
    def order_json(question_json):
        """Reorder question JSON to match schema field order."""
        ordered = {}
        field_order = ["id", "type", "stem", "image", "input", "answer", "topic", "subtopic", "level"]
        
        for field in field_order:
            if field in question_json:
                ordered[field] = question_json[field]
        
        return ordered

    @staticmethod
    def prepare_html(question):
        """Generate HTML versions from LaTeX for all text fields."""
        # Make a copy to avoid mutating input
        if isinstance(question, dict):
            question = dict(question)
        
        # Stem - ensure both latex and html exist
        if 'stem' in question:
            if isinstance(question['stem'], dict):
                question['stem'] = dict(question['stem'])
            else:
                question['stem'] = {'latex': str(question['stem']), 'html': ''}
            
            # Convert LaTeX to HTML if we have LaTeX
            if 'latex' in question['stem']:
                question['stem']['html'] = latex_to_html(question['stem']['latex'])
            elif 'html' not in question['stem']:
                question['stem']['html'] = question['stem'].get('latex', '')
        
        # Blanks - convert labels to HTML
        if 'input' in question and 'blanks' in question['input']:
            blanks_list = []
            for blank in question['input']['blanks']:
                blank_copy = dict(blank) if isinstance(blank, dict) else blank
                if 'input_label' in blank_copy:
                    if isinstance(blank_copy['input_label'], dict):
                        blank_copy['input_label'] = dict(blank_copy['input_label'])
                    else:
                        blank_copy['input_label'] = {'latex': str(blank_copy['input_label']), 'html': ''}
                    
                    if 'latex' in blank_copy['input_label']:
                        blank_copy['input_label']['html'] = latex_to_html(blank_copy['input_label']['latex'])
                    elif 'html' not in blank_copy['input_label']:
                        blank_copy['input_label']['html'] = blank_copy['input_label'].get('latex', '')
                if 'label_after' in blank_copy:
                    la = blank_copy['label_after']
                    if isinstance(la, dict):
                        la = dict(la)
                    else:
                        la = {'latex': str(la), 'html': ''}
                    if 'latex' in la:
                        la['html'] = latex_to_html(la['latex'])
                    elif 'html' not in la:
                        la['html'] = la.get('latex', '')
                    blank_copy['label_after'] = la
                blanks_list.append(blank_copy)
            question['input']['blanks'] = blanks_list
        
        return question

    @staticmethod
    def save_question(data):
        """
        Save FILL question to database using safe pattern.
        Returns (question, error) tuple.
        """
        try:
            question_type = data['type']
            topic = data['topic']
            subtopic = data['subtopic']
            level = data['level']
            # Prepare question JSON
            question = FILLHandler.prepare_html(data['question'])
            final_json = FILLHandler.order_json(question)

            q, error = save_question_to_db(question_type, topic, subtopic, level, final_json, data)

            if error:
                return None, error

            # Validate after save (ID is now in q.json)
            valid, error_msg = FILLHandler.validate(q.json)
            if not valid:
                return None, error_msg
            
            return q, None
            
        except Exception as e:
            db.session.rollback()
            logger.exception("Error saving FILL question")
            return None, str(e)

    @staticmethod
    def generate_pdf(question_data, question_id):
        """Generate PDF for FILL question using LaTeX compilation."""
        try:
            question = question_data.get('question', {})
            
            stem_latex = question.get('stem', {}).get('latex', '')
            blanks = question.get('input', {}).get('blanks', [])
            
            # Build LaTeX document
            latex_doc = r"""\documentclass[14pt,a4paper]{article}
\usepackage{mathpazo}
\usepackage{amsmath}
\usepackage{amssymb}
\usepackage{geometry}
\usepackage{graphicx}
\usepackage{xcolor}

\geometry{margin=0.5in}
\pagestyle{empty}

\begin{document}

\noindent
\textbf{Question ID:} """ + str(question_id) + r""" \\
\textbf{Topic:} """ + (question_data.get('topic', 'N/A') or 'N/A') + r""" $|$ 
\textbf{Subtopic:} """ + (question_data.get('subtopic', 'N/A') or 'N/A') + r""" $|$ 
\textbf{Level:} """ + (question_data.get('level', 'N/A') or 'N/A') + r"""

\vspace{0.15in}

\noindent\hrulefill

\vspace{0.2in}

\noindent\textbf{\LARGE Question:}

\vspace{0.1in}

{\large
"""
            
            # Add stem
            from qb.latex_utils import preserve_newlines_latex, escape_latex
            latex_doc += r"\noindent " + preserve_newlines_latex(stem_latex) + "\n\n"
            
            # Add image if present
            if question.get('image', {}).get('src'):
                try:
                    import os
                    from flask import current_app
                    image_path = question['image']['src']
                    
                    if image_path.startswith('./'):
                        image_path = image_path[2:]
                    if image_path.startswith('static/'):
                        image_path = image_path[7:]
                    
                    full_path = os.path.join(current_app.static_folder, image_path)
                    full_path = os.path.abspath(full_path)
                    
                    if os.path.exists(full_path):
                        latex_image_path = full_path.replace('\\', '/')
                        latex_doc += r"\begin{center}" + "\n"
                        latex_doc += r"\includegraphics[width=4in,height=3in,keepaspectratio]{" + latex_image_path + "}\n"
                        latex_doc += r"\end{center}" + "\n\n"
                except Exception as e:
                    logger.warning(f"Error adding image to FILL PDF: {e}")
            
            # Add blanks
            for idx, blank in enumerate(blanks):
                label_latex = blank.get('input_label', {}).get('latex', f'Blank {idx + 1}')
                label_after_latex = blank.get('label_after', {}).get('latex', '')
                # Use a), b), c), etc. labeling
                alpha_label = chr(97 + idx)  # 'a', 'b', 'c', etc.

                if label_after_latex:
                    # Inline: label _______ label_after
                    latex_doc += f"{alpha_label}) {label_latex} " + r"\underline{\hspace{4cm}}" + f" {label_after_latex}\n\n"
                else:
                    latex_doc += f"{alpha_label}) {label_latex}\n"
                    latex_doc += r"\vspace{0.15in}\noindent\underline{\hspace{5cm}}" + "\n\n"
            
            latex_doc += r"""}

\end{document}
"""
            
            pdf_buffer = compile_latex_to_pdf(latex_doc)
            return pdf_buffer
        
        except Exception as e:
            logger.exception("Error generating FILL PDF")
            raise
