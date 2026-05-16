# FEVAL Question Type — Authoring Guide

## What is FEVAL?

**FEVAL** (Fill with Evaluation) is a question type where the student enters one or more numeric values and correctness is checked by running Python-style logical expressions (rules) against those values.

Unlike a standard fill-in-the-blank that checks for an exact match, FEVAL lets you write rules like `a + b == -7` — so the same question accepts any pair of values that satisfy the condition.

---

## Anatomy of an FEVAL Question

| Part | What it is |
|------|-----------|
| **Stem** | Question text, written in LaTeX |
| **Variables** | Named input boxes shown to the student |
| **Rules** | Python expressions that must all be `True` for a correct answer |

---

## Variables

Each variable becomes one input box. Each has two fields:

| Field | Example |
|-------|---------|
| **Variable Name** — used in rules | `a`, `b`, `x` |
| **Label** — shown above the input | `First integer`, `Value of x` |

Student input is parsed as a number before rules run. Decimals, negatives, and integers all work. Unparseable input is treated as `0`.

---

## Rules — What You Can Write

Rules are Python-style boolean expressions. **All rules must pass** for the answer to be correct.

### Operators

```python
a + b          # arithmetic: + - * / ** % //
a == 7         # comparisons: == != > >= < <=
a > 0 and b > 0    # logical: and  or  not
```

### Built-in Functions

| Function | Meaning |
|----------|---------|
| `abs(a)` | Absolute value |
| `round(a, 2)` | Round to 2 decimal places |
| `max(a, b)` | Larger of two values |
| `min(a, b)` | Smaller of two values |
| `isinstance(a, int)` | True if whole number |
| `isinstance(a, float)` | True if decimal |

---

## Feedback Templates

Each rule has an optional feedback message shown when that rule fails. Embed computed values with `{expression}`.

| Template | Shown to student (a=3, b=5) |
|----------|----------------------------|
| `Sum is {a+b}, not -7` | Sum is 8, not -7 |
| `Product {a*b} should be < 10` | Product 15 should be < 10 |
| `Expected {a} to be negative` | Expected 3 to be negative |

---

## Examples

### Example 1 — Sum of two integers
> *"Enter two integers whose sum is $-7$."*

Variables: `a` (First integer), `b` (Second integer)
```
Rule:     a + b == -7
Feedback: Sum is {a+b}, not -7
```

---

### Example 2 — Multiple constraints
> *"Enter two different positive integers whose product is less than 20."*

Variables: `a`, `b`
```
Rule 1:   isinstance(a, int) and isinstance(b, int)
Feedback: Both values must be whole numbers

Rule 2:   a > 0 and b > 0
Feedback: Both values must be positive

Rule 3:   a != b
Feedback: The two values must be different

Rule 4:   a * b < 20
Feedback: Product is {a*b}, which is not less than 20
```

---

### Example 3 — Quadratic roots
> *"Enter both roots of $x^2 - 5x + 6 = 0$."*

Variables: `p` (First root), `q` (Second root)
```
Rule 1:   p + q == 5
Feedback: Sum of roots should be 5, you got {p+q}

Rule 2:   p * q == 6
Feedback: Product of roots should be 6, you got {p*q}
```

---

### Example 4 — Decimal with tolerance
> *"What is $\sqrt{2}$ to 2 decimal places?"*

Variables: `x` (Your answer)
```
Rule:     abs(x - 1.41) < 0.005
Feedback: Expected approximately 1.41, you entered {x}
```

---

### Example 5 — Integer constraint
> *"Enter an even number between 10 and 20 (inclusive)."*

Variables: `n` (Your number)
```
Rule 1:   isinstance(n, int)
Feedback: Must be a whole number

Rule 2:   n >= 10 and n <= 20
Feedback: {n} is not between 10 and 20

Rule 3:   n % 2 == 0
Feedback: {n} is odd
```

---

## Common Mistakes

| ✗ Wrong | ✓ Correct | Reason |
|--------|-----------|--------|
| `a + b = -7` | `a + b == -7` | `=` is assignment; use `==` to compare |
| `2 < a < 10` | `a > 2 and a < 10` | Chained comparisons not supported |
| `a^2` | `a ** 2` | Python uses `**` for powers |
| `a / b == 0.5` | `abs(a/b - 0.5) < 0.001` | Use tolerance for decimal comparisons |
| Using `c` in a rule without declaring it | Add `c` as a variable | All names in rules must be declared variables |

---

## How Scoring Works

- All rules are evaluated together.
- **All must pass** — there is no partial credit.
- Failed rules show their feedback messages to the student.
