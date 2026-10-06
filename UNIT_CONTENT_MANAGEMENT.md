# Unit content ordering

On `/units/list`, open a unit's content modal to drag items into a new order,
remove items, or sort selected quizzes.

## Sorting selected quizzes

- Each quiz has a selection checkbox. Videos and interactions do not.
- **Sort Selected Quizzes** appears when at least one quiz is selected and is
  enabled when at least two are selected.
- Sorting uses the numeric suffix of the displayed quiz code, not the database
  quiz ID: `Q-2` comes before `Q-10`.
- Selected quizzes exchange only their currently occupied positions.
  Every unselected item stays in its current position.
- Selections remain checked after sorting.
- A quiz marked "not found" can still be sorted if its code has a valid numeric
  suffix. Invalid codes have a disabled checkbox with an explanation.
- Sorting changes the draft only. Click **Save Order** to persist it.
  Cancel or close the modal to discard unsaved changes.
- Existing drag-and-drop and removal controls remain available.

For example, selecting only `Q-30` and `Q-10` in:

```text
V-1 | Q-30 | Q-20 | I-1 | Q-10
```

produces:

```text
V-1 | Q-10 | Q-20 | I-1 | Q-30
```

## Regression tests

Run the dependency-free JavaScript tests:

```powershell
node --test .\tests\test_unit_quiz_sort.js
```

## Latest Report

The admin dashboard replaces Generate Sheet with **Latest Report** at
`/latest-report`. It is also available in the shared header's Actions menu.
Sheet generation endpoints remain available elsewhere.

The report lists completed `Q-` quiz records from `my_work_list`, newest first,
with the student's full name and username, item code, stored score, and last
updated timestamp. The default window is 7 rolling 24-hour days; Apply or Enter
updates it. Positive whole numbers are accepted up to the supported date limit.
Existing work-list timestamps are UTC without a timezone; display timestamps
are converted to America/New_York, including daylight saving time. This is the
latest state of each assignment, not an attempt history.

The compact online row includes only student roles (`student`, `student_new`,
and `new`), not teachers or admins. Authenticated HTML student pages send a
heartbeat every minute. A browser session expires from the online list after
5 minutes without a heartbeat; signing out removes that session immediately.
Multiple browser sessions are deduplicated by user. Both open idle pages and
background tabs send heartbeats, subject to browser timer throttling or device
sleep. Presence collection starts after deployment when students load a page.
The online row refreshes every minute and when the report tab becomes visible.
Network/database failures are displayed rather than reported as an empty list.

### Deployment

Before serving the new code, manually run
[latest_report_presence.sql](migrations/latest_report_presence.sql) in the
backend SQL editor. It targets `prod`; replace the schema and index-name prefix
if the deployment uses another `APP_SCHEMA`. The script is safe to rerun.

Alternatively, create the table using the deployment's `DATABASE_URL` and
`APP_SCHEMA`:

```powershell
.\venv\Scripts\python.exe -m flask --app app init-report-presence
```

Both options create only `student_presence` and its indexes; they
does not alter existing users or work records. Run it for each deployed schema.
Database sessions must use UTC to match existing work-list timestamp writes.
`tzdata` supplies IANA timezone data on Windows and systems without OS data.

Run isolated report regressions (no production records are read or changed):

```powershell
.\venv\Scripts\python.exe -m unittest discover -s tests -p test_latest_report.py
node --test .\tests\test_report_presence.js
```
