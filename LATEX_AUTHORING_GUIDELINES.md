# LaTeX Authoring Guidelines for Questions

## Overview
All question content must follow strict LaTeX conventions to ensure consistent rendering across:
- Web display (MathJax)
- PDF generation (pdflatex compilation)

## Guidelines

### 1. Inline Math (Single Dollar Signs)
Use `$...$` for inline mathematical expressions that appear within text.

**✓ CORRECT:**
```
What is the value of $x$ in the equation $2x + 3 = 7$?
```

**✗ INCORRECT:**
```
What is the value of x in the equation 2x + 3 = 7?
What is the value of $x$ in the equation 2x + 3 = 7?
```

### 2. Display Math (Double Dollar Signs)
Use `$$...$$` for standalone mathematical expressions that should appear on their own line(s).

**✓ CORRECT:**
```
Solve the system of equations:
$$x + y = 5$$
$$x - y = 1$$
```

**✗ INCORRECT:**
```
Solve the system of equations:
$x + y = 5$
$x - y = 1$
```

### 3. LaTeX Syntax Requirements

#### Fractions
Always use `\frac{numerator}{denominator}`

**✓ CORRECT:**
```
$\frac{1}{2}$
$$\frac{x + 1}{x - 1}$$
```

**✗ INCORRECT:**
```
$1/2$
${1 \over 2}$
```

#### Exponents and Powers
Always use `^` with braces for multi-character exponents

**✓ CORRECT:**
```
$x^2$
$2^{10}$
$(x + y)^{2n}$
```

**✗ INCORRECT:**
```
$x**2$
$2^10$
$(x + y)^2n$
```

#### Subscripts
Always use `_` with braces for multi-character subscripts

**✓ CORRECT:**
```
$a_1$
$x_{n+1}$
$a_{b_c}$
```

**✗ INCORRECT:**
```
$a1$
$x_n+1$
```

#### Greek Letters
Always use backslash notation

**✓ CORRECT:**
```
$\alpha + \beta = \gamma$
$$\sum_{i=1}^{n} x_i$$
$$\Sigma = \frac{1}{\sqrt{2\pi}}$$
```

**✗ INCORRECT:**
```
$α + β = γ$
```

#### Operators and Functions
Always use LaTeX commands for special operators

**✓ CORRECT:**
```
$\sin(x)$, $\cos(x)$, $\tan(x)$
$\sqrt{2}$, $\sqrt[3]{8}$
$\log(x)$, $\ln(x)$
$\frac{d}{dx}$, $\int_0^1$
```

**✗ INCORRECT:**
```
sin(x), cos(x), tan(x)
sqrt(2)
log(x)
d/dx
```

#### Alignment in Display Math
Use `\quad` or `\qquad` for spacing between equations

**✓ CORRECT:**
```
$$\frac{xy}{x+y}=a,\quad \frac{xz}{x+z}=b,\quad \frac{yz}{y+z}=c$$
```

**✗ INCORRECT:**
```
$$\frac{xy}{x+y}=a, \frac{xz}{x+z}=b, \frac{yz}{y+z}=c$$
```

#### Spacing and Alignment
For complex multi-line expressions, use align environment in display math

**✓ CORRECT:**
```
$$\begin{align}
x + y &= 5 \\
x - y &= 1
\end{align}$$
```

**Can also use:**
```
$$\begin{array}{l}
x + y = 5 \\
x - y = 1
\end{array}$$
```

### 4. Text Formatting

#### Bold Text
Use `\textbf{...}` inside math mode or wrap in `<b>` tags outside

**✓ CORRECT:**
```
Given $\textbf{positive}$ integers, find $x$.
```

**For non-math text:**
```
<b>Given</b> positive integers, find x.
```

#### Italic Text
Use `\textit{...}` for emphasis

**✓ CORRECT:**
```
This is an \textit{important} constraint.
```

### 5. Special Cases

#### Absolute Value and Norms
Use `\left|...\right|` for scalability

**✓ CORRECT:**
```
$\left|x - 2\right| < 3$
$\left\lvert \frac{a}{b} \right\rvert$
```

#### Fractions in Fractions
Always use explicit braces

**✓ CORRECT:**
```
$$\frac{\frac{a}{b}}{c} = \frac{a}{bc}$$
```

#### Summation and Integration
Always use `_` and `^` for limits

**✓ CORRECT:**
```
$$\sum_{i=1}^{n} i^2 = \frac{n(n+1)(2n+1)}{6}$$
$$\int_0^{\infty} e^{-x} dx = 1$$
```

### 6. Common Mistakes to Avoid

| ✗ WRONG | ✓ CORRECT | Reason |
|---------|-----------|--------|
| `$x+y$` | `$x + y$` | Add spaces around operators |
| `$sin(x)$` | `$\sin(x)$` | Use LaTeX commands for functions |
| `$(x)^2$` | `$(x)^2$` or `$\left(x\right)^2$` | Parentheses don't scale |
| `$x^2+y^2$` | `$x^2 + y^2$` | Add spaces around `+` |
| `\frac 1 2` | `\frac{1}{2}` | Always use braces for fractions |
| `$1/2$` | `$\frac{1}{2}$` | Use \frac not forward slash |
| `One $ x $ plus two` | `One $x$ plus two` | No spaces inside `$` |
| Multiple $$ on same line poorly | Use `\quad` between expressions | Proper spacing |

### 7. Question Structure Template

#### For MCQ questions, follow this structure:

**Stem (Question Text):**
```
<b>Stem:</b> [Question text with inline math using $ $]
Or for complex math:
[Introduction text]
$$[Display math using $$ $$]$$
[Follow-up question]
```

**Options:**
Each option should be LaTeX-compatible and self-contained:
```
$\frac{abc}{ab+ac+bc}$
$\frac{2abc}{ab+ac+bc}$
$2^{10} + 2^{20}$
```

### 8. Validation Checklist

Before saving a question, ensure:

- [ ] All inline math expressions are wrapped in `$...$`
- [ ] All display math expressions are wrapped in `$$...$$`
- [ ] No mixing of $ and $$ on the same line
- [ ] All fractions use `\frac{}{}`
- [ ] All functions use LaTeX commands (`\sin`, `\cos`, `\sqrt`, etc.)
- [ ] All Greek letters use `\alpha`, `\beta`, etc.
- [ ] Spaces exist around binary operators (`+`, `-`, `=`, etc.)
- [ ] No HTML tags inside math expressions
- [ ] Backslashes are properly escaped in form inputs

### 9. Testing Your Questions

1. **Web Preview:** Copy the LaTeX and paste into the quiz builder preview to verify MathJax rendering
2. **PDF Print:** Click "Print" to generate PDF and verify proper mathematical notation
3. **Both match:** Ensure web and PDF displays are identical

---

## Summary

**One Rule to Remember:**
> Use `$...$` for inline math, `$$...$$` for display math, and always use proper LaTeX syntax. The same input will render identically on web and in PDF.

