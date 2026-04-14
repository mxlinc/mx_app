"""LaTeX processing utilities for questions."""

import os
import re
import random
import subprocess
import tempfile
import shutil
import logging
from io import BytesIO

logger = logging.getLogger(__name__)


def escape_latex(text):
    """Escape special LaTeX characters in text (not in math mode)"""
    if not text:
        return text
    
    # Protect math mode expressions
    math_display = re.findall(r'\$\$[^\$]+\$\$', text)
    math_inline = re.findall(r'\$[^\$]+\$', text)
    
    # Replace with placeholders
    protected = text
    for i, match in enumerate(math_display):
        protected = protected.replace(match, f"__MATH_DISPLAY_{i}__", 1)
    for i, match in enumerate(math_inline):
        protected = protected.replace(match, f"__MATH_INLINE_{i}__", 1)
    
    # Escape special characters in text
    special_chars = {
        '\\': r'\textbackslash{}',
        '&': r'\&',
        '%': r'\%',
        '$': r'\$',
        '#': r'\#',
        '_': r'\_',
        '{': r'\{',
        '}': r'\}',
        '~': r'\textasciitilde{}',
        '^': r'\textasciicircum{}',
    }
    
    for char, replacement in special_chars.items():
        protected = protected.replace(char, replacement)
    
    # Restore math expressions
    for i, match in enumerate(math_display):
        protected = protected.replace(f"__MATH_DISPLAY_{i}__", match, 1)
    for i, match in enumerate(math_inline):
        protected = protected.replace(f"__MATH_INLINE_{i}__", match, 1)
    
    return protected


def preserve_newlines_latex(text):
    """Convert newlines to LaTeX line breaks while preserving math mode"""
    if not text:
        return text
    
    # Protect math mode expressions
    math_display = re.findall(r'\$\$[^\$]+\$\$', text)
    math_inline = re.findall(r'\$[^\$]+\$', text)
    
    # Replace with placeholders
    protected = text
    for i, match in enumerate(math_display):
        protected = protected.replace(match, f"__MATH_DISPLAY_{i}__", 1)
    for i, match in enumerate(math_inline):
        protected = protected.replace(match, f"__MATH_INLINE_{i}__", 1)
    
    # Replace newlines with LaTeX line breaks
    protected = protected.replace('\n', ' \\\\ ')
    
    # Restore math expressions
    for i, match in enumerate(math_display):
        protected = protected.replace(f"__MATH_DISPLAY_{i}__", match, 1)
    for i, match in enumerate(math_inline):
        protected = protected.replace(f"__MATH_INLINE_{i}__", match, 1)
    
    return protected


