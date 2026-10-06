"""Isolated latest-report and session-presence tests."""

import unittest
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch

from flask import Flask, Response, g
from flask_login import LoginManager
from sqlalchemy.exc import SQLAlchemyError

from db import db
from lms.reports import init_report_features
from lms.routes import lms_bp
from models import MyWorkList, StudentPresence, UserTable


NOW = datetime(2026, 3, 25, 3, 44)


class LatestReportTests(unittest.TestCase):
    def setUp(self):
        self.app = Flask(
            __name__, template_folder=str(Path(__file__).resolve().parents[1] / 'templates'),
        )
        self.app.config.update(
            TESTING=True, SECRET_KEY='report-test-only',
            SQLALCHEMY_DATABASE_URI='sqlite://',
            SQLALCHEMY_ENGINE_OPTIONS={
                'execution_options': {'schema_translate_map': {UserTable.__table__.schema: None}},
            },
        )
        db.init_app(self.app)
        login = LoginManager(self.app)
        login.login_view = 'lms.login'
        login.user_loader(lambda user_id: db.session.get(UserTable, int(user_id)))
        self.app.register_blueprint(lms_bp)
        for endpoint in (
            'question.list_questions_page', 'question.upload_page',
            'qb.quiz_list_page', 'qb.assign_page',
        ):
            self.app.add_url_rule(f'/test/{endpoint}', endpoint, lambda: '')
        self.app.add_url_rule('/test-page', 'test_page', lambda: '<html><body>Student page</body></html>')
        self.app.add_url_rule('/upper-page', 'upper_page', lambda: '<HTML><BODY>Page</BODY></HTML>')
        self.app.add_url_rule('/test-json', 'test_json', lambda: {'ok': True})
        self.app.add_url_rule(
            '/download', 'download',
            lambda: Response('<html><body>Sheet</body></html>', mimetype='text/html',
                             headers={'Content-Disposition': 'attachment; filename=sheet.html'}),
        )
        init_report_features(self.app)
        self.context = self.app.app_context()
        self.context.push()
        db.metadata.create_all(
            db.engine, tables=[UserTable.__table__, MyWorkList.__table__, StudentPresence.__table__],
        )
        self.admin = UserTable(username='admin-test', user_role='admin_new')
        self.student = UserTable(username='alice', full_name='Alice Example', user_role='student_new')
        db.session.add_all([self.admin, self.student])
        db.session.commit()
        self.client = self.app.test_client()
        self.login(self.admin)
        self.clock = patch('lms.reports.utc_now', return_value=NOW)
        self.clock.start()

    def tearDown(self):
        self.clock.stop()
        db.session.remove()
        db.engine.dispose()
        self.context.pop()

    def login(self, user, client=None):
        g.pop('_login_user', None)
        with (client or self.client).session_transaction() as cookie:
            cookie['_user_id'] = str(user.id)
            cookie['_fresh'] = True

    def work(self, code, updated=NOW, status='done', username='alice', score='8 of 10'):
        work = MyWorkList(
            user=username, au_name='Test unit', item_code=code,
            last_updated=updated, status=status, score=score,
        )
        db.session.add(work)
        db.session.commit()
        return work

    def presence(self, token, user=None, last_seen=NOW):
        db.session.add(StudentPresence(
            session_id=token, user_id=(user or self.student).id, last_seen=last_seen,
        ))
        db.session.commit()

    def heartbeat(self, client=None):
        return (client or self.client).post('/api/student-presence', headers={'X-MX-Presence': '1'})

    def test_dashboard_replaces_sheet_and_preserves_other_actions(self):
        html = self.client.get('/admin-new').get_data(as_text=True)
        self.assertIn('Latest Report', html)
        self.assertIn('href="/latest-report"', html)
        self.assertNotIn('Generate Sheet', html)
        self.assertNotIn('sheet-modal', html)
        self.assertNotIn('btn-open-sheet', html)
        self.assertIn('Quiz Review', html)
        self.assertIn('Create Unit', html)

    def test_default_window_filters_and_sorts_exact_timestamps(self):
        self.work('Q-newest', NOW)
        self.work('Q-older', NOW - timedelta(hours=1))
        self.work('Q-boundary', NOW - timedelta(days=7))
        for code, updated, status in (
            ('Q-too-old', NOW - timedelta(days=7, microseconds=1), 'done'),
            ('Q-future', NOW + timedelta(microseconds=1), 'done'),
            ('Q-assigned', NOW, 'assigned'),
            ('V-video', NOW, 'done'),
            ('I-interaction', NOW, 'done'),
        ):
            self.work(code, updated, status)
        self.work('Q-null', NOW)
        MyWorkList.query.filter_by(item_code='Q-null').update({'last_updated': None})
        db.session.commit()
        response = self.client.get('/latest-report')
        html = response.get_data(as_text=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn('value="7"', html)
        self.assertIn('Alice Example (alice)', html)
        self.assertIn('8 of 10', html)
        self.assertIn('24 Mar 23:44', html)
        self.assertLess(html.index('Q-newest'), html.index('Q-older'))
        self.assertLess(html.index('Q-older'), html.index('Q-boundary'))
        for code in ('Q-too-old', 'Q-future', 'Q-assigned', 'V-video', 'I-interaction', 'Q-null'):
            self.assertNotIn(code, html)
        self.assertEqual(response.headers['Cache-Control'], 'private, no-store')
        for label in ('Content', 'Actions', 'Dashboard', 'Sign Out'):
            self.assertIn(label, html)

    def test_changed_window_and_legacy_user_fallback(self):
        self.work('Q-legacy', NOW - timedelta(days=9), username='missing-account', score=None)
        html = self.client.get('/latest-report?days=10').get_data(as_text=True)
        self.assertIn('Q-legacy', html)
        self.assertIn('missing-account', html)
        self.assertIn('Not recorded', html)
        html = self.client.get('/latest-report?days=8').get_data(as_text=True)
        self.assertNotIn('Q-legacy', html)
        self.assertIn('No completed quizzes', html)

    def test_invalid_days_are_explicit_errors_not_default_reports(self):
        for value in ('0', '-1', '1.5', '', 'abc', '1e2', '999999999', '9' * 5000):
            with self.subTest(value=value):
                response = self.client.get('/latest-report', query_string={'days': value})
                self.assertEqual(response.status_code, 400)
                html = response.get_data(as_text=True)
                self.assertIn('Enter a whole number', html)
                self.assertNotIn('No completed quizzes', html)
        self.assertEqual(self.client.get('/latest-report?days=0007').status_code, 200)
        maximum = (NOW - datetime.min).days
        self.assertEqual(self.client.get(f'/latest-report?days={maximum}').status_code, 200)
        self.assertEqual(self.client.get(f'/latest-report?days={maximum + 1}').status_code, 400)

    def test_eastern_standard_time_and_dst_rolling_window(self):
        winter = datetime(2026, 1, 25, 4, 44)
        self.work('Q-winter', winter)
        with patch('lms.reports.utc_now', return_value=winter):
            html = self.client.get('/latest-report').get_data(as_text=True)
        self.assertIn('24 Jan 23:44', html)
        spring = datetime(2026, 3, 9, 4)
        self.work('Q-dst-boundary', spring - timedelta(hours=24))
        self.work('Q-dst-outside', spring - timedelta(hours=24, seconds=1))
        with patch('lms.reports.utc_now', return_value=spring):
            html = self.client.get('/latest-report?days=1').get_data(as_text=True)
        self.assertIn('Q-dst-boundary', html)
        self.assertNotIn('Q-dst-outside', html)
        self.assertIn('07 Mar 23:00', html)

    def test_access_for_both_admin_roles_and_denied_other_roles(self):
        for role in ('admin', 'admin_new'):
            self.admin.user_role = role
            db.session.commit()
            self.assertEqual(self.client.get('/latest-report').status_code, 200)
        for role in ('teacher', 'student', 'student_new', 'new'):
            self.admin.user_role = role
            db.session.commit()
            self.assertEqual(self.client.get('/latest-report').status_code, 403)
            self.assertEqual(self.client.get('/api/latest-report/online-users').status_code, 403)
        g.pop('_login_user', None)
        anonymous = self.app.test_client()
        self.assertEqual(anonymous.get('/latest-report').status_code, 302)
        self.assertEqual(anonymous.get('/api/latest-report/online-users').status_code, 302)
        self.assertEqual(self.heartbeat(anonymous).status_code, 401)

    def test_online_students_deduplicated_and_five_minute_boundary(self):
        self.presence('alice-1')
        self.presence('alice-2', last_seen=NOW - timedelta(minutes=5))
        expired = UserTable(username='expired', user_role='student', full_name='Expired Student')
        teacher = UserTable(username='teacher', user_role='teacher', full_name='Teacher')
        inactive = UserTable(username='inactive', user_role='student', is_active=False)
        future = UserTable(username='future', user_role='student')
        unnamed = UserTable(username='unnamed', user_role='new')
        db.session.add_all([expired, teacher, inactive, future, unnamed])
        db.session.commit()
        self.presence('expired', expired, NOW - timedelta(minutes=5, microseconds=1))
        self.presence('teacher', teacher)
        self.presence('admin', self.admin)
        self.presence('inactive', inactive)
        self.presence('future', future, NOW + timedelta(seconds=1))
        self.presence('unnamed', unnamed)
        data = self.client.get('/api/latest-report/online-users').json
        self.assertCountEqual(data['users'], ['Alice Example (alice)', 'unnamed'])
        self.assertEqual(data['users'].count('Alice Example (alice)'), 1)
        html = self.client.get('/latest-report').get_data(as_text=True)
        self.assertIn('Alice Example (alice)', html)
        self.assertNotIn('Expired Student', html)
        self.assertNotIn('Teacher', html)

    def test_heartbeat_refreshes_same_session_and_cleans_expired_records(self):
        self.login(self.student)
        self.presence('old', last_seen=NOW - timedelta(minutes=6))
        self.assertEqual(self.heartbeat().status_code, 204)
        with self.client.session_transaction() as cookie:
            token = cookie['presence_session']
        row = db.session.get(StudentPresence, token)
        self.assertEqual(row.user_id, self.student.id)
        self.assertEqual(row.last_seen, NOW)
        self.assertIsNone(db.session.get(StudentPresence, 'old'))
        later = NOW + timedelta(minutes=1)
        with patch('lms.reports.utc_now', return_value=later):
            self.assertEqual(self.heartbeat().status_code, 204)
        db.session.expire_all()
        self.assertEqual(StudentPresence.query.count(), 1)
        self.assertEqual(db.session.get(StudentPresence, token).last_seen, later)

    def test_heartbeat_denies_invalid_requests_and_inactive_accounts(self):
        self.assertEqual(self.heartbeat().status_code, 403)
        self.login(self.student)
        self.assertEqual(self.client.post('/api/student-presence').status_code, 400)
        self.student.is_active = False
        db.session.commit()
        self.assertEqual(self.heartbeat().status_code, 401)
        self.assertEqual(StudentPresence.query.count(), 0)

    def test_student_html_injection_covers_standalone_and_uppercase_pages_only(self):
        self.assertNotIn('student_presence.js', self.client.get('/test-page').get_data(as_text=True))
        self.login(self.student)
        for path in ('/test-page', '/upper-page'):
            response = self.client.get(path)
            self.assertEqual(response.get_data(as_text=True).count('student_presence.js'), 1)
            self.assertIn('data-presence-url="/api/student-presence"', response.get_data(as_text=True))
            self.assertEqual(response.headers['Cache-Control'], 'private, no-store')
        self.assertEqual(self.client.get('/test-json').json, {'ok': True})
        self.assertNotIn('student_presence.js', self.client.get('/download').get_data(as_text=True))

    def test_signout_removes_only_current_session_and_other_session_stays_online(self):
        self.login(self.student)
        self.heartbeat()
        with self.client.session_transaction() as cookie:
            token = cookie['presence_session']
        self.presence('other-browser')
        response = self.client.get('/logout')
        self.assertEqual(response.status_code, 302)
        self.assertIsNone(db.session.get(StudentPresence, token))
        self.assertIsNotNone(db.session.get(StudentPresence, 'other-browser'))
        self.assertEqual(self.heartbeat().status_code, 401)
        self.login(self.admin)
        self.assertEqual(self.client.get('/api/latest-report/online-users').json['users'],
                         ['Alice Example (alice)'])

    def test_report_database_failure_is_logged_and_shown(self):
        with patch('lms.reports.online_students', side_effect=SQLAlchemyError('test failure')):
            with self.assertLogs('lms.reports', level='ERROR'):
                response = self.client.get('/latest-report')
        self.assertEqual(response.status_code, 503)
        html = response.get_data(as_text=True)
        self.assertIn('Unable to load the report', html)
        self.assertIn('Unable to load currently logged in users', html)
        self.assertNotIn('No completed quizzes', html)

    def test_presence_database_failure_is_logged_and_returned(self):
        self.login(self.student)
        with patch.object(db.session, 'commit', side_effect=SQLAlchemyError('test failure')):
            with self.assertLogs('lms.reports', level='ERROR'):
                response = self.heartbeat()
        self.assertEqual(response.status_code, 503)
        self.assertIn('Unable to update', response.json['error'])
        self.assertEqual(StudentPresence.query.count(), 0)

    def test_online_refresh_failure_does_not_return_an_empty_success(self):
        with patch('lms.reports.online_students', side_effect=SQLAlchemyError('test failure')):
            with self.assertLogs('lms.reports', level='ERROR'):
                response = self.client.get('/api/latest-report/online-users')
        self.assertEqual(response.status_code, 503)
        self.assertIn('error', response.json)
        self.assertNotIn('users', response.json)

    def test_presence_initialization_is_idempotent(self):
        runner = self.app.test_cli_runner()
        for _ in range(2):
            result = runner.invoke(args=['init-report-presence'])
            self.assertEqual(result.exit_code, 0, result.output)
            self.assertIn('table is ready', result.output)


if __name__ == '__main__':
    unittest.main()
