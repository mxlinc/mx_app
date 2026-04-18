"""Common question handling utilities."""

import os
import base64
from flask import current_app


def save_image_from_data_url(data_url, filename, subdir="qimage"):
    """Save base64 encoded image from data URL."""
    if not data_url:
        return None
    # data:image/png;base64,...
    header, encoded = data_url.split(",", 1)
    data = base64.b64decode(encoded)
    upload_dir = os.path.join(current_app.static_folder, subdir)
    os.makedirs(upload_dir, exist_ok=True)
    file_path = os.path.join(upload_dir, filename)
    with open(file_path, "wb") as f:
        f.write(data)
    return f"./static/{subdir}/{filename}"


def latex_to_html(latex):
    """Convert LaTeX to HTML by preserving LaTeX in math spans."""
    if not isinstance(latex, str):
        return latex
    # Normalize escaped backslashes
    normalized = latex.replace('\\\\', '\\')
    # Just wrap in math span - preserve LaTeX as-is for client-side rendering
    return f'<span class="math">{normalized}</span>'


def generate_question_html(question):
    """Generate HTML for question from LaTeX."""
    if not isinstance(question, dict):
        return question
    
    # Make a copy to avoid mutating input
    question = dict(question)
    
    # Generate HTML for stem
    if 'stem' in question:
        if isinstance(question['stem'], dict):
            question['stem'] = dict(question['stem'])
        else:
            question['stem'] = {'latex': str(question['stem']), 'html': ''}
        
        if 'latex' in question['stem']:
            question['stem']['html'] = latex_to_html(question['stem']['latex'])
        elif 'html' not in question['stem']:
            question['stem']['html'] = question['stem'].get('latex', '')
        
        # Generate HTML for feedback if present
        if 'feedback' in question['stem'] and isinstance(question['stem']['feedback'], dict):
            feedback_copy = dict(question['stem']['feedback'])
            if 'latex' in feedback_copy:
                feedback_copy['html'] = latex_to_html(feedback_copy['latex'])
            elif 'html' not in feedback_copy:
                feedback_copy['html'] = feedback_copy.get('latex', '')
            question['stem']['feedback'] = feedback_copy
    
    # Generate HTML for options
    if 'input' in question and 'options' in question['input']:
        options_list = []
        for opt in question['input']['options']:
            opt_copy = dict(opt) if isinstance(opt, dict) else opt
            if 'latex' in opt_copy:
                opt_copy['html'] = latex_to_html(opt_copy['latex'])
            elif 'html' not in opt_copy:
                opt_copy['html'] = opt_copy.get('latex', '')
            options_list.append(opt_copy)
        question['input']['options'] = options_list
    
    # Generate HTML for blanks (FILL questions)
    if 'input' in question and 'blanks' in question['input']:
        blanks_list = []
        for blank in question['input']['blanks']:
            blank_copy = dict(blank) if isinstance(blank, dict) else blank
            if 'input_label' in blank_copy:
                if isinstance(blank_copy['input_label'], dict):
                    blank_copy['input_label'] = dict(blank_copy['input_label'])
                else:
                    blank_copy['input_label'] = {'latex': str(blank_copy['input_label']), 'html': ''}
                
                if 'latex' in blank_copy['input_label']:
                    blank_copy['input_label']['html'] = latex_to_html(blank_copy['input_label']['latex'])
                elif 'html' not in blank_copy['input_label']:
                    blank_copy['input_label']['html'] = blank_copy['input_label'].get('latex', '')
            blanks_list.append(blank_copy)
        question['input']['blanks'] = blanks_list
    
    return question
