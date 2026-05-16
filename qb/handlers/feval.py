"""Fill in the Blank with Custom Evaluation (FEVAL) question handler."""

import ast
import re
from jsonschema import ValidationError, validate
from qb.latex_utils import compile_latex_to_pdf
from qb.handlers.common import latex_to_html, generate_question_html
from qb.db_utils import save_question_to_db
from db import db
import logging

logger = logging.getLogger(__name__)


class FEVALHandler:
    """Static methods for handling FEVAL (Fill with Evaluation) question operations."""

    @staticmethod
    def validate_rule_syntax(expression):
        """
        Validate Python expression syntax.
        Returns (valid, error_message)
        """
        try:
            ast.parse(expression, mode='eval')
            return True, None
        except SyntaxError as e:
            return False, str(e)

    @staticmethod
    def validate_variables_exist(expression, declared_variables):
        """
        Check that all variables used in expression are declared.
        Returns (valid, error_message)
        """
        try:
            tree = ast.parse(expression, mode='eval')
            used_vars = set()
            
            # Extract all Name nodes (variable references)
            for node in ast.walk(tree):
                if isinstance(node, ast.Name):
                    used_vars.add(node.id)
            
            # Check for safe builtins that don't need to be declared
            safe_builtins = {
                'abs', 'round', 'max', 'min', 'len', 'sum', 'isinstance',
                'True', 'False', 'None', 'int', 'float', 'str', 'list', 'dict'
            }
            
            undeclared = used_vars - safe_builtins - set(declared_variables)
            
            if undeclared:
                return False, f"Undefined variables: {', '.join(sorted(undeclared))}"
            
            return True, None
        except Exception as e:
            return False, str(e)

    @staticmethod
    def validate_feedback_template(template, declared_variables):
        """
        Validate that feedback template {expressions} are valid.
        Returns (valid, error_message)
        """
        try:
            # Find all {expression} patterns
            pattern = r'\{([^}]+)\}'
            expressions = re.findall(pattern, template)
            
            for expr in expressions:
                # Check syntax
                valid, error = FEVALHandler.validate_rule_syntax(expr)
                if not valid:
                    return False, f"Invalid template expression: {expr} - {error}"
                
                # Check variables
                valid, error = FEVALHandler.validate_variables_exist(expr, declared_variables)
                if not valid:
                    return False, f"Invalid template expression: {expr} - {error}"
            
            return True, None
        except Exception as e:
            return False, str(e)

    @staticmethod
    def test_rule_execution(expression, declared_variables, timeout_seconds=2):
        """
        Test that rule executes safely and returns boolean.
        Returns (valid, error_message)
        """
        try:
            # Prepare safe namespace
            safe_namespace = {var: 0 for var in declared_variables}
            safe_namespace.update({
                'abs': abs,
                'round': round,
                'max': max,
                'min': min,
                'len': len,
                'sum': sum,
                'isinstance': isinstance,
                'int': int,
                'float': float,
                'str': str,
            })
            
            # Use compile with timeout (simulated via simple execution)
            compiled = compile(expression, '<string>', 'eval')
            result = eval(compiled, {"__builtins__": {}}, safe_namespace)
            
            # Verify result is boolean-like
            if not isinstance(result, (bool, int, float)):
                return False, f"Rule must return a boolean value, got {type(result).__name__}"
            
            return True, None
        except TimeoutError:
            return False, "Rule execution timeout (infinite loop?)"
        except Exception as e:
            return False, str(e)

    @staticmethod
    def validate_rules(rules, blanks):
        """
        Comprehensive validation of all rules.
        Returns (valid, error_list)
        """
        if not rules:
            return False, ["At least one rule is required"]
        
        # Extract declared variable names
        declared_variables = [blank.get('variable_name') for blank in blanks if blank.get('variable_name')]
        
        errors = []
        
        for i, rule in enumerate(rules):
            expression = rule.get('expression', '').strip()
            feedback = rule.get('feedback', '').strip()
            
            if not expression:
                errors.append(f"Rule {i+1}: Expression is required")
                continue
            
            # Syntax check
            valid, error = FEVALHandler.validate_rule_syntax(expression)
            if not valid:
                errors.append(f"Rule {i+1} syntax error: {error}")
                continue
            
            # Variable existence check
            valid, error = FEVALHandler.validate_variables_exist(expression, declared_variables)
            if not valid:
                errors.append(f"Rule {i+1}: {error}")
                continue
            
            # Timeout test
            valid, error = FEVALHandler.test_rule_execution(expression, declared_variables)
            if not valid:
                errors.append(f"Rule {i+1} execution error: {error}")
                continue
            
            # Feedback template validation (if provided)
            if feedback:
                valid, error = FEVALHandler.validate_feedback_template(feedback, declared_variables)
                if not valid:
                    errors.append(f"Rule {i+1} feedback: {error}")
        
        return len(errors) == 0, errors

    @staticmethod
    def order_json(question_json):
        """Reorder question JSON to match schema field order."""
        ordered = {}
        field_order = ["id", "type", "stem", "image", "input", "answer", "feedback", "topic", "subtopic", "level"]
        
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
        
        # Feedback - ensure both latex and html exist
        if 'feedback' in question:
            if isinstance(question['feedback'], dict):
                question['feedback'] = dict(question['feedback'])
            else:
                question['feedback'] = {'latex': str(question['feedback']), 'html': ''}
            
            if 'latex' in question['feedback']:
                question['feedback']['html'] = latex_to_html(question['feedback']['latex'])
            elif 'html' not in question['feedback']:
                question['feedback']['html'] = question['feedback'].get('latex', '')
        
        return question

    @staticmethod
    def save_question(data):
        """
        Save FEVAL question to database using safe pattern.
        Returns (question, error) tuple.
        """
        try:
            question_type = data['type']
            topic = data.get('topic', '')
            subtopic = data.get('subtopic', '')
            level = data.get('level', '')
            # Prepare question JSON
            question = FEVALHandler.prepare_html(data['question'])

            # Validate rules before saving
            blanks = question.get('input', {}).get('blanks', [])
            rules = question.get('answer', {}).get('rules', [])

            valid, errors = FEVALHandler.validate_rules(rules, blanks)
            if not valid:
                error_msg = "Rule validation failed: " + "; ".join(errors)
                return None, error_msg

            final_json = FEVALHandler.order_json(question)

            q, error = save_question_to_db(question_type, topic, subtopic, level, final_json, data)

            if error:
                return None, error

            return q, None
            
        except Exception as e:
            db.session.rollback()
            logger.exception("Error saving FEVAL question")
            return None, str(e)

    @staticmethod
    def generate_pdf(question_data, question_id):
        """Generate PDF for FEVAL question using LaTeX compilation."""
        try:
            question = question_data.get('question', {})
            
            stem_latex = question.get('stem', {}).get('latex', '')
            blanks = question.get('input', {}).get('blanks', [])
            rules = question.get('answer', {}).get('rules', [])
            
            # Build LaTeX document
            latex_doc = r"""\documentclass[14pt,a4paper]{article}
\usepackage{mathpazo}
\usepackage{amsmath}
\usepackage{amssymb}
\usepackage{geometry}
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
""" + stem_latex + r"""
}

\vspace{0.2in}

\noindent\textbf{Input Variables:}

\begin{itemize}
"""
            
            # Add blanks
            for blank in blanks:
                var_name = blank.get('variable_name', '')
                label = blank.get('label', '')
                latex_doc += f"\n\t\\item $\\mathbf{{{var_name}}}$: {label}\n"
            
            latex_doc += r"""
\end{itemize}

\vspace{0.15in}

\noindent\textbf{Validation Rules:}

\begin{enumerate}
"""
            
            # Add rules
            for i, rule in enumerate(rules, 1):
                expr = rule.get('expression', '')
                feedback = rule.get('feedback', '')
                latex_doc += f"\n\t\\item Expression: \\texttt{{{expr}}}\n"
                if feedback:
                    latex_doc += f"\t\\ \\ Feedback: {feedback}\n"
            
            latex_doc += r"""
\end{enumerate}

\end{document}
"""
            
            # Compile PDF
            pdf_buffer = compile_latex_to_pdf(latex_doc)
            return pdf_buffer
            
        except Exception as e:
            logger.exception(f"Error generating FEVAL PDF: {e}")
            raise
