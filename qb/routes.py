"""Question Bank (QB) routes - blueprint definitions and shared utilities.

Route handlers are split across sub-modules:
  qb/questions.py   - /question/ endpoints (CRUD, display, print, list)
  qb/quizzes.py     - /quiz/     management (create, list, update, delete, preview)
  qb/execution.py   - /quiz/     execution  (start, execute, submit, results)
  qb/assignments.py - /quiz/     assignment (assign page, users, batch assign)
"""

import logging

from flask import Blueprint, jsonify
from qb.handlers.mcq import MCQHandler
from qb.handlers.mr import MRHandler
from qb.handlers.fill import FILLHandler
from qb.handlers.ohs import OHSHandler
from qb.handlers.feval import FEVALHandler
from qb.handlers.algebra import AlgebraHandler

logger = logging.getLogger(__name__)

# Blueprint declarations
qb_bp = Blueprint("qb", __name__, url_prefix="/quiz")
question_bp = Blueprint("question", __name__, url_prefix="/question")


# Global error handlers
@qb_bp.errorhandler(Exception)
def qb_error_handler(error):
    logger.exception(error)
    response = jsonify({"ok": False, "errors": [str(error)]})
    response.status_code = 500
    return response


@question_bp.errorhandler(Exception)
def question_error_handler(error):
    from db import db
    db.session.rollback()
    logger.exception(error)
    response = jsonify({"ok": False, "errors": [str(error)]})
    response.status_code = 500
    return response


# Shared helper
_HANDLERS = {
    "mcq":     MCQHandler,
    "mr":      MRHandler,
    "fill":    FILLHandler,
    "ohs":     OHSHandler,
    "feval":   FEVALHandler,
    "algebra": AlgebraHandler,
}


def get_handler(question_type):
    """Return the handler class for the given question type, or None."""
    return _HANDLERS.get((question_type or "").lower())
