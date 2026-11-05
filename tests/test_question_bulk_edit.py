"""Tests for the bulk unused-question editor and the shared builder form partial."""

import unittest
from pathlib import Path

from flask import Blueprint, Flask
from flask_login import LoginManager

from db import db
from models import QBank, Quiz, UserTable
from qb import qb_bp, question_bp
from qb.questions import BULK_EDIT_PAGE_SIZE


class QuestionBulkEditTests(unittest.TestCase):
    def setUp(self):
        self.app = Flask(
            __name__, template_folder=str(Path(__file__).resolve().parents[1] / 'templates'),
        )
        self.app.config.update(
            TESTING=True,
            SECRET_KEY='question-bulk-edit-test-only',
            SQLALCHEMY_DATABASE_URI='sqlite://',
            SQLALCHEMY_ENGINE_OPTIONS={
                'execution_options': {'schema_translate_map': {UserTable.__table__.schema: None}},
            },
        )
        db.init_app(self.app)
        login_manager = LoginManager(self.app)
        login_manager.user_loader(lambda user_id: db.session.get(UserTable, int(user_id)))
        self.app.register_blueprint(qb_bp)
        self.app.register_blueprint(question_bp)
        # Stub for the dashboard link rendered by the bulk-edit page.
        lms_stub = Blueprint('lms', __name__)
        lms_stub.add_url_rule('/admin', 'admin_home_new', lambda: '')
        self.app.register_blueprint(lms_stub)

        self.context = self.app.app_context()
        self.context.push()
        db.metadata.create_all(
            db.engine, tables=[UserTable.__table__, QBank.__table__, Quiz.__table__],
        )
        self.admin = UserTable(username='admin-test', user_role='admin')
        db.session.add(self.admin)
        # 1..30 questions; 5 and 12 are used by a quiz.
        db.session.add_all([QBank(id=i, type='unknown', json={}) for i in range(1, 31)])
        self.quiz = Quiz(title='Uses some', question_ids='5, 12')
        db.session.add(self.quiz)
        db.session.commit()
        self.client = self.app.test_client()
        with self.client.session_transaction() as session:
            session['_user_id'] = str(self.admin.id)
            session['_fresh'] = True

    def tearDown(self):
        db.session.remove()
        db.engine.dispose()
        self.context.pop()

    def test_unused_ids_first_page_is_newest_first_and_excludes_used(self):
        data = self.client.get('/question/api/unused-ids').get_json()

        self.assertTrue(data['ok'])
        self.assertEqual(data['total'], 28)
        self.assertEqual(len(data['ids']), BULK_EDIT_PAGE_SIZE)
        self.assertEqual(data['ids'][0], 30)
        self.assertNotIn(12, data['ids'])
        self.assertTrue(data['has_more'])
        self.assertEqual(data['next_before_id'], data['ids'][-1])

    def test_unused_ids_next_page_uses_cursor(self):
        first = self.client.get('/question/api/unused-ids').get_json()
        second = self.client.get(
            f"/question/api/unused-ids?before_id={first['next_before_id']}").get_json()

        self.assertEqual(second['ids'], [9, 8, 7, 6, 4, 3, 2, 1])
        self.assertFalse(second['has_more'])
        self.assertIsNone(second['next_before_id'])
        self.assertFalse(set(first['ids']) & set(second['ids']))

    def test_cursor_page_is_stable_after_delete(self):
        first = self.client.get('/question/api/unused-ids').get_json()
        resp = self.client.post(f"/question/api/delete/{first['ids'][0]}", json={})
        self.assertTrue(resp.get_json()['ok'])

        second = self.client.get(
            f"/question/api/unused-ids?before_id={first['next_before_id']}").get_json()
        self.assertEqual(second['ids'][0], 9)
        self.assertEqual(second['total'], 27)

    def test_bulk_edit_page_renders_builder_form_without_toolbar_delete(self):
        resp = self.client.get('/question/bulk-edit')
        html = resp.get_data(as_text=True)

        self.assertEqual(resp.status_code, 200)
        self.assertIn('id="saveBtn"', html)
        self.assertIn('id="stem_latex"', html)
        self.assertIn('css/question-builder-form.css', html)
        self.assertNotIn('id="deleteBtn"', html)

    def test_quiz_question_editor_still_renders_full_form(self):
        resp = self.client.get(f'/quiz/{self.quiz.id}/question-editor')
        html = resp.get_data(as_text=True)

        self.assertEqual(resp.status_code, 200)
        self.assertIn('id="saveBtn"', html)
        self.assertIn('id="deleteBtn"', html)
        self.assertIn('id="algebra-section"', html)
        self.assertIn('css/question-builder-form.css', html)


if __name__ == '__main__':
    unittest.main()
