"""Regression tests for quiz APIs receiving browser string question IDs."""

import unittest
from pathlib import Path

from flask import Flask
from flask_login import LoginManager

from db import db
from models import QBank, Quiz, UserTable
from qb import qb_bp
from qb.quizzes import normalize_question_ids


class QuizQuestionIdTests(unittest.TestCase):
    def setUp(self):
        self.app = Flask(
            __name__, template_folder=str(Path(__file__).resolve().parents[1] / 'templates'),
        )
        self.app.config.update(
            TESTING=True,
            SECRET_KEY='quiz-question-id-test-only',
            SQLALCHEMY_DATABASE_URI='sqlite://',
            SQLALCHEMY_ENGINE_OPTIONS={
                'execution_options': {'schema_translate_map': {UserTable.__table__.schema: None}},
            },
        )
        db.init_app(self.app)
        login_manager = LoginManager(self.app)
        login_manager.login_view = 'lms.login'
        login_manager.user_loader(lambda user_id: db.session.get(UserTable, int(user_id)))
        self.app.register_blueprint(qb_bp)
        self.context = self.app.app_context()
        self.context.push()
        db.metadata.create_all(
            db.engine, tables=[UserTable.__table__, QBank.__table__, Quiz.__table__],
        )
        self.admin = UserTable(username='admin-test', user_role='admin')
        self.question = QBank(id=101, type='unknown', json={})
        self.quiz = Quiz(title='Existing quiz', question_ids='')
        db.session.add_all([self.admin, self.question, self.quiz])
        db.session.commit()
        self.client = self.app.test_client()
        with self.client.session_transaction() as session:
            session['_user_id'] = str(self.admin.id)
            session['_fresh'] = True

    def tearDown(self):
        db.session.remove()
        db.engine.dispose()
        self.context.pop()

    def test_add_questions_accepts_browser_string_ids(self):
        response = self.client.post('/quiz/api/add-questions', json={
            'quiz_id': self.quiz.id,
            'question_ids': ['101'],
        })

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.get_json()['ok'])
        self.assertEqual(db.session.get(Quiz, self.quiz.id).question_ids, '101')

    def test_normalize_question_ids_returns_integers_for_database_queries(self):
        normalized_ids = normalize_question_ids(['101'])

        self.assertEqual(normalized_ids, [101])
        self.assertIsInstance(normalized_ids[0], int)

    def test_create_quiz_accepts_browser_string_ids(self):
        response = self.client.post('/quiz/api/create-quiz', json={
            'title': 'New quiz',
            'question_ids': ['101'],
        })

        self.assertEqual(response.status_code, 200)
        created_quiz = db.session.get(Quiz, response.get_json()['quiz_id'])
        self.assertEqual(created_quiz.question_ids, '101')

    def test_quiz_apis_reject_malformed_question_ids(self):
        for url, payload in (
            ('/quiz/api/add-questions', {
                'quiz_id': self.quiz.id,
                'question_ids': ['not-a-question-id'],
            }),
            ('/quiz/api/create-quiz', {
                'title': 'Invalid quiz',
                'question_ids': ['not-a-question-id'],
            }),
        ):
            response = self.client.post(url, json=payload)
            self.assertEqual(response.status_code, 400)
            self.assertFalse(response.get_json()['ok'])
            self.assertEqual(response.get_json()['error'], 'Question IDs must be positive integers')


if __name__ == '__main__':
    unittest.main()