def generate_latex_template(question_data, question_id):
    """Generate LaTeX source for question"""
    question = question_data.get('question', {})
    
    stem_latex = question.get('stem', {}).get('latex', '')
    options = list(question.get('input', {}).get('options', []))
    correct_id = question.get('answer', {}).get('correct_option_id', '')
    should_shuffle = question.get('input', {}).get('shuffle', False)
    
    # Shuffle options if enabled
    if should_shuffle:
        random.shuffle(options)
    
    # Determine correct option letter by finding position after shuffle
    correct_letter = ''
    if correct_id and options:
        try:
            for idx, opt in enumerate(options):
                if opt.get('id') == correct_id:
                    correct_letter = chr(65 + idx)
                    break
        except:
            pass
    
    # Build LaTeX document
    latex_doc = r"""\documentclass[14pt,a4paper]{article}
\usepackage{mathpazo}
\usepackage{amsmath}
\usepackage{amssymb}
\usepackage{geometry}
\usepackage{graphicx}
\usepackage{xcolor}

\geometry{margin=0.5in}
\pagestyle{empty}

\begin{document}

\noindent
\textbf{Question ID:} """ + str(question_id) + r""" \\
\textbf{Topic:} """ + escape_latex(question_data.get('topic', 'N/A')) + r""" $|$ 
\textbf{Subtopic:} """ + escape_latex(question_data.get('subtopic', 'N/A')) + r""" $|$ 
\textbf{Level:} """ + escape_latex(question_data.get('level', 'N/A')) + r"""

\vspace{0.15in}

\noindent\hrulefill

\vspace{0.2in}

\noindent\textbf{\LARGE Question:}

\vspace{0.1in}

{\large
"""
    
    # Add stem
    latex_doc += r"\noindent " + preserve_newlines_latex(stem_latex) + "\n\n"
    
    # Add image if present
    from flask import current_app
    if question.get('image', {}).get('src'):
        try:
            image_path = question['image']['src']
            logger.info(f"Processing image for PDF. Original path: {image_path}")
            
            # Strip ./ prefix and static/ prefix
            if image_path.startswith('./'):
                image_path = image_path[2:]
            if image_path.startswith('static/'):
                image_path = image_path[7:]
            
            # Build absolute path to the image file
            full_path = os.path.join(current_app.static_folder, image_path)
            full_path = os.path.abspath(full_path)
            
            logger.info(f"Checking image at: {full_path}")
            logger.info(f"Image exists: {os.path.exists(full_path)}")
            
            if os.path.exists(full_path):
                # Convert Windows backslashes to forward slashes for LaTeX compatibility
                latex_image_path = full_path.replace('\\', '/')
                logger.info(f"Adding image to LaTeX: {latex_image_path}")
                latex_doc += r"\begin{center}" + "\n"
                latex_doc += r"\includegraphics[width=4in,height=3in,keepaspectratio]{" + latex_image_path + "}\n"
                latex_doc += r"\end{center}" + "\n\n"
            else:
                logger.warning(f"Image file not found at: {full_path}")
        except Exception as e:
            logger.error(f"Error adding image to LaTeX: {e}", exc_info=True)
    
    # Add options
    latex_doc += r"\noindent\textbf{\large Options:}" + "\n\n"
    latex_doc += r"\begin{enumerate}" + "\n"
    
    for idx, opt in enumerate(options, 1):
        opt_latex = opt.get('latex', '')
        option_letter = chr(64 + idx)
        latex_doc += f"\\item[{option_letter}.] {opt_latex}\n"
    
    latex_doc += r"\end{enumerate}" + "\n\n"
    
    # Add correct answer
    if correct_letter:
        latex_doc += r"\noindent\hrulefill" + "\n\n"
        latex_doc += r"\textbf{Correct Answer:} \textcolor{darkgreen}{\textbf{" + correct_letter + "}}\n"
    
    latex_doc += r"""}

\end{document}
"""
    
    return latex_doc


def compile_latex_to_pdf(latex_source):
    """Compile LaTeX source to PDF, return PDF buffer"""
    temp_dir = tempfile.mkdtemp()
    
    try:
        # Write LaTeX source to file
        tex_file = os.path.join(temp_dir, 'question.tex')
        with open(tex_file, 'w', encoding='utf-8') as f:
            f.write(latex_source)
        
        # Determine pdflatex executable path
        pdflatex_cmd = 'pdflatex'  # Default for Linux/Mac
        if os.name == 'nt':  # Windows
            windows_path = os.path.expanduser(r'~\AppData\Local\Programs\MiKTeX\miktex\bin\x64\pdflatex.exe')
            if os.path.exists(windows_path):
                pdflatex_cmd = windows_path
        
        # Compile with pdflatex
        result = subprocess.run(
            [pdflatex_cmd, '-interaction=nonstopmode', '-output-directory', temp_dir, tex_file],
            capture_output=True,
            timeout=30,
            text=True
        )
        
        # Check for PDF
        pdf_file = os.path.join(temp_dir, 'question.pdf')
        if not os.path.exists(pdf_file):
            error_msg = f"PDF compilation failed.\nStdout:\n{result.stdout}\n\nStderr:\n{result.stderr}"
            logger.error(error_msg)
            print(f"\n=== PDFLATEX ERROR ===\n{error_msg}\n=== END ERROR ===\n")
            raise Exception(f"PDF compilation failed. Check application logs for details.")
        
        # Read PDF into buffer
        with open(pdf_file, 'rb') as f:
            pdf_data = f.read()
        
        pdf_buffer = BytesIO(pdf_data)
        return pdf_buffer
    
    except subprocess.TimeoutExpired:
        logger.error("LaTeX compilation timed out")
        raise Exception("PDF generation timed out")
    except FileNotFoundError:
        logger.error("pdflatex not found. Please install LaTeX/texlive.")
        raise Exception("LaTeX compiler not installed. Please install texlive or MiKTeX.")
    finally:
        # Cleanup temp directory
        shutil.rmtree(temp_dir, ignore_errors=True)
