"""Regression tests for Fine Tune unit-membership repair."""

import unittest
from pathlib import Path

from flask import Flask
from flask_login import LoginManager

from db import db
from lms.routes import lms_bp
from models import AUnit, Interaction, MyWorkList, ParkedUnit, Quiz, UserTable, Video


class FineTuneUnitRepairTests(unittest.TestCase):
    def setUp(self):
        self.app = Flask(
            __name__, template_folder=str(Path(__file__).resolve().parents[1] / 'templates')
        )
        self.app.config.update(
            TESTING=True,
            SECRET_KEY='finetune-repair-test-only',
            SQLALCHEMY_DATABASE_URI='sqlite://',
            SQLALCHEMY_ENGINE_OPTIONS={
                'execution_options': {'schema_translate_map': {AUnit.__table__.schema: None}}
            },
        )
        db.init_app(self.app)
        login_manager = LoginManager(self.app)
        login_manager.login_view = 'lms.login'
        login_manager.user_loader(lambda user_id: db.session.get(UserTable, int(user_id)))
        self.app.register_blueprint(lms_bp)
        self.context = self.app.app_context()
        self.context.push()
        db.metadata.create_all(
            db.engine,
            tables=[
                UserTable.__table__, AUnit.__table__, MyWorkList.__table__,
                ParkedUnit.__table__, Quiz.__table__, Video.__table__, Interaction.__table__,
            ],
        )
        self.admin = UserTable(username='admin-repair', user_role='admin')
        self.student = UserTable(
            username='student-repair', user_role='student_new', can_assign_work=True,
        )
        self.source = AUnit(au_name='Original unit', au_content='Q-OLD')
        self.target = AUnit(au_name='Current unit', au_content='Q-001')
        self.db_add(self.admin, self.student, self.source, self.target)
        self.client = self.app.test_client()
        with self.client.session_transaction() as session:
            session['_user_id'] = str(self.admin.id)
            session['_fresh'] = True

    def tearDown(self):
        db.session.remove()
        db.engine.dispose()
        self.context.pop()

    def db_add(self, *objects):
        db.session.add_all(objects)
        db.session.commit()

    def assignment(self, au_name='Original unit', item_code='Q-001'):
        row = MyWorkList(
            user=self.student.username,
            user_id=self.student.id,
            au_name=au_name,
            item_code=item_code,
            status='done',
            score='8',
            views=4,
            questions_answered=6,
        )
        self.db_add(row)
        return row

    def test_work_response_identifies_items_removed_from_saved_unit(self):
        row = self.assignment()

        response = self.client.get(f'/unit/api/finetune-work?student_id={self.student.id}')

        self.assertEqual(response.status_code, 200)
        repair_items = response.json['repair_items']
        self.assertEqual(len(repair_items), 1)
        self.assertEqual(repair_items[0]['row_id'], row.id)
        self.assertEqual(repair_items[0]['reason'], 'item_not_in_unit')
        self.assertEqual(
            repair_items[0]['candidates'],
            [{'au_id': self.target.au_id, 'au_name': 'Current unit'}],
        )

    def test_work_response_identifies_items_with_a_missing_saved_unit(self):
        row = self.assignment(au_name='Retired unit')

        response = self.client.get(f'/unit/api/finetune-work?student_id={self.student.id}')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json['repair_items'][0]['row_id'], row.id)
        self.assertEqual(response.json['repair_items'][0]['reason'], 'unit_not_found')
        self.assertEqual(
            response.json['repair_items'][0]['candidates'],
            [{'au_id': self.target.au_id, 'au_name': 'Current unit'}],
        )

    def test_repair_relinks_existing_row_and_preserves_progress(self):
        row = self.assignment()

        response = self.client.post('/unit/api/repair-unit-membership', json={
            'student_id': self.student.id,
            'repairs': [{'row_id': row.id, 'target_au_id': self.target.au_id}],
        })

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json['relinked'], [{'row_id': row.id, 'au_name': 'Current unit'}])
        db.session.expire_all()
        repaired = db.session.get(MyWorkList, row.id)
        self.assertEqual(repaired.au_name, 'Current unit')
        self.assertEqual(repaired.status, 'done')
        self.assertEqual(repaired.score, '8')
        self.assertEqual(repaired.views, 4)
        self.assertEqual(repaired.questions_answered, 6)

    def test_repair_rejects_target_that_does_not_contain_the_item(self):
        row = self.assignment()
        invalid_target = AUnit(au_name='Unrelated unit', au_content='Q-999')
        self.db_add(invalid_target)

        response = self.client.post('/unit/api/repair-unit-membership', json={
            'student_id': self.student.id,
            'repairs': [{'row_id': row.id, 'target_au_id': invalid_target.au_id}],
        })

        self.assertEqual(response.status_code, 409)
        db.session.expire_all()
        self.assertEqual(db.session.get(MyWorkList, row.id).au_name, 'Original unit')


if __name__ == '__main__':
    unittest.main()
