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
from models import MyWorkList, Quiz, StudentPresence, UserTable


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
            db.engine, tables=[
                UserTable.__table__, MyWorkList.__table__, Quiz.__table__, StudentPresence.__table__,
            ],
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

    def details(self, days='7', end=NOW, client=None):
        return (client or self.client).get('/api/latest-report/details', query_string={
            'days': days, 'end': end.strftime('%Y-%m-%dT%H:%M:%S.%f'),
        })

    def assert_summary(self, html, name, completed, wrong, incomplete=False):
        marker = '*' if incomplete else ''
        self.assertIn(
            f'<td>{name}</td><td>{completed}</td><td class="wrong-count">{wrong}{marker}</td></tr>',
            html,
        )

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
        self.assertNotIn('Alice Example (alice)', html)
        self.assert_summary(html, 'Alice Example', 3, 6)
        self.assertIn(
            '<th scope="col">Row#</th><th scope="col">Student</th><th scope="col">#Quiz</th>'
            '<th scope="col">#Wrong Questions</th>', html,
        )
        self.assertLess(html.index('Student quiz summary'), html.index('id="report-details-button"'))
        self.assertNotIn('<table>', html)
        self.assertEqual(html.count('<table aria-label="Student quiz summary">'), 1)
        self.assertNotIn('<th scope="col">Quiz item code-title</th>', html)
        self.assertNotIn('Q-newest', html)
        self.assertIn('id="report-details"', html)
        self.assertIn('hidden></div>', html)
        details = self.details()
        self.assertEqual(details.status_code, 200)
        records = details.json['records']
        self.assertEqual([record['quiz'] for record in records], [
            'Q-newest-Title unavailable', 'Q-older-Title unavailable', 'Q-boundary-Title unavailable',
        ])
        self.assertEqual(records[0], {
            'user': 'Alice Example', 'quiz': 'Q-newest-Title unavailable',
            'score': '8 of 10', 'updated': '24 Mar 23:44',
        })
        for code in ('Q-too-old', 'Q-future', 'Q-assigned', 'V-video', 'I-interaction', 'Q-null'):
            self.assertNotIn(code, str(records))
        self.assertEqual(response.headers['Cache-Control'], 'private, no-store')
        self.assertEqual(details.headers['Cache-Control'], 'private, no-store')
        for label in ('Content', 'Actions', 'Dashboard', 'Sign Out'):
            self.assertIn(label, html)

    def test_changed_window_and_legacy_user_fallback(self):
        self.work('Q-legacy', NOW - timedelta(days=9), username='missing-account', score=None)
        html = self.client.get('/latest-report?days=10').get_data(as_text=True)
        self.assert_summary(html, 'missing-account', 1, 0, incomplete=True)
        self.assertIn('results unavailable for 1 quiz', html)
        records = self.details(days='10').json['records']
        self.assertEqual(records[0]['user'], 'missing-account')
        self.assertEqual(records[0]['score'], 'Not recorded')
        html = self.client.get('/latest-report?days=8').get_data(as_text=True)
        self.assertNotIn('Q-legacy', html)
        self.assertIn('No completed quizzes', html)
        self.assertNotIn('Student quiz summary', html)
        self.assertEqual(self.details(days='8').json['records'], [])

    def test_summary_groups_by_account_not_name_and_sums_scores(self):
        duplicate = UserTable(username='other-alice', full_name='Alice Example', user_role='student')
        db.session.add(duplicate)
        db.session.commit()
        self.work('Q-first', NOW - timedelta(hours=2), score='3 of 5')
        self.work('Q-second', NOW - timedelta(hours=1), score=' 7 out of 10 ')
        self.work('Q-perfect', username='other-alice', score='10 of 10')
        html = self.client.get('/latest-report').get_data(as_text=True)
        self.assert_summary(html, 'Alice Example', 2, 5)
        self.assert_summary(html, 'Alice Example', 1, 0)
        self.assertNotIn('(alice)', html)
        self.assertNotIn('(other-alice)', html)
        self.assertLess(
            html.index('<td>Alice Example</td><td>1</td>'),
            html.index('<td>Alice Example</td><td>2</td>'),
        )

    def test_summary_name_fallback_and_online_label_unchanged(self):
        self.student.full_name = 'Rebecca'
        unnamed = UserTable(username='unnamed', full_name='   ', user_role='student')
        db.session.add(unnamed)
        db.session.commit()
        self.presence('alice-online')
        self.work('Q-named', score='9 of 10')
        self.work('Q-unnamed', username='unnamed', score='1 of 1')
        html = self.client.get('/latest-report').get_data(as_text=True)
        self.assertIn('Rebecca (alice)', html)
        report = html.split('<section class="report-section"', 1)[1]
        self.assert_summary(report, 'Rebecca', 1, 1)
        self.assertNotIn('(alice)', report)
        self.assert_summary(report, 'unnamed', 1, 0)
        self.assertCountEqual(
            [record['user'] for record in self.details().json['records']], ['Rebecca', 'unnamed'],
        )

    def test_summary_alphabetical_names_and_row_numbers_leave_details_newest_first(self):
        self.student.full_name = 'Rebecca'
        db.session.add_all([
            UserTable(username='z-account', full_name='alice', user_role='student'),
            UserTable(username='a-account', full_name='Bob', user_role='student'),
        ])
        db.session.commit()
        self.work('Q-rebecca', score='8 of 10')
        self.work('Q-alice', NOW - timedelta(hours=2), username='z-account', score='10 of 10')
        self.work('Q-bob', NOW - timedelta(hours=1), username='a-account', score='9 of 10')
        self.work('Q-fallback', NOW - timedelta(hours=3), username='aaron', score='10 of 10')
        self.work('Q-excluded', NOW - timedelta(days=9), username='excluded')
        for days in ('7', '1'):
            with self.subTest(days=days):
                html = self.client.get('/latest-report', query_string={'days': days}).get_data(as_text=True)
                rows = [
                    '<tr><td>1</td><td>aaron</td><td>1</td><td class="wrong-count">0</td></tr>',
                    '<tr><td>2</td><td>alice</td><td>1</td><td class="wrong-count">0</td></tr>',
                    '<tr><td>3</td><td>Bob</td><td>1</td><td class="wrong-count">1</td></tr>',
                    '<tr><td>4</td><td>Rebecca</td><td>1</td><td class="wrong-count">2</td></tr>',
                ]
                positions = [html.index(row) for row in rows]
                self.assertEqual(positions, sorted(positions))
                self.assertEqual(html.count('<td class="wrong-count">'), 4)
                self.assertNotIn('<tr><td>5</td>', html)
                self.assertNotIn('excluded', html)
                self.assertEqual(
                    [record['user'] for record in self.details(days=days).json['records']],
                    ['Rebecca', 'Bob', 'alice', 'aaron'],
                )

    def test_summary_missing_and_invalid_scores_do_not_claim_complete_totals(self):
        self.work('Q-known', score='8 of 10')
        for index, score in enumerate((None, '', 'Not recorded', '11 of 10', '-1 of 10', '8 of 10 extra')):
            self.work(f'Q-unknown-{index}', score=score)
        html = self.client.get('/latest-report').get_data(as_text=True)
        self.assert_summary(html, 'Alice Example', 7, 2, incomplete=True)
        self.assertIn('results unavailable for 6 quizzes', html)

    def test_summary_changes_with_selected_period(self):
        self.work('Q-recent', score='9 of 10')
        self.work('Q-old', NOW - timedelta(days=9), score='5 of 10')
        html = self.client.get('/latest-report').get_data(as_text=True)
        self.assert_summary(html, 'Alice Example', 1, 1)
        html = self.client.get('/latest-report?days=10').get_data(as_text=True)
        self.assert_summary(html, 'Alice Example', 2, 6)
        self.assertNotIn('<table>', html)
        self.assertNotIn('Q-old', html)
        self.assertEqual(len(self.details(days='10').json['records']), 2)

    def test_details_titles_are_loaded_only_on_request(self):
        db.session.add(Quiz(quiz_code='Q-0001', title='Adding fractions'))
        db.session.commit()
        self.work('Q-0001')
        with patch('lms.reports.Quiz') as quiz:
            html = self.client.get('/latest-report').get_data(as_text=True)
            quiz.query.filter.assert_not_called()
        self.assertNotIn('Adding fractions', html)
        self.assertNotIn('Q-0001', html)
        self.assertEqual(self.details().json['records'][0]['quiz'], 'Q-0001-Adding fractions')

    def test_details_window_does_not_move_when_button_is_clicked_later(self):
        self.work('Q-boundary', NOW - timedelta(days=7))
        self.work('Q-new-after-summary', NOW + timedelta(minutes=1))
        with patch('lms.reports.utc_now', return_value=NOW + timedelta(minutes=2)):
            records = self.details().json['records']
        self.assertEqual([record['quiz'] for record in records], ['Q-boundary-Title unavailable'])

    def test_details_invalid_periods_are_explicit_errors(self):
        for value in ('', 'not-a-time', '2026-03-25', '2026-03-25T03:44:00.000000+00:00'):
            with self.subTest(end=value):
                response = self.client.get('/api/latest-report/details', query_string={'end': value})
                self.assertEqual(response.status_code, 400)
                self.assertIn('Invalid report period', response.json['error'])
        self.assertEqual(self.details(end=NOW + timedelta(seconds=1)).status_code, 400)
        for value in ('0', '-1', '1.5', '', 'abc', '9' * 5000):
            with self.subTest(days=value):
                response = self.details(days=value)
                self.assertEqual(response.status_code, 400)
                self.assertIn('Enter a whole number', response.json['error'])

    def test_details_database_failure_is_logged_and_returned(self):
        with patch('lms.reports.completed_quizzes', side_effect=SQLAlchemyError('test failure')):
            with self.assertLogs('lms.reports', level='ERROR'):
                response = self.details()
        self.assertEqual(response.status_code, 503)
        self.assertIn('Unable to load report details', response.json['error'])
        self.assertNotIn('records', response.json)

    def test_invalid_days_are_explicit_errors_not_default_reports(self):
        for value in ('0', '-1', '1.5', '', 'abc', '1e2', '999999999', '9' * 5000):
            with self.subTest(value=value):
                response = self.client.get('/latest-report', query_string={'days': value})
                self.assertEqual(response.status_code, 400)
                html = response.get_data(as_text=True)
                self.assertIn('Enter a whole number', html)
                self.assertNotIn('No completed quizzes', html)
                self.assertNotIn('Student quiz summary', html)
        self.assertEqual(self.client.get('/latest-report?days=0007').status_code, 200)
        maximum = (NOW - datetime.min).days
        self.assertEqual(self.client.get(f'/latest-report?days={maximum}').status_code, 200)
        self.assertEqual(self.client.get(f'/latest-report?days={maximum + 1}').status_code, 400)

    def test_eastern_standard_time_and_dst_rolling_window(self):
        winter = datetime(2026, 1, 25, 4, 44)
        self.work('Q-winter', winter)
        with patch('lms.reports.utc_now', return_value=winter):
            records = self.details(end=winter).json['records']
        self.assertEqual(records[0]['updated'], '24 Jan 23:44')
        spring = datetime(2026, 3, 9, 4)
        self.work('Q-dst-boundary', spring - timedelta(hours=24))
        self.work('Q-dst-outside', spring - timedelta(hours=24, seconds=1))
        with patch('lms.reports.utc_now', return_value=spring):
            records = self.details(days='1', end=spring).json['records']
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]['quiz'], 'Q-dst-boundary-Title unavailable')
        self.assertEqual(records[0]['updated'], '07 Mar 23:00')

    def test_access_for_both_admin_roles_and_denied_other_roles(self):
        for role in ('admin', 'admin_new'):
            self.admin.user_role = role
            db.session.commit()
            self.assertEqual(self.client.get('/latest-report').status_code, 200)
            self.assertEqual(self.details().status_code, 200)
        for role in ('teacher', 'student', 'student_new', 'new'):
            self.admin.user_role = role
            db.session.commit()
            self.assertEqual(self.client.get('/latest-report').status_code, 403)
            self.assertEqual(self.client.get('/api/latest-report/online-users').status_code, 403)
            self.assertEqual(self.details().status_code, 403)
        g.pop('_login_user', None)
        anonymous = self.app.test_client()
        self.assertEqual(anonymous.get('/latest-report').status_code, 302)
        self.assertEqual(anonymous.get('/api/latest-report/online-users').status_code, 302)
        self.assertEqual(self.details(client=anonymous).status_code, 302)
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
