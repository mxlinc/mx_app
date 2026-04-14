# PDF Generation Implementation Summary

## What Changed

### Architecture
**Before:** Matplotlib-based PNG rendering
- Fragile dependency chain (matplotlib → PIL → system libraries)
- Each math expression rendered as separate PNG image
- Inconsistent rendering between web and PDF
- Poor quality for complex equations

**After:** Native LaTeX compilation via pdflatex
- Single system dependency: pdflatex
- Complete question rendered to professional PDF
- Identical rendering across web and PDF
- Publication-quality mathematical output

## How It Works

### 1. Question Input (Strict LaTeX Format)
Users author questions following **LATEX_AUTHORING_GUIDELINES.md**:
```latex
Stem: Solve for $x$: $$x^2 - 5x + 6 = 0$$
Options:
- $x = 2$ or $x = 3$
- $x = 1$ or $x = 2$
- $x = -2$ or $x = -3$
```

### 2. Web Rendering
The same LaTeX is rendered on the web using MathJax:
- Frontend loads MathJax CDN
- Detects `$...$` and `$$...$$` patterns
- Renders to beautiful mathematical notation in real-time
- No server processing needed

### 3. PDF Generation (New Process)
When user clicks "Print":

**Step 1: Generate LaTeX Document**
```python
generate_latex_template(question_data, question_id)
```
- Takes the raw LaTeX from question
- Wraps in complete LaTeX document structure
- Includes metadata, options, images, correct answer
- Returns: full LaTeX source code

**Step 2: Compile to PDF**
```python
compile_latex_to_pdf(latex_source)
```
- Creates temporary directory
- Saves LaTeX source to `question.tex`
- Calls `pdflatex` subprocess: `pdflatex -interaction=nonstopmode question.tex`
- waits for compilation to complete
- Reads compiled `question.pdf`
- Cleans up temp files
- Returns: PDF as BytesIO buffer

**Step 3: Deliver PDF**
```python
return send_file(pdf_buffer, mimetype='application/pdf', ...)
```
- Browser downloads PDF named `question_{id}.pdf`

## Code Changes

### app.py Functions

1. **`escape_latex(text)`**
   - Escapes special LaTeX characters in text
   - Protects math expressions (preserves `$...$` and `$$...$$`)
   - Handles `&`, `%`, `_`, `{`, `}`, etc.

2. **`generate_latex_template(question_data, question_id)`**
   - Creates complete LaTeX document
   - Includes: title, metadata, question stem, options, images, answer key
   - Uses `\documentclass{article}` with math packages (amsmath, amssymb)

3. **`compile_latex_to_pdf(latex_source)`**
   - Compiles LaTeX source using pdflatex
   - Handles temporary file creation/cleanup
   - Catches errors (missing LaTeX, compilation failures, timeouts)
   - Returns PDF buffer or raises exception

4. **`generate_question_pdf(question_data, question_id)`**
   - Simple wrapper: calls template generator and compiler
   - Called by `/quiz/print/<question_id>` route

### Routes

**Existing:** No changes to core routes

**New:** `/quiz/print/<question_id>` 
- Fetches question from database
- Generates PDF
- Returns as downloadable file

### Frontend

**quiz_display.html:**
- Added "Print" link in top navigation
- Added event handler that calls `/quiz/print/{id}`

## Benefits

| Aspect | Before | After |
|--------|--------|-------|
| **Math Quality** | Low (PNG) | Excellent (LaTeX) |
| **Dependencies** | 5+ packages | 1 system package |
| **Web/PDF Consistency** | Different | Identical |
| **Performance** | Slow (many images) | Fast (single compilation) |
| **Reliability** | Fragile | Robust |
| **Maintainability** | Complex | Simple |
| **File Size** | Large (many PNGs) | Compact (single PDF) |

## Usage Example

### For Question Authors
```
1. Write question in LaTeX format
   - Use proper LaTeX syntax per guidelines
   - Test web rendering first (MathJax)
   
2. Save the question
   
3. Click "Print" button
   
4. Download PDF with perfect math rendering
```

### For End Users
```
1. View question in quiz
   - HTML with MathJax rendering
   
2. If you want to print or share:
   - Click "Print" button
   - Save as PDF or print directly
```

## Strict Authoring Requirements

All questions MUST follow these rules (enforced by LaTeX compilation):

1. **Inline Math:** `$expression$`
   ```latex
   ✓ Solve for $x$ in $2x + 1 = 5$
   ✗ Solve for x in 2x + 1 = 5
   ```

2. **Display Math:** `$$expression$$`
   ```latex
   ✓ Consider the function:
     $$f(x) = \frac{x^2 + 1}{x - 1}$$
   
   ✗ Consider the function:
     $f(x) = \frac{x^2 + 1}{x - 1}$
   ```

3. **Fractions:** `\frac{num}{den}`
   ```latex
   ✓ $\frac{1}{2}$
   ✗ $1/2$ or $\frac 1 2$
   ```

4. **Functions:** LaTeX commands
   ```latex
   ✓ $\sin(x)$, $\sqrt{2}$, $\log(x)$
   ✗ $sin(x)$, $sqrt(2)$, $log(x)$
   ```

5. **No HTML in Math:** Plain LaTeX only
   ```latex
   ✓ $x^2 + y^2 = z^2$
   ✗ $x<sup>2</sup> + y<sup>2</sup> = z<sup>2</sup>$
   ```

## System Requirements

### To Use the Feature
1. **Python packages:** `reportlab>=4.0.0` (for rendering to PDF format)
2. **System package:** `pdflatex` (the LaTeX compiler)
   - Windows: MiKTeX or TeX Live
   - macOS: basictex or MacTeX
   - Linux: `texlive-latex-base` + `texlive-latex-extra`

### To Author Questions
1. Read **LATEX_AUTHORING_GUIDELINES.md**
2. Understand LaTeX basics for math
3. Test on web before saving (verify MathJax renders)
4. Save and test PDF generation

## Error Handling

### If pdflatex not installed:
```
Exception: LaTeX compiler not installed. Please install texlive or MiKTeX.
```
→ Install LaTeX distribution (see PDF_SETUP_GUIDE.md)

### If LaTeX syntax invalid:
```
Exception: PDF compilation failed
[pdflatex shows detailed error]
```
→ Fix LaTeX in question (likely unescaped special chars or invalid syntax)

### If compilation times out:
```
Exception: PDF generation timed out
```
→ Check for infinite loops in LaTeX (30s timeout)

## Testing

### Automated (Dev)
```python
def test_pdf_generation():
    question_data = {...}  # Valid question
    pdf = generate_question_pdf(question_data, 1)
    assert pdf is not None
    assert len(pdf.getvalue()) > 0  # PDF has content
```

### Manual (User)
1. Create test question with simple math: `$x + y = z$`
2. Click Print
3. Verify PDF downloads
4. Open PDF and verify math renders

## Future Enhancements

Potential improvements:
- Add multiple export formats (DOCX, HTML)
- Batch PDF generation for quiz sets
- PDF watermarking with student info
- Interactive element support
- Custom header/footer per user/class

