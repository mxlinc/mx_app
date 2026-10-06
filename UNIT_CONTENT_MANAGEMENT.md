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
