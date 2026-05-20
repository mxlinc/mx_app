"""Common question handling utilities."""

import os
import base64
import json as _json
import shutil
import subprocess
import latex2mathml.converter
from flask import current_app

# Resolve node executable once at import time (None if not on PATH)
_NODE_BIN = shutil.which('node')
_KATEX_SCRIPT = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'katex_render.js')


def _render_math(inner, display_mode):
    """Render a LaTeX math expression to HTML.

    Primary:  node katex_render.js via subprocess (full KaTeX — textcolor, textbf, etc.)
    Fallback: latex2mathml (used locally when node is not installed, or on timeout/error)

    Controlled by LATEX_RENDERER config: 'katex' (default) or 'mathml'.
    """
    renderer = current_app.config.get("LATEX_RENDERER", "katex")
    if renderer == "katex" and _NODE_BIN and os.path.exists(_KATEX_SCRIPT):
        try:
            payload = _json.dumps({'latex': inner, 'displayMode': display_mode})
            result = subprocess.run(
                [_NODE_BIN, _KATEX_SCRIPT],
                input=payload,
                capture_output=True,
                text=True,
                encoding='utf-8',
                timeout=10
            )
            if result.returncode == 0 and result.stdout:
                return result.stdout
            # Non-zero exit: KaTeX parse error — fall through to mathml
        except subprocess.TimeoutExpired:
            pass
        except Exception:
            pass
    # Fallback: latex2mathml (works without node; no textcolor/textbf support)
    mode = 'block' if display_mode else 'inline'
    try:
        return latex2mathml.converter.convert(inner, display=mode)
    except Exception:
        return inner  # last resort: raw LaTeX


def save_image_from_data_url(data_url, filename, subdir="qimage"):
    """Save base64 encoded image from data URL."""
    if not data_url:
        return None
    # data:image/png;base64,...
    header, encoded = data_url.split(",", 1)
    data = base64.b64decode(encoded)
    from config import QIMAGE_PATH
    os.makedirs(QIMAGE_PATH, exist_ok=True)
    file_path = os.path.join(QIMAGE_PATH, filename)
    with open(file_path, "wb") as f:
        f.write(data)
    return f"/qimage/{filename}"


def rename_image_file(old_filename, new_filename, subdir="qimage"):
    """
    Rename an image file in the static folder.
    
    Args:
        old_filename: Current filename (e.g., 'temp.png')
        new_filename: New filename (e.g., '75.png')
        subdir: Subdirectory within static (default 'qimage')
    
    Returns:
        New file path or None if rename failed
    """
    try:
        from config import QIMAGE_PATH
        old_path = os.path.join(QIMAGE_PATH, old_filename)
        new_path = os.path.join(QIMAGE_PATH, new_filename)
        if os.path.exists(old_path):
            os.rename(old_path, new_path)
            return f"/qimage/{new_filename}"
        return None
    except Exception as e:
        print(f"Failed to rename image: {e}")
        return None


def latex_to_html(latex):
    """Convert LaTeX text formatting to HTML while preserving math mode.
    
    Handles:
    - \\textbf{...} → <strong>...</strong>
    - \\textit{...} → <em>...</em>
    - \\underline{...} → <u>...</u>
    - \\texttt{...} → <code>...</code>
    - \\\\ (LaTeX line break) → <br>
    - Newlines → <br>
    - Preserves math delimiters: $...$, $$...$$, \\(...\\), \\[...\\]
    - Supports nested LaTeX commands and math within text formatting
    
    MathJax will render any remaining LaTeX math mode content.
    """
    if not isinstance(latex, str):
        return latex
    
    result = []
    i = 0
    length = len(latex)
    
    while i < length:
        # Preserve math mode content - don't convert LaTeX inside math
        if i < length - 1 and latex[i:i+2] == '$$':
            # Display math mode: $$ ... $$ → MathML block
            j = latex.find('$$', i + 2)
            if j != -1:
                inner = latex[i+2:j]
                try:
                    result.append(_render_math(inner, display_mode=True))
                except Exception:
                    result.append(latex[i:j+2])  # fallback: keep raw
                i = j + 2
                continue
            else:
                result.append('$$')
                i += 2
        elif i < length - 1 and latex[i:i+2] == '\\$':
            # Escaped dollar sign (literal currency symbol, e.g. \$50)
            result.append('$')
            i += 2
        elif latex[i] == '$':
            # Inline math mode: $ ... $ → MathML inline
            j = latex.find('$', i + 1)
            if j != -1:
                inner = latex[i+1:j]
                try:
                    result.append(_render_math(inner, display_mode=False))
                except Exception:
                    result.append(latex[i:j+1])  # fallback: keep raw
                i = j + 1
                continue
            else:
                result.append('$')
                i += 1
        elif i < length - 1 and latex[i:i+2] == '\\[':
            # Display math mode: \[ ... \]
            j = latex.find('\\]', i + 2)
            if j != -1:
                result.append(latex[i:j+2])
                i = j + 2
                continue
            else:
                result.append('\\[')
                i += 2
        elif i < length - 1 and latex[i:i+2] == '\\(':
            # Inline math mode: \( ... \)
            j = latex.find('\\)', i + 2)
            if j != -1:
                result.append(latex[i:j+2])
                i = j + 2
                continue
            else:
                result.append('\\(')
                i += 2
        # Handle LaTeX text formatting commands
        elif i < length - 7 and latex[i:i+8] == '\\textbf{':
            # Extract content of \textbf{...}
            content, end_pos = _extract_latex_arg(latex, i + 8)
            if content is not None:
                converted_content = latex_to_html(content)  # Recursively handle nested formatting
                result.append(f'<strong>{converted_content}</strong>')
                i = end_pos
                continue
            else:
                result.append(latex[i])
                i += 1
        elif i < length - 7 and latex[i:i+8] == '\\textit{':
            # Extract content of \textit{...}
            content, end_pos = _extract_latex_arg(latex, i + 8)
            if content is not None:
                converted_content = latex_to_html(content)  # Recursively handle nested formatting
                result.append(f'<em>{converted_content}</em>')
                i = end_pos
                continue
            else:
                result.append(latex[i])
                i += 1
        elif i < length - 10 and latex[i:i+11] == '\\underline{':
            # Extract content of \underline{...}
            content, end_pos = _extract_latex_arg(latex, i + 11)
            if content is not None:
                converted_content = latex_to_html(content)  # Recursively handle nested formatting
                result.append(f'<u>{converted_content}</u>')
                i = end_pos
                continue
            else:
                result.append(latex[i])
                i += 1
        elif i < length - 7 and latex[i:i+8] == '\\texttt{':
            # Extract content of \texttt{...}
            content, end_pos = _extract_latex_arg(latex, i + 8)
            if content is not None:
                converted_content = latex_to_html(content)  # Recursively handle nested formatting
                result.append(f'<code>{converted_content}</code>')
                i = end_pos
                continue
            else:
                result.append(latex[i])
                i += 1
        # Handle line breaks
        elif i < length - 1 and latex[i:i+2] == '\\\\':
            # LaTeX line break (two backslashes: \\)
            result.append('<br>')
            i += 2
        elif latex[i] == '\n':
            # Actual newline character (user pressed Enter)
            result.append('<br>')
            i += 1
        else:
            result.append(latex[i])
            i += 1
    
    return ''.join(result)


