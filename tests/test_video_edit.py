"""Isolated video-management regression tests; no production database is used."""

import unittest
from pathlib import Path
from unittest.mock import patch

from flask import Flask
from flask_login import LoginManager
from sqlalchemy.exc import SQLAlchemyError

from db import db
from lms.routes import lms_bp
from models import AUnit, MyWorkList, UserTable, Video


class VideoEditTests(unittest.TestCase):
    def setUp(self):
        self.app = Flask(
            __name__, template_folder=str(Path(__file__).resolve().parents[1] / 'templates')
        )
        self.app.config.update(
            TESTING=True,
            SECRET_KEY='video-test-only',
            SQLALCHEMY_DATABASE_URI='sqlite://',
            SQLALCHEMY_ENGINE_OPTIONS={
                'execution_options': {'schema_translate_map': {Video.__table__.schema: None}}
            },
        )
        db.init_app(self.app)
        login_manager = LoginManager(self.app)
        login_manager.login_view = 'lms.login'
        login_manager.user_loader(lambda user_id: db.session.get(UserTable, int(user_id)))
        self.app.register_blueprint(lms_bp)
        for endpoint in ('question.list_questions_page', 'qb.quiz_list_page', 'qb.assign_page'):
            self.app.add_url_rule(f'/test/{endpoint}', endpoint, lambda: '')
        self.context = self.app.app_context()
        self.context.push()
        db.metadata.create_all(
            db.engine,
            tables=[UserTable.__table__, Video.__table__, AUnit.__table__, MyWorkList.__table__],
        )
        self.admin = UserTable(username='admin-test', user_role='admin')
        self.video = Video(
            lesson_code='V-0001',
            file_name='old.html',
            display_name='Original name',
            broad_area='Algebra',
            details='Original notes',
        )
        db.session.add_all([self.admin, self.video])
        db.session.commit()
        self.video_id = self.video.id
        self.client = self.app.test_client()
        with self.client.session_transaction() as session:
            session['_user_id'] = str(self.admin.id)
            session['_fresh'] = True

    def tearDown(self):
        db.session.remove()
        db.engine.dispose()
        self.context.pop()

    def payload(self, **changes):
        data = {
            'id': self.video_id,
            'file_name': 'new.html',
            'display_name': 'Updated name',
            'broad_area': 'Geometry',
            'details': 'Updated notes',
        }
        data.update(changes)
        return data

    def assign(self, code='V-0001', status='assigned', user='student-test'):
        assignment = MyWorkList(
            user=user, au_name='Test unit', item_code=code,
            item_detail='https://mx-app-mm.onrender.com/packages/advanced/old.html',
            status=status, views=3, score='5',
        )
        db.session.add(assignment)
        db.session.commit()
        return assignment

    def test_update_all_fields_and_existing_assignment_urls(self):
        assignments = [
            self.assign(status=status, user=f'student-{status}')
            for status in ('future', 'assigned', 'done')
        ]
        other_assignment = self.assign(code='V-0002', user='other-student')
        response = self.client.post('/videos/update', json=self.payload())
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json, {'ok': True})
        db.session.expire_all()
        self.assertEqual(self.video.file_name, 'new.html')
        self.assertEqual(self.video.display_name, 'Updated name')
        self.assertEqual(self.video.broad_area, 'Geometry')
        self.assertEqual(self.video.details, 'Updated notes')
        self.assertEqual(self.video.lesson_code, 'V-0001')
        self.assertEqual(self.video.id, self.video_id)
        self.assertIsNotNone(self.video.last_updated)
        for assignment in assignments:
            self.assertEqual(
                assignment.item_detail,
                'https://mx-app-mm.onrender.com/packages/advanced/new.html',
            )
            self.assertEqual(assignment.views, 3)
            self.assertEqual(assignment.score, '5')
        self.assertTrue(other_assignment.item_detail.endswith('/old.html'))

    def test_unchanged_filename_preserves_existing_assignment_url(self):
        assignment = self.assign()
        assignment.item_detail = 'https://example.invalid/custom-playback'
        db.session.commit()
        response = self.client.post('/videos/update', json=self.payload(file_name='old.html'))
        self.assertEqual(response.status_code, 200)
        db.session.expire_all()
        self.assertEqual(assignment.item_detail, 'https://example.invalid/custom-playback')

    def test_trimming_and_clearing_optional_fields(self):
        response = self.client.post('/videos/update', json=self.payload(
            file_name=' new.html ', display_name=' New name ', broad_area=' ', details=' '
        ))
        self.assertEqual(response.status_code, 200)
        db.session.expire_all()
        self.assertEqual(self.video.file_name, 'new.html')
        self.assertEqual(self.video.display_name, 'New name')
        self.assertIsNone(self.video.broad_area)
        self.assertIsNone(self.video.details)

    def test_field_length_boundaries(self):
        response = self.client.post('/videos/update', json=self.payload(
            file_name='f' * 255, display_name='d' * 255, broad_area='a' * 100
        ))
        self.assertEqual(response.status_code, 200)
        for field, length in (('file_name', 256), ('display_name', 256), ('broad_area', 101)):
            with self.subTest(field=field):
                response = self.client.post('/videos/update', json=self.payload(**{field: 'x' * length}))
                self.assertEqual(response.status_code, 400)
                self.assertIn(field, response.json['error'])

    def test_invalid_fields_do_not_modify_video(self):
        for changes in (
            {'file_name': ''}, {'display_name': '  '}, {'details': []},
            {'broad_area': None}, {'display_name': 123},
        ):
            with self.subTest(changes=changes):
                response = self.client.post('/videos/update', json=self.payload(**changes))
                self.assertEqual(response.status_code, 400)
                self.assertFalse(response.json['ok'])
        incomplete = self.payload()
        del incomplete['file_name']
        self.assertEqual(self.client.post('/videos/update', json=incomplete).status_code, 400)
        db.session.expire_all()
        self.assertEqual(self.video.file_name, 'old.html')

    def test_invalid_json_and_ids(self):
        for route in ('/videos/update', '/videos/delete'):
            for body in ([], 'not an object', None):
                with self.subTest(route=route, body=body):
                    response = self.client.post(route, json=body)
                    self.assertEqual(response.status_code, 400)
                    self.assertFalse(response.json['ok'])
            response = self.client.post(route, data='{broken', content_type='application/json')
            self.assertEqual(response.status_code, 400)
            for video_id in (None, '', '1', True, 0, -1, 1.5):
                with self.subTest(route=route, video_id=video_id):
                    response = self.client.post(route, json=self.payload(id=video_id))
                    self.assertEqual(response.status_code, 400)

    def test_missing_video(self):
        for route in ('/videos/update', '/videos/delete'):
            response = self.client.post(route, json=self.payload(id=999))
            self.assertEqual(response.status_code, 404)
            self.assertEqual(response.json['error'], 'Video not found')

    def test_non_admin_is_forbidden(self):
        for role in ('student', 'student_new', 'teacher', 'new'):
            self.admin.user_role = role
            db.session.commit()
            for route in ('/videos/update', '/videos/delete'):
                with self.subTest(role=role, route=route):
                    response = self.client.post(route, json=self.payload())
                    self.assertEqual(response.status_code, 403)
        db.session.expire_all()
        self.assertEqual(self.video.file_name, 'old.html')

    def test_admin_new_can_edit_and_delete(self):
        self.admin.user_role = 'admin_new'
        db.session.commit()
        self.assertEqual(self.client.post('/videos/update', json=self.payload()).status_code, 200)
        self.assertEqual(
            self.client.post('/videos/delete', json={'id': self.video_id}).status_code, 200
        )

    def test_login_is_required(self):
        with self.client.session_transaction() as session:
            session.clear()
        for route in ('/videos/update', '/videos/delete'):
            response = self.client.post(route, json=self.payload())
            self.assertEqual(response.status_code, 302)
            self.assertIn('/login', response.location)

    def test_delete_unreferenced_video(self):
        db.session.add(AUnit(au_name='Other unit', au_content='V-00010|Q-0001'))
        db.session.commit()
        self.assign(code='V-00010')
        response = self.client.post('/videos/delete', json={'id': self.video_id})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json, {'ok': True})
        self.assertIsNone(db.session.get(Video, self.video_id))
        self.assertEqual(AUnit.query.count(), 1)
        self.assertEqual(MyWorkList.query.count(), 1)

    def test_unit_reference_blocks_delete_with_exact_trimmed_code_matching(self):
        db.session.add(AUnit(au_name='Referenced unit', au_content='Q-0001| V-0001 |I-0001'))
        db.session.commit()
        response = self.client.post('/videos/delete', json={'id': self.video_id})
        self.assertEqual(response.status_code, 409)
        self.assertIn('1 unit(s)', response.json['error'])
        self.assertIn('0 student', response.json['error'])
        self.assertIsNotNone(db.session.get(Video, self.video_id))

    def test_work_list_references_block_delete_for_every_status(self):
        for status in ('future', 'assigned', 'done'):
            with self.subTest(status=status):
                assignment = self.assign(status=status)
                response = self.client.post('/videos/delete', json={'id': self.video_id})
                self.assertEqual(response.status_code, 409)
                self.assertIn('1 student', response.json['error'])
                self.assertIsNotNone(db.session.get(Video, self.video_id))
                db.session.delete(assignment)
                db.session.commit()

    def test_commit_failure_rolls_back_video_and_assignment(self):
        assignment = self.assign()
        for route in ('/videos/update', '/videos/delete'):
            if route.endswith('delete'):
                db.session.delete(assignment)
                db.session.commit()
            with patch.object(db.session, 'commit', side_effect=SQLAlchemyError('test failure')):
                with self.assertLogs('lms.routes', level='ERROR'):
                    response = self.client.post(route, json=self.payload())
            self.assertEqual(response.status_code, 500)
            self.assertFalse(response.json['ok'])
            db.session.expire_all()
            self.assertIsNotNone(db.session.get(Video, self.video_id))
            self.assertEqual(self.video.file_name, 'old.html')
            if route.endswith('update'):
                self.assertTrue(assignment.item_detail.endswith('/old.html'))

    def test_notes_only_endpoint_remains_compatible(self):
        response = self.client.post(
            '/videos/update-details', json={'id': self.video_id, 'details': 'Notes only'}
        )
        self.assertEqual(response.status_code, 200)
        db.session.expire_all()
        self.assertEqual(self.video.details, 'Notes only')
        self.assertEqual(self.video.file_name, 'old.html')

    def test_list_renders_edit_fields_and_safely_preloaded_values(self):
        self.video.display_name = 'Name with "quotes" and \'apostrophes\' <tag>'
        self.video.details = 'Notes with </script> and \'apostrophes\''
        db.session.commit()
        response = self.client.get('/videos/list')
        self.assertEqual(response.status_code, 200)
        html = response.get_data(as_text=True)
        self.assertIn('>Edit</a>', html)
        self.assertNotIn('>Details</a>', html)
        for element_id in ('vd-file-name', 'vd-display-name', 'vd-area-select', 'vd-textarea'):
            self.assertIn(f'id="{element_id}"', html)
        self.assertIn('Delete this video', html)
        self.assertIn('"old.html", "Algebra"', html)
        self.assertIn(r'\u003c/script\u003e', html)


if __name__ == '__main__':
    unittest.main()
