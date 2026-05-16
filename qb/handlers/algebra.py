"""Algebra question handler — single expression input with string/sympy equivalence."""

import logging
from qb.handlers.common import latex_to_html
from qb.db_utils import save_question_to_db
from db import db

logger = logging.getLogger(__name__)


class AlgebraHandler:
    """Handler for Algebra question type.

    Answer JSON structure:
        {
          "accepted":  ["x+4", "4+x"],   # fast-path list, spaces already stripped
          "canonical": "x+4",            # used by sympy as the reference expression
          "variables": ["x"],            # declared symbols — sympy security gate
          "use_sympy": true              # enable sympy fallback when string match fails
        }
    """

    @staticmethod
    def prepare_html(question):
        """Generate HTML versions from LaTeX for stem and feedback."""
        if isinstance(question, dict):
            question = dict(question)

        if 'stem' in question:
            if isinstance(question['stem'], dict):
                question['stem'] = dict(question['stem'])
            else:
                question['stem'] = {'latex': str(question['stem']), 'html': ''}
            if 'latex' in question['stem']:
                question['stem']['html'] = latex_to_html(question['stem']['latex'])
            elif 'html' not in question['stem']:
                question['stem']['html'] = question['stem'].get('latex', '')

        if 'feedback' in question:
            if isinstance(question['feedback'], dict):
                question['feedback'] = dict(question['feedback'])
            else:
                question['feedback'] = {'latex': str(question['feedback']), 'html': ''}
            if 'latex' in question['feedback']:
                question['feedback']['html'] = latex_to_html(question['feedback']['latex'])
            elif 'html' not in question['feedback']:
                question['feedback']['html'] = question['feedback'].get('latex', '')

        for field in ('input_label', 'label_after'):
            if field in question:
                node = question[field]
                if not isinstance(node, dict):
                    node = {'latex': str(node), 'html': ''}
                else:
                    node = dict(node)
                if 'latex' in node:
                    node['html'] = latex_to_html(node['latex'])
                elif 'html' not in node:
                    node['html'] = node.get('latex', '')
                question[field] = node

        return question

    @staticmethod
    def order_json(question_json):
        """Reorder question JSON fields."""
        ordered = {}
        for field in ["id", "type", "stem", "input_label", "label_after", "image", "answer", "feedback", "topic", "subtopic", "level"]:
            if field in question_json:
                ordered[field] = question_json[field]
        return ordered

    @staticmethod
    def validate(question):
        """Validate algebra question. Returns (valid, error_list)."""
        errors = []
        answer = question.get('answer', {})

        if not answer.get('accepted'):
            errors.append("At least one accepted answer string is required")
        if not (answer.get('canonical') or '').strip():
            errors.append("Canonical form is required")
        if not answer.get('variables'):
            errors.append("At least one variable must be declared")

        return len(errors) == 0, errors

    @staticmethod
    def save_question(data):
        """Save algebra question to database. Returns (question, error) tuple."""
        try:
            question_type = data['type']
            topic    = data.get('topic', '')
            subtopic = data.get('subtopic', '')
            level    = data.get('level', '')

            question = AlgebraHandler.prepare_html(data['question'])

            valid, errors = AlgebraHandler.validate(question)
            if not valid:
                return None, "Validation failed: " + "; ".join(errors)

            final_json = AlgebraHandler.order_json(question)
            q, error = save_question_to_db(question_type, topic, subtopic, level, final_json, data)
            if error:
                return None, error
            return q, None

        except Exception as e:
            db.session.rollback()
            logger.exception("Error saving algebra question")
            return None, str(e)
