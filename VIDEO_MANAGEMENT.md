# Video management

Admins (`admin` and `admin_new`) can manage the video catalogue at `/videos/list`.

## Editing

Select **Edit** beside a video to open its current File Name, Display Name,
Broad Area, and Video details / notes.

- File Name and Display Name are required, with a maximum of 255 characters each.
- Broad Area allows an existing area, a new area (up to 100 characters), or
  Uncategorised.
- Notes and Broad Area may be cleared.
- Save persists all fields together and refreshes the list, including its
  playback link, display name, and area grouping.
- A filename change also updates playback URLs for all existing student
  work-list entries with the video's lesson code, regardless of status.
  Student progress is preserved.
- Editing a filename does not rename, upload, or check the hosted file.
- Cancel, Escape, or clicking the backdrop discards unsaved changes.
- The video ID and lesson code do not change.

## Deleting

**Delete this video** requires confirmation. Deletion is blocked if any unit
or student work-list entry references the video's lesson code, including
completed work. The error reports the reference counts; remove those
references before retrying. Only the catalogue record is deleted, never
the hosted file.

## API compatibility and regression tests

The modal uses `POST /videos/update` and `POST /videos/delete`.
The existing `POST /videos/update-details` endpoint remains available for
notes-only callers.

Run the isolated SQLite regression tests on Windows:

```powershell
.\venv\Scripts\python.exe -m unittest discover -s tests -p test_video_edit.py -v
```

The tests use an in-memory database and do not access the production database.
