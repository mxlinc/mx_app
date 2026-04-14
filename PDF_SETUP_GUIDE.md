# PDF Generation Setup Guide

## Overview
The PDF generation feature for questions now uses **native LaTeX compilation** (pdflatex) instead of image rendering. This ensures:
- Perfect mathematical notation in PDFs
- Professional, publication-ready output
- Consistent rendering across web and PDF

## System Requirements

### 1. Install LaTeX Distribution

#### Windows
Install **MiKTeX** (recommended):
1. Download from: https://miktex.org/download
2. Run the installer
3. Choose "Install MiKTeX with default settings"
4. Restart your computer

OR install **TeX Live**:
1. Download from: https://tug.org/texlive/
2. Run the installer and follow instructions

#### macOS
Install via Homebrew:
```bash
brew install --cask basictex
```

Or via MacPorts:
```bash
sudo port install texlive
```

#### Linux (Ubuntu/Debian)
```bash
sudo apt-get update
sudo apt-get install texlive-latex-base texlive-latex-extra texlive-fonts-recommended
```

#### Linux (Fedora/RHEL)
```bash
sudo dnf install texlive texlive-latex texlive-xetex
```

### 2. Verify Installation
After installation, verify `pdflatex` is accessible:

```bash
pdflatex --version
```

You should see output like:
```
pdflatex (TeX Live 2024) 3.141592653-2.6-1.40.25
```

If you get "command not found", you may need to:
- Add the binary path to your system PATH
- Restart your terminal/IDE
- Restart your computer (especially on Windows)

## Python Dependencies

The PDF generator requires only `reportlab`:

```bash
pip install -r requirements.txt
```

This will install `reportlab>=4.0.0` which is used for the document structure (though the heavy math rendering is done by pdflatex).

## Testing the Feature

1. Create or edit an MCQ question following the **LATEX_AUTHORING_GUIDELINES.md**
2. Save the question
3. Click the "Print" button in the question display page
4. A PDF should download with properly rendered mathematics

### If PDF Generation Fails

**Error: "LaTeX compiler not installed"**
- Ensure pdflatex is installed and in your PATH
- Restart your application after installing LaTeX

**Error: "PDF compilation failed"**
- Check your LaTeX syntax in the question stem/options
- Verify all math expressions are within `$...$` or `$$...$$`
- Check the application logs for detailed pdflatex error messages

## Authoring Guidelines

Follow the strict LaTeX conventions in **LATEX_AUTHORING_GUIDELINES.md**:

### ✓ CORRECT Format
```
Solve for $x$: $$2x + 3 = 7$$
```

### ✗ INCORRECT Format
```
Solve for x: 2x + 3 = 7
Solve for $x$: $2x + 3 = 7$
```

**Key Rules:**
- Use `$...$` for inline math
- Use `$$...$$` for display math
- Use `\frac{}{}` for fractions, not `/`
- Use LaTeX commands for functions: `\sin`, `\cos`, `\sqrt`, etc.
- Use `\_` to escape underscores in text

## LaTeX Features Supported

| Feature | Syntax | Example |
|---------|--------|---------|
| Inline Math | `$expression$` | `$\frac{1}{2}$` |
| Display Math | `$$expression$$` | `$$\sum_{i=1}^n i$$` |
| Fractions | `\frac{num}{den}` | `$\frac{x+1}{x-1}$` |
| Exponents | `^{exp}` | `$2^{10}$` |
| Subscripts | `_{sub}` | `$a_1$` |
| Greek | `\alpha, \beta, ...` | `$\alpha + \beta$` |
| Trig Functions | `\sin, \cos, \tan` | `$\sin(x)$` |
| Square Root | `\sqrt[n]{expr}` | `$\sqrt[3]{8}$` |
| Integral | `\int_a^b` | `$\int_0^1 x dx$` |
| Sum | `\sum_{i}^{n}` | `$\sum_{i=1}^n i$` |

## Troubleshooting

### On Render (Web Display)
If LaTeX isn't rendering on the web page, MathJax might not be loading:
- Check browser console (F12) for errors
- Verify the MathJax CDN is accessible
- Check your question uses proper LaTeX syntax

### On PDF Generation
If PDF isn't generating, check:
1. Is pdflatex installed? Run `pdflatex --version`
2. Check application logs for detailed error messages
3. Is the question LaTeX valid? Test in an online LaTeX compiler
4. Do you have write permissions to the temp directory?

### Performance
- First PDF generation may take 2-5 seconds (LaTeX compilation)
- Subsequent PDFs should be faster (LaTeX caching)
- Large documents with many equations may take longer

## Migration Notes

**Old System (Matplotlib PNG rendering):**
- Fragile and dependency-heavy
- Inconsistent between web and PDF
- Poor quality math rendering
- Removed in favor of native LaTeX

**New System (pdflatex compilation):**
- Robust and professional
- Consistent across web and PDF
- High-quality mathematical output
- Single system dependency: pdflatex

---

## Support

For issues with LaTeX installation:
- **Windows**: Check MiKTeX documentation or install "Complete" edition
- **macOS**: Try `brew install --cask mactex` for full TeX Live
- **Linux**: Ensure you've installed `texlive-latex-extra` package

For authoring questions:
- Follow **LATEX_AUTHORING_GUIDELINES.md** strictly
- Test in an online LaTeX compiler before adding to questions
- Use simple, proven LaTeX patterns