def _extract_latex_arg(text, start_pos):
    """Extract the argument of a LaTeX command, handling nested braces.
    
    Args:
        text: The full LaTeX string
        start_pos: Position right after the opening brace
    
    Returns:
        Tuple of (content, end_pos) or (None, start_pos) if no matching brace found
    """
    if start_pos >= len(text):
        return None, start_pos
    
    depth = 1
    i = start_pos
    
    while i < len(text) and depth > 0:
        if text[i] == '{':
            depth += 1
        elif text[i] == '}':
            depth -= 1
        i += 1
    
    if depth == 0:
        # Found matching closing brace
        content = text[start_pos:i-1]
        return content, i
    else:
        # No matching brace found
        return None, start_pos


def generate_question_html(question):
    """Convert LaTeX fields to HTML in a question dict.

    Single source of truth for LaTeX→HTML conversion. Idempotent — fields
    that already have an ``html`` value are left unchanged, so it is safe to
    call at both save-time and cache-build-time without redundant work.

    Makes shallow copies of modified sub-dicts; the caller's original is not
    mutated. Returns the (possibly new) top-level dict.

    Covers: stem, stem.feedback, input.options (MCQ/MR), input.blanks (FILL).
    No Flask dependency — safe to import from standalone scripts.
    """
    if not isinstance(question, dict):
        return question

    question = dict(question)

    # ── Stem ──────────────────────────────────────────────────────────────
    if 'stem' in question:
        if isinstance(question['stem'], dict):
            question['stem'] = dict(question['stem'])
        else:
            question['stem'] = {'latex': str(question['stem']), 'html': ''}

        stem = question['stem']
        if 'latex' in stem and not stem.get('html'):
            stem['html'] = latex_to_html(stem['latex'])
        elif 'html' not in stem:
            stem['html'] = ''

        # Feedback block inside stem
        if 'feedback' in stem and isinstance(stem['feedback'], dict):
            fb = dict(stem['feedback'])
            if 'latex' in fb and not fb.get('html'):
                fb['html'] = latex_to_html(fb['latex'])
            elif 'html' not in fb:
                fb['html'] = ''
            stem['feedback'] = fb

    # ── Options + Blanks (copy input sub-dict once) ───────────────────────
    if 'input' in question:
        inp = dict(question['input'])

        # Options (MCQ / MR)
        if 'options' in inp:
            options_list = []
            for opt in inp['options']:
                opt = dict(opt) if isinstance(opt, dict) else opt
                if isinstance(opt, dict):
                    if 'latex' in opt and not opt.get('html'):
                        opt['html'] = latex_to_html(opt['latex'])
                    elif 'html' not in opt:
                        opt['html'] = ''
                options_list.append(opt)
            inp['options'] = options_list

        # Blanks (FILL)
        if 'blanks' in inp:
            blanks_list = []
            for blank in inp['blanks']:
                blank = dict(blank) if isinstance(blank, dict) else blank
                if isinstance(blank, dict) and 'input_label' in blank:
                    if isinstance(blank['input_label'], dict):
                        lbl = dict(blank['input_label'])
                    else:
                        lbl = {'latex': str(blank['input_label']), 'html': ''}
                    if 'latex' in lbl and not lbl.get('html'):
                        lbl['html'] = latex_to_html(lbl['latex'])
                    elif 'html' not in lbl:
                        lbl['html'] = ''
                    blank['input_label'] = lbl
                if isinstance(blank, dict) and 'label_after' in blank:
                    la = blank['label_after']
                    if isinstance(la, dict):
                        la = dict(la)
                    else:
                        la = {'latex': str(la), 'html': ''}
                    if 'latex' in la and not la.get('html'):
                        la['html'] = latex_to_html(la['latex'])
                    elif 'html' not in la:
                        la['html'] = ''
                    blank['label_after'] = la
                blanks_list.append(blank)
            inp['blanks'] = blanks_list

        question['input'] = inp

    return question
