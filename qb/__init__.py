"""Question Bank (QB) package for managing quiz questions."""

from qb.routes import qb_bp, question_bp

# Import sub-modules to register their routes on the blueprints.
# Must come AFTER the blueprint objects are created above.
from qb import questions   # noqa: F401
from qb import quizzes     # noqa: F401
from qb import execution   # noqa: F401
from qb import assignments # noqa: F401

__all__ = ['qb_bp', 'question_bp']
