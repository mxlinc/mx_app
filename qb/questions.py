"""Question CRUD routes — all /question/ endpoints."""

import copy
import logging

from flask import render_template, request, jsonify, send_file, redirect, url_for
from flask_login import login_required

from db import db
from models import QBank, Quiz
from qb.routes import question_bp, qb_bp, get_handler
from qb.handlers.common import latex_to_html
from qb.db_utils import create_question_safely

logger = logging.getLogger(__name__)


# ==================== SHARED HELPERS ====================

def _quizzes_using_question(question_id: int) -> list:
    """Return Quiz objects whose question_ids string contains question_id."""
    candidates = Quiz.query.filter(
        Quiz.question_ids.like(f'%{question_id}%')
    ).all()
    # Narrow out false positives from the LIKE (e.g. id=1 matching ids '10,11')
    return [
        qz for qz in candidates
        if str(question_id) in [i.strip() for i in (qz.question_ids or '').split(',')]
    ]


# ==================== BUILDER ==================== #

@question_bp.route("/builder", methods=["GET"])
@login_required
def builder_page():
    return render_template("quiz_builder.html")


@question_bp.route("/edit/<int:question_id>", methods=["GET"])
@login_required
def edit_question_redirect(question_id):
    """Redirect to builder for the given question."""
    q = QBank.query.get(question_id)
    if not q:
        return jsonify({"ok": False, "errors": ["Question not found"]}), 404
    question_type = q.type.lower() if q.type else 'mcq'
    return redirect(f"/question/builder?id={question_id}&type={question_type}")


@question_bp.route("/new", methods=["GET"])
@login_required
def new_question():
    return redirect("/question/builder")


# ==================== PREVIEW / SAVE ==================== #

@question_bp.route("/api/preview", methods=["POST"])
@login_required
def preview_question():
    data = request.get_json()
    question_type = data.get('type', 'mcq').lower()
    handler = get_handler(question_type)
    if not handler:
        return jsonify({"ok": False, "errors": [f"Unknown question type: {question_type}"]}), 400
    question = handler.prepare_html(data['question'])
    if data.get('image_data_url'):
        question['image'] = question.get('image', {})
        question['image']['src'] = data['image_data_url']
    return jsonify({"ok": True, "question": question, "errors": []})


@question_bp.route("/api/save", methods=["POST"])
@login_required
def save_question():
    data = request.get_json()
    question_type = data.get('type', 'mcq').lower()
    data['type'] = question_type
    handler = get_handler(question_type)
    if not handler:
        return jsonify({"ok": False, "errors": [f"Unknown question type: {question_type}"]}), 400
    q, error = handler.save_question(data)
    if error:
        return jsonify({"ok": False, "errors": [error]}), 400
    # Mark question as needing quiz re-sync (admin triggers this manually)
    q.sync_required = True
    db.session.commit()
    return jsonify({"ok": True, "question_id": q.id, "message": "Question saved.", "question": q.json})


# ==================== DISPLAY ==================== #

@question_bp.route("/display/<int:question_id>", methods=["GET"])
@login_required
def display_question(question_id):
    q = QBank.query.get(question_id)
    if not q:
        return "Question not found", 404
    return render_template("quiz_display.html", question_id=question_id)


@question_bp.route("/api/display/<int:question_id>", methods=["GET"])
@login_required
def get_display_question(question_id):
    q = QBank.query.get(question_id)
    if not q:
        return jsonify({"ok": False, "errors": ["Question not found"]}), 404
    handler = get_handler(q.type.lower() if q.type else 'mcq')
    if not handler:
        return jsonify({"ok": False, "errors": [f"Unknown question type: {q.type}"]}), 400
    question = handler.prepare_html(q.json)
    ordered_question = handler.order_json(question)
    return jsonify({
        "ok": True,
        "question": ordered_question,
        "question_id": q.id,
        "type": q.type.lower() if q.type else 'mcq',
        "topic": q.topic,
        "subtopic": q.subtopic,
        "level": q.level
    })


@question_bp.route("/api/delete/<int:question_id>", methods=["POST"])
@login_required
def delete_question(question_id):
    """Delete a question and its associated image file from disk."""
    import os
    from config import QIMAGE_PATH

    q = QBank.query.get(question_id)
    if not q:
        return jsonify({"ok": False, "error": "Question not found"}), 404

    blocking = _quizzes_using_question(question_id)
    if blocking:
        names = ', '.join(f"{qz.quiz_code} ({qz.title})" for qz in blocking)
        return jsonify({"ok": False,
                        "error": f"Cannot delete — used in {len(blocking)} quiz(zes): {names}"}), 400

    image_src = (q.json or {}).get("image", {}).get("src") if isinstance(q.json, dict) else None
    if image_src:
        if image_src.startswith("/qimage/"):
            img_path = os.path.join(QIMAGE_PATH, image_src[len("/qimage/"):])
        elif image_src.startswith("/static/qimage/"):
            img_path = os.path.join(QIMAGE_PATH, image_src[len("/static/qimage/"):])
        else:
            img_path = None
        if img_path and os.path.exists(img_path):
            try:
                os.remove(img_path)
            except Exception:
                pass

    db.session.delete(q)
    db.session.commit()
    return jsonify({"ok": True})


@question_bp.route("/api/next-id/<int:question_id>", methods=["GET"])
@login_required
def get_next_question_id(question_id):
    """Get the next unused question ID (not in any quiz); wraps to first unused if at end."""
    try:
        used_ids = set()
        for qz in Quiz.query.filter(Quiz.question_ids.isnot(None)).all():
            for i in qz.question_ids.split(','):
                if i.strip().isdigit():
                    used_ids.add(int(i.strip()))

        base = QBank.query if not used_ids else QBank.query.filter(~QBank.id.in_(used_ids))

        next_q = base.filter(QBank.id > question_id).order_by(QBank.id).first()
        if next_q:
            return jsonify({"ok": True, "next_id": next_q.id})
        # Wrap around to the first unused question
        first_q = base.order_by(QBank.id).first()
        if first_q:
            return jsonify({"ok": True, "next_id": first_q.id})
        return jsonify({"ok": False, "all_used": True, "error": "No unused questions left"}), 200
    except Exception as e:
        logger.exception(e)
        return jsonify({"ok": False, "error": str(e)}), 500


# ==================== SHEET ==================== #

@question_bp.route("/generate-sheet", methods=["GET"])
@login_required
def generate_sheet():
    """Generate a printable HTML sheet for selected question IDs."""
    ids_param = request.args.get('ids', '')
    if not ids_param:
        return "No question IDs provided", 400

    try:
        ids = [int(i.strip()) for i in ids_param.split(',') if i.strip().isdigit()]
    except ValueError:
        return "Invalid question IDs", 400

    if not ids:
        return "No valid question IDs", 400

    questions_data = []
    for qid in ids:
        q = QBank.query.get(qid)
        if not q:
            continue
        handler = get_handler(q.type.lower() if q.type else 'mcq')
        if not handler:
            continue
        question = handler.prepare_html(q.json)
        questions_data.append({'id': qid, 'type': q.type.lower(), 'question': question})

    html = _render_sheet(questions_data)
    from flask import Response
    return Response(
        html,
        mimetype='text/html',
        headers={'Content-Disposition': 'attachment; filename=questions.html'}
    )


def _render_sheet(questions_data):
    """Build a self-contained HTML sheet string."""
    import re
    import base64
    import os
    import random
    from config import QIMAGE_PATH

    OPTION_LABELS = ['A', 'B', 'C', 'D', 'E', 'F']

    def clean_html(s):
        """Strip leading/trailing <br> tags and whitespace."""
        s = (s or '').strip()
        s = re.sub(r'^(\s*<br\s*/?>)+', '', s).strip()
        s = re.sub(r'(<br\s*/?>\s*)+$', '', s).strip()
        return s

    def embed_image(src):
        """Return base64 data URI so the image works in a downloaded file."""
        try:
            if src.startswith('/qimage/'):
                path = os.path.join(QIMAGE_PATH, src[len('/qimage/'):])
            elif src.startswith('/static/qimage/'):
                path = os.path.join(QIMAGE_PATH, src[len('/static/qimage/'):])
            else:
                return src
            if os.path.exists(path):
                with open(path, 'rb') as f:
                    data = base64.b64encode(f.read()).decode()
                return f'data:image/png;base64,{data}'
        except Exception:
            pass
        return src

    def get_stem(q):
        stem = q.get('stem', '')
        raw = (stem.get('html') or stem.get('latex', '')) if isinstance(stem, dict) else str(stem)
        return clean_html(raw)

    def get_options(q):
        """Return list of (label, id, text), shuffled if flagged."""
        inp = q.get('input', {})
        opts = list(inp.get('options', []))
        if inp.get('shuffle', False):
            random.shuffle(opts)
        result = []
        for i, opt in enumerate(opts):
            label = OPTION_LABELS[i] if i < len(OPTION_LABELS) else str(i + 1)
            text = ''
            if isinstance(opt, dict):
                text = clean_html(opt.get('html') or opt.get('text') or opt.get('latex', ''))
            else:
                text = clean_html(str(opt))
            result.append((label, opt.get('id', str(i + 1)) if isinstance(opt, dict) else str(i + 1), text))
        return result

    def options_html(q, qtype):
        parts = []
        if qtype in ('mcq', 'mr'):
            for label, _, text in get_options(q):
                parts.append(f'<div class="option"><span class="opt-label">{label}.</span> {text}</div>')
        elif qtype == 'fill':
            blanks = q.get('input', {}).get('blanks', [])
            for blank in blanks:
                label_html = label_after_html = ''
                if isinstance(blank, dict):
                    il = blank.get('input_label', {})
                    label_html = clean_html((il.get('html') or il.get('latex', '')) if isinstance(il, dict) else str(il))
                    la = blank.get('label_after', {})
                    label_after_html = clean_html((la.get('html') or la.get('latex', '')) if isinstance(la, dict) else str(la))
                parts.append(
                    f'<div class="fill-row">{label_html}'
                    f'<span class="blank-box"></span>{label_after_html}</div>'
                )
        return '\n'.join(parts)

    def answer_html(q, qtype):
        answer = q.get('answer', {})
        if qtype in ('mcq', 'mr'):
            # Support both singular and plural correct_option_id(s)
            cid_raw = answer.get('correct_option_ids') or answer.get('correct_option_id')
            if cid_raw is None:
                return '\u2014'
            correct_ids = set(str(x) for x in (cid_raw if isinstance(cid_raw, list) else [cid_raw]))
            parts = []
            for label, oid, text in get_options(q):
                if str(oid) in correct_ids:
                    parts.append(f'<strong>{label}.</strong> {text}')
            return ' / '.join(parts) if parts else '\u2014'

        elif qtype == 'fill':
            blanks = q.get('input', {}).get('blanks', [])
            blank_map = {b['id']: b for b in blanks if isinstance(b, dict) and 'id' in b}
            correct = answer.get('correct', [])
            parts = []
            for item in correct:
                if not isinstance(item, dict):
                    parts.append(str(item))
                    continue
                bid = item.get('blank_id', '')
                blank_def = blank_map.get(bid, {})
                # Build label from latex (cleaner than stripping KaTeX HTML)
                il = blank_def.get('input_label', {})
                la = blank_def.get('label_after', {})
                label_tex = (il.get('latex', '') if isinstance(il, dict) else str(il)).strip()
                after_tex = (la.get('latex', '') if isinstance(la, dict) else str(la)).strip()
                context = ' '.join(p for p in [label_tex, after_tex] if p) or bid
                # Get answer value
                rtype = item.get('response_type', '')
                if rtype == 'numeric':
                    vals = item.get('accepted_numeric', [])
                    val_str = ', '.join(str(v) for v in vals)
                elif rtype == 'fraction':
                    val_str = f"{item.get('numerator', '')} / {item.get('denominator', '')}"
                else:
                    vals = item.get('accepted_values', [])
                    val_str = ', '.join(str(v) for v in vals) if vals else '\u2014'
                parts.append(f'{context} : <strong>{val_str}</strong>')
            return ' &nbsp;|&nbsp; '.join(parts) if parts else '\u2014'

        return '\u2014'

    # Build blocks
    q_blocks = []
    ans_blocks = []
    for seq, item in enumerate(questions_data, start=1):
        qid = item['id']
        qtype = item['type']
        q = item['question']

        img_html = ''
        if q.get('image', {}).get('src'):
            src = embed_image(q['image']['src'])
            img_html = f'<div class="q-image"><img src="{src}" alt=""></div>'

        HANDLE = """
        <div class="insert-handle">
            <div class="insert-line"></div>
            <div class="insert-btns">
                <button class="ins-btn" onclick="insertSpacer(this)">+ Space</button>
                <button class="ins-btn ins-pb" onclick="insertPageBreak(this)">&#8676; Page Break</button>
            </div>
        </div>"""

        # Insert handle between questions (not before the first one)
        prefix = '' if seq == 1 else HANDLE

        q_blocks.append(prefix + f"""
        <div class="question-block">
            <div class="q-row">
                <div class="q-label">
                    <span class="q-num">Q-{seq}</span>
                    <span class="q-id">[{str(qid).zfill(4)}]</span>
                </div>
                <div class="q-content" contenteditable="true">
                    <div class="q-stem">{get_stem(q)}</div>
                    {img_html}
                    <div class="q-options">{options_html(q, qtype)}</div>
                </div>
            </div>
        </div>""")

        ans_blocks.append(
            f'<div class="ans-row">'
            f'<span class="ans-num">Answer-{seq}</span> '
            f'<span class="ans-val" contenteditable="true">{answer_html(q, qtype)}</span></div>'
        )

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>Question Sheet</title>
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/katex@0.16.9/dist/katex.min.css">
<script defer src="https://cdn.jsdelivr.net/npm/katex@0.16.9/dist/katex.min.js"></script>
<script defer src="https://cdn.jsdelivr.net/npm/katex@0.16.9/dist/contrib/auto-render.min.js"
    onload="renderMathInElement(document.body, {{delimiters:[{{left:'$',right:'$',display:false}},{{left:'\\\\(',right:'\\\\)',display:false}},{{left:'\\\\[',right:'\\\\]',display:true}}]}})"></script>
<style>
  body {{ font-family: 'Georgia', serif; max-width: 820px; margin: 40px auto; padding: 0 24px; color: #111; line-height: 1.7; }}
  /* Toolbar */
  #toolbar {{ position: fixed; top: 0; left: 0; right: 0; background: #1F6FAE; color: #fff; padding: 8px 24px; display: flex; align-items: center; gap: 14px; font-family: sans-serif; font-size: 0.9rem; z-index: 999; box-shadow: 0 2px 6px rgba(0,0,0,.3); }}
  #toolbar button {{ background: #fff; color: #1F6FAE; border: none; border-radius: 4px; padding: 6px 16px; font-weight: 700; cursor: pointer; font-size: 0.88rem; }}
  #toolbar button:hover {{ background: #dceeff; }}
  #toolbar span {{ opacity: .8; font-size: 0.82rem; }}
  body {{ padding-top: 56px; }}
  /* Editable regions */
  [contenteditable] {{ outline: none; border-radius: 3px; }}
  [contenteditable]:hover {{ background: #f0f7ff; }}
  [contenteditable]:focus {{ background: #e8f2ff; box-shadow: inset 0 0 0 1px #1F6FAE; }}
  /* Insert handles */
  .insert-handle {{ display: flex; align-items: center; gap: 10px; margin: 4px 0; opacity: 0; transition: opacity .15s; }}
  .insert-handle:hover {{ opacity: 1; }}
  .insert-line {{ flex: 1; border-top: 1px dashed #b0c8e0; }}
  .insert-btns {{ display: flex; gap: 6px; flex-shrink: 0; }}
  .ins-btn {{ font-size: 0.74rem; padding: 2px 10px; border: 1px solid #1F6FAE; border-radius: 3px; background: #fff; color: #1F6FAE; cursor: pointer; font-family: sans-serif; }}
  .ins-btn:hover {{ background: #dceeff; }}
  .ins-pb {{ border-color: #b44; color: #b44; }}
  .ins-pb:hover {{ background: #ffeaea; }}
  /* Spacer */
  .sheet-spacer {{ position: relative; min-height: 60px; background: repeating-linear-gradient(0deg,transparent,transparent 23px,#eef4fb 23px,#eef4fb 24px); border-radius: 3px; margin: 2px 0; resize: vertical; overflow: hidden; }}
  .sheet-spacer .rm {{ position: absolute; top: 3px; right: 6px; background: none; border: none; color: #bbb; cursor: pointer; font-size: 0.78rem; font-family: sans-serif; }}
  .sheet-spacer .rm:hover {{ color: #c00; }}
  /* Page break */
  .sheet-pb {{ border: 2px dashed #1F6FAE; border-radius: 3px; text-align: center; padding: 3px 0; margin: 4px 0; font-family: sans-serif; font-size: 0.76rem; color: #1F6FAE; position: relative; }}
  .sheet-pb .rm {{ position: absolute; right: 8px; top: 50%; transform: translateY(-50%); background: none; border: none; color: #1F6FAE; cursor: pointer; font-size: 0.88rem; }}
  .question-block {{ margin-bottom: 44px; }}
  .q-row {{ display: grid; grid-template-columns: 68px 1fr; gap: 0 4px; }}
  .q-label {{ padding-top: 2px; text-align: right; padding-right: 10px; }}
  .q-num {{ font-size: 1rem; font-weight: 700; display: block; }}
  .q-id {{ font-size: 0.68rem; color: #aaa; display: block; }}
  .q-stem {{ font-size: 1rem; margin-bottom: 8px; }}
  .q-image img {{ max-width: 50%; margin-bottom: 8px; }}
  .option {{ margin: 4px 0; }}
  .opt-label {{ font-weight: 600; min-width: 22px; display: inline-block; }}
  .fill-row {{ display: flex; align-items: baseline; gap: 6px; margin: 6px 0; }}
  .blank-box {{ display: inline-block; width: 110px; border-bottom: 1.5px solid #333; margin: 0 4px; }}
  hr.divider {{ border: none; border-top: 2px solid #ccc; margin: 40px 0; }}
  .answers-section h2 {{ font-size: 1rem; font-weight: 700; margin-bottom: 14px; }}
  .ans-row {{ margin: 6px 0; font-size: 0.92rem; }}
  .ans-num {{ font-weight: 700; margin-right: 10px; }}
  .ans-val {{ color: #1a5c1a; }}
  #sheet-footer {{ text-align: center; font-size: 0.72rem; color: #bbb; border-top: 1px solid #eee; padding: 12px 0 4px; margin-top: 32px; font-family: sans-serif; }}
  @media print {{
    #toolbar, .insert-handle, .rm {{ display: none !important; }}
    body {{ margin: 20px; padding-top: 0; }}
    [contenteditable]:hover, [contenteditable]:focus {{ background: none; box-shadow: none; }}
    .sheet-pb {{ break-before: page; border: none; color: transparent; padding: 0; margin: 0; height: 0; }}
    .sheet-spacer {{ background: none; }}
    #sheet-footer {{ position: fixed; bottom: 0; left: 0; right: 0; margin: 0; border-top: 1px solid #ddd; padding: 4px 0; }}
  }}
</style>
</head>
<body>
<div id="toolbar">
  <button onclick="window.print()">&#128438; Print / Save PDF</button>
  <span>Hover between questions for insert options &nbsp;&bull;&nbsp; Click text to edit &nbsp;&bull;&nbsp; Print when ready</span>
</div>
<div id="sheet-footer">MX Learning Inc.</div>
{''.join(q_blocks)}
        <div class="insert-handle">
            <div class="insert-line"></div>
            <div class="insert-btns">
                <button class="ins-btn" onclick="insertSpacer(this)">+ Space</button>
                <button class="ins-btn ins-pb" onclick="insertPageBreak(this)">&#8676; Page Break</button>
            </div>
        </div>
<hr class="divider">
<div class="answers-section">
  <h2>Answers</h2>
  {''.join(ans_blocks)}
</div>
<script>
function insertSpacer(btn) {{
  var h = btn.closest('.insert-handle');
  var el = document.createElement('div');
  el.className = 'sheet-spacer';
  var rm = document.createElement('button');
  rm.className = 'rm';
  rm.textContent = '\u2715 remove';
  rm.onclick = function() {{ el.remove(); }};
  el.appendChild(rm);
  h.insertAdjacentElement('afterend', el);
}}
function insertPageBreak(btn) {{
  var h = btn.closest('.insert-handle');
  var el = document.createElement('div');
  el.className = 'sheet-pb';
  el.appendChild(document.createTextNode('\u21b5 Page Break\u00a0'));
  var rm = document.createElement('button');
  rm.className = 'rm';
  rm.textContent = '\u2715';
  rm.onclick = function() {{ el.remove(); }};
  el.appendChild(rm);
  h.insertAdjacentElement('afterend', el);
}}
</script>
</body>
</html>"""


# ==================== EXPORT ==================== #

def _strip_for_export(obj):
    """Recursively remove 'html' and 'image' keys; strip residual HTML tags from strings."""
    import re
    _TAG = re.compile(r'<[^>]+')
    if isinstance(obj, dict):
        return {k: _strip_for_export(v) for k, v in obj.items() if k not in ('html', 'image')}
    if isinstance(obj, list):
        return [_strip_for_export(i) for i in obj]
    if isinstance(obj, str):
        return _TAG.sub('', obj).strip()
    return obj


@question_bp.route("/api/export", methods=["GET"])
@login_required
def export_questions():
    """Download all questions as clean JSON (LaTeX only, no HTML, no images)."""
    import io
    import json as _json
    questions = QBank.query.order_by(QBank.id).all()
    out = []
    for q in questions:
        cleaned = _strip_for_export(q.json or {})
        cleaned.pop('id', None)   # remove embedded DB id; leave option/blank ids intact
        out.append({
            "type": q.type,
            "topic": q.topic,
            "subtopic": q.subtopic,
            "level": q.level,
            "question": cleaned,
        })
    payload = _json.dumps(out, ensure_ascii=False, indent=2)
    buf = io.BytesIO(payload.encode('utf-8'))
    return send_file(
        buf,
        mimetype='application/json',
        as_attachment=True,
        download_name='questions_export.json',
    )


def generate_review_html(*, student_name, quiz_title, score, completed_at, total, questions):
    """Return a self-contained HTML page showing incorrect answers for admin review.

    Parameters
    ----------
    student_name : str
    quiz_title   : str
    score        : str   e.g. "7 of 10"
    completed_at : datetime | None
    total        : int   total questions attempted
    questions    : list of dicts with keys:
                   sequence, question (JSON), qtype, correct_answer, user_answer
    """
    import re
    import base64
    import os
    from config import QIMAGE_PATH

    OPTION_LABELS = ['A', 'B', 'C', 'D', 'E', 'F']

    def clean_html(s):
        s = (s or '').strip()
        s = re.sub(r'^(\s*<br\s*/?>)+', '', s).strip()
        s = re.sub(r'(<br\s*/?>\s*)+$', '', s).strip()
        return s

    def embed_image(src):
        try:
            if src.startswith('/qimage/'):
                path = os.path.join(QIMAGE_PATH, src[len('/qimage/'):])
            elif src.startswith('/static/qimage/'):
                path = os.path.join(QIMAGE_PATH, src[len('/static/qimage/'):])
            else:
                return src
            if os.path.exists(path):
                with open(path, 'rb') as f:
                    data = base64.b64encode(f.read()).decode()
                return f'data:image/png;base64,{data}'
        except Exception:
            pass
        return src

    def get_stem(q):
        stem = q.get('stem', '')
        raw = (stem.get('html') or stem.get('latex', '')) if isinstance(stem, dict) else str(stem)
        return clean_html(raw)

    def options_html(q, qtype):
        parts = []
        if qtype in ('mcq', 'mr'):
            opts = q.get('input', {}).get('options', [])
            for i, opt in enumerate(opts):
                label = OPTION_LABELS[i] if i < len(OPTION_LABELS) else str(i + 1)
                text = ''
                if isinstance(opt, dict):
                    text = clean_html(opt.get('html') or opt.get('text') or opt.get('latex', ''))
                else:
                    text = clean_html(str(opt))
                parts.append(f'<div class="option"><span class="opt-label">{label}.</span> {text}</div>')
        elif qtype == 'fill':
            blanks = q.get('input', {}).get('blanks', [])
            for blank in blanks:
                if isinstance(blank, dict):
                    il = blank.get('input_label', {})
                    la = blank.get('label_after', {})
                    lbl = clean_html((il.get('html') or il.get('latex', '')) if isinstance(il, dict) else str(il))
                    aft = clean_html((la.get('html') or la.get('latex', '')) if isinstance(la, dict) else str(la))
                    parts.append(f'<div class="fill-row">{lbl}<span class="blank-box"></span>{aft}</div>')
        return '\n'.join(parts)

    # Build question blocks
    blocks = []
    for item in questions:
        seq   = item['sequence']
        q     = item['question'] or {}
        qtype = item['qtype']
        corr  = item['correct_answer']
        user  = item['user_answer']

        img_html = ''
        if q.get('image', {}).get('src'):
            src = embed_image(q['image']['src'])
            img_html = f'<div class="q-image"><img src="{src}" alt=""></div>'

        blocks.append(f"""
        <div class="review-block">
          <div class="q-row">
            <div class="q-label">
              <span class="q-num">Q-{seq}</span>
            </div>
            <div class="q-content">
              <div class="q-stem">{get_stem(q)}</div>
              {img_html}
              <div class="q-options">{options_html(q, qtype)}</div>
              <div class="answer-row correct-row">
                <span class="ans-icon">&#10003;</span>
                <span class="ans-label">Correct:</span>
                <span class="ans-val">{corr}</span>
              </div>
              <div class="answer-row student-row">
                <span class="ans-icon">&#10007;</span>
                <span class="ans-label">Student:</span>
                <span class="ans-val">{user}</span>
              </div>
            </div>
          </div>
        </div>""")

    incorrect_count = len(questions)
    date_str = completed_at.strftime('%B %d, %Y') if completed_at else ''
    header_score = f"{incorrect_count} incorrect out of {total}" if total else f"{incorrect_count} incorrect"
    blocks_html = '\n'.join(blocks) if blocks else '<p style="color:#666;padding:1rem 0;">No incorrect answers — all correct!</p>'

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Review: {quiz_title}</title>
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/katex@0.16.9/dist/katex.min.css">
<script defer src="https://cdn.jsdelivr.net/npm/katex@0.16.9/dist/katex.min.js"></script>
<script defer src="https://cdn.jsdelivr.net/npm/katex@0.16.9/dist/contrib/auto-render.min.js"
    onload="renderMathInElement(document.body, {{delimiters:[{{left:'$',right:'$',display:false}},{{left:'\\\\(',right:'\\\\)',display:false}},{{left:'\\\\[',right:'\\\\]',display:true}}]}})"></script>
<style>
  body {{ font-family: 'Segoe UI', system-ui, sans-serif; max-width: 820px; margin: 40px auto; padding: 0 24px; color: #111; line-height: 1.65; }}
  #toolbar {{ position: fixed; top: 0; left: 0; right: 0; background: #1F6FAE; color: #fff; padding: 8px 24px;
             display: flex; align-items: center; gap: 14px; font-size: 0.9rem; z-index: 999; box-shadow: 0 2px 6px rgba(0,0,0,.25); }}
  #toolbar button {{ background: #fff; color: #1F6FAE; border: none; border-radius: 4px; padding: 5px 14px; font-weight: 700; cursor: pointer; font-size: 0.88rem; }}
  #toolbar button:hover {{ background: #dceeff; }}
  body {{ padding-top: 54px; }}
  .review-header {{ background: #f0f6fb; border: 1px solid #cfe0ed; border-radius: 8px; padding: 1rem 1.25rem; margin-bottom: 1.75rem; }}
  .review-header h1 {{ font-size: 1.15rem; font-weight: 700; margin: 0 0 4px; color: #1a2d3d; }}
  .review-meta {{ font-size: 0.87rem; color: #5a7a9a; display: flex; gap: 1.5rem; flex-wrap: wrap; }}
  .review-meta span b {{ color: #1a2d3d; }}
  .review-block {{ margin-bottom: 2rem; border-bottom: 1px solid #e8edf2; padding-bottom: 1.5rem; }}
  .review-block:last-child {{ border-bottom: none; }}
  .q-row {{ display: grid; grid-template-columns: 54px 1fr; gap: 0 6px; }}
  .q-label {{ text-align: right; padding-right: 10px; padding-top: 2px; }}
  .q-num {{ font-size: 0.95rem; font-weight: 700; display: block; color: #2c6e9e; }}
  .q-stem {{ font-size: 0.97rem; margin-bottom: 8px; }}
  .q-image img {{ max-width: 50%; margin-bottom: 8px; }}
  .q-options {{ margin-bottom: 10px; }}
  .option {{ margin: 3px 0; font-size: 0.92rem; }}
  .opt-label {{ font-weight: 600; min-width: 22px; display: inline-block; }}
  .fill-row {{ display: flex; align-items: baseline; gap: 6px; margin: 5px 0; font-size: 0.92rem; }}
  .blank-box {{ display: inline-block; width: 90px; border-bottom: 1.5px solid #555; margin: 0 3px; }}
  .answer-row {{ display: flex; align-items: baseline; gap: 6px; font-size: 0.9rem; margin-top: 5px; }}
  .ans-icon {{ font-weight: 700; font-size: 0.95rem; width: 18px; flex-shrink: 0; }}
  .ans-label {{ color: #666; min-width: 58px; flex-shrink: 0; }}
  .correct-row .ans-icon {{ color: #1a7a4a; }}
  .correct-row .ans-val {{ color: #1a7a4a; font-weight: 600; }}
  .student-row .ans-icon {{ color: #b44; }}
  .student-row .ans-val {{ color: #b44; }}
  @media print {{
    #toolbar {{ display: none !important; }}
    body {{ margin: 16px; padding-top: 0; }}
    .review-block {{ page-break-inside: avoid; }}
  }}
</style>
</head>
<body>
<div id="toolbar">
  <button onclick="window.print()">&#128438; Print / Save PDF</button>
  <span style="opacity:.75">{student_name} &nbsp;&bull;&nbsp; {quiz_title}</span>
</div>
<div class="review-header">
  <h1>{quiz_title}</h1>
  <div class="review-meta">
    <span>Student: <b>{student_name}</b></span>
    <span>Score: <b>{score}</b></span>
    <span>Incorrect: <b>{header_score}</b></span>
    {'<span>Completed: <b>' + date_str + '</b></span>' if date_str else ''}
  </div>
</div>
{blocks_html}
</body>
</html>"""



# ==================== PDF ==================== #

@question_bp.route("/print/<int:question_id>", methods=["GET"])
@login_required
def print_question(question_id):
    """Generate and download a PDF of the question."""
    q = QBank.query.get(question_id)
    if not q:
        return jsonify({"ok": False, "errors": ["Question not found"]}), 404
    handler = get_handler(q.type.lower() if q.type else 'mcq')
    if not handler:
        return jsonify({"ok": False, "errors": [f"Unknown question type: {q.type}"]}), 400
    question = handler.prepare_html(q.json)
    question_data = {
        "question": question, "question_id": q.id,
        "type": q.type, "topic": q.topic, "subtopic": q.subtopic, "level": q.level
    }
    pdf_buffer = handler.generate_pdf(question_data, question_id)
    return send_file(pdf_buffer, mimetype='application/pdf', as_attachment=True,
                     download_name=f'question_{question_id}.pdf')


# ==================== RETRIEVE (via qb_bp) ==================== #

@qb_bp.route("/question/<int:question_id>", methods=["GET"])
@login_required
def get_question(question_id):
    q = QBank.query.get(question_id)
    if not q:
        return jsonify({"ok": False, "errors": ["Question not found"]}), 404
    return jsonify({
        "ok": True, "id": q.id, "type": q.type,
        "topic": q.topic, "subtopic": q.subtopic, "level": q.level, "question": q.json
    })


@qb_bp.route("/questions", methods=["GET"])
@login_required
def list_questions():
    query = QBank.query
    for field in ('type', 'topic', 'subtopic', 'level'):
        if request.args.get(field):
            query = query.filter_by(**{field: request.args[field]})
    items = [{
        "id": q.id, "type": q.type, "topic": q.topic, "subtopic": q.subtopic,
        "level": q.level, "stem_latex": q.json['stem']['latex'], "image": q.json.get('image')
    } for q in query.all()]
    return jsonify({"ok": True, "items": items})


# ==================== LIST & PAGINATION ==================== #

@question_bp.route("/list", methods=["GET"])
@login_required
def list_questions_page():
    return render_template("question_list.html")


@question_bp.route("/api/page", methods=["GET"])
@login_required
def get_questions_paginated():
    """Paginated question list with optional topic filter."""
    try:
        page = int(request.args.get('page', 1))
        per_page = 50
        topic = request.args.get('topic', '').strip()
        ids_param = request.args.get('ids', '').strip()
        id_from   = request.args.get('id_from', type=int)
        id_to     = request.args.get('id_to',   type=int)
        unused = request.args.get('unused', '0') == '1'

        query = QBank.query
        if ids_param:
            id_list = [int(i) for i in ids_param.split(',') if i.strip().isdigit()]
            query = query.filter(QBank.id.in_(id_list))
        elif id_from is not None:
            if id_to is not None:
                query = query.filter(QBank.id >= id_from, QBank.id <= id_to)
            else:
                query = query.filter(QBank.id == id_from)
        elif topic:
            query = query.filter_by(topic=topic)
        if unused and not ids_param:
            used_ids = set()
            for row in Quiz.query.with_entities(Quiz.question_ids).all():
                if row.question_ids:
                    for qid in row.question_ids.split(','):
                        qid = qid.strip()
                        if qid.isdigit():
                            used_ids.add(int(qid))
            if used_ids:
                query = query.filter(~QBank.id.in_(used_ids))
        if id_from is not None:
            query = query.order_by(QBank.id.asc())
        else:
            query = query.order_by(QBank.id.desc())

        total = query.count()
        pagination = query.paginate(page=page, per_page=per_page)
        items = []

        import re as _re
        for q in pagination.items:
            stem_text = ""
            if isinstance(q.json.get('stem'), dict):
                stem_text = q.json['stem'].get('latex') or \
                    _re.sub(r'<[^>]+>', '', q.json['stem'].get('html', ''))
            elif q.json.get('stem'):
                stem_text = str(q.json['stem'])

            input_text = ""
            if q.type in ('mcq', 'mr', 'ohs') and 'options' in q.json.get('input', {}):
                input_text = f"{len(q.json['input']['options'])} options"
            elif q.type == 'fill' and 'blanks' in q.json.get('input', {}):
                input_text = f"{len(q.json['input']['blanks'])} blanks"

            # Build answer_text
            ans = q.json.get('answer', {})
            answer_text = "—"
            if q.type in ('mcq', 'ohs'):
                cid = ans.get('correct_option_id') or ans.get('correct_option_ids')
                if isinstance(cid, list):
                    cid = cid[0] if cid else None
                opts = {o['id']: o.get('latex', o.get('html', o['id']))
                        for o in q.json.get('input', {}).get('options', [])}
                answer_text = opts.get(cid, cid or '—')
            elif q.type == 'mr':
                cids = ans.get('correct_option_ids') or ans.get('correct_option_id') or []
                if isinstance(cids, str):
                    cids = [cids]
                opts = {o['id']: o.get('latex', o.get('html', o['id']))
                        for o in q.json.get('input', {}).get('options', [])}
                answer_text = ', '.join(opts.get(c, c) for c in cids) or '—'
            elif q.type == 'fill':
                correct = ans.get('correct', [])
                if isinstance(correct, list):
                    parts = []
                    for item in correct:
                        if isinstance(item, dict):
                            nums = item.get('accepted_numeric', [])
                            parts.append(str(nums[0]) if nums else item.get('blank_id', '—'))
                        elif isinstance(item, list) and item:
                            parts.append(str(item[0]))
                        else:
                            parts.append(str(item))
                    answer_text = ' | '.join(parts) or '—'
            elif q.type == 'feval':
                answer_text = 'computed'

            items.append({
                "id": q.id, "type": q.type, "topic": q.topic or "—",
                "stem": (stem_text[:100] + '...') if len(stem_text) > 100 else stem_text,
                "input": (input_text[:100] + '...') if len(input_text) > 100 else input_text,
                "answer_text": (answer_text[:80] + '...') if len(str(answer_text)) > 80 else answer_text
            })

        return jsonify({
            "ok": True, "items": items, "total": total, "page": page,
            "pages": pagination.pages, "has_next": pagination.has_next, "has_prev": pagination.has_prev
        })
    except Exception as e:
        logger.exception(e)
        return jsonify({"ok": False, "error": str(e)}), 400


# ==================== DELETE / DUPLICATE ==================== #

@question_bp.route("/api/delete", methods=["POST"])
@login_required
def delete_questions():
    try:
        data = request.get_json()
        question_ids = data.get('question_ids', [])
        if not question_ids:
            return jsonify({"ok": False, "error": "No questions specified"}), 400
        existing_count = QBank.query.filter(QBank.id.in_(question_ids)).count()
        if existing_count != len(question_ids):
            return jsonify({"ok": False, "error": "One or more questions do not exist"}), 400

        # Block if any selected question is used in a quiz
        blocked = []
        for qid in question_ids:
            quizzes = _quizzes_using_question(qid)
            if quizzes:
                names = ', '.join(f"{qz.quiz_code} ({qz.title})" for qz in quizzes)
                blocked.append(f"Q#{qid} → {names}")
        if blocked:
            return jsonify({"ok": False,
                            "error": "Cannot delete — remove from quizzes first:\n" + "\n".join(blocked)}), 400

        deleted = QBank.query.filter(QBank.id.in_(question_ids)).delete()
        db.session.commit()
        logger.info(f"Deleted {deleted} question(s): IDs={question_ids}")
        return jsonify({"ok": True, "deleted_count": deleted,
                        "message": f"Successfully deleted {deleted} question(s)"})
    except Exception as e:
        logger.exception(e)
        db.session.rollback()
        return jsonify({"ok": False, "error": str(e)}), 500


@question_bp.route("/api/duplicate/<int:question_id>", methods=["POST"])
@login_required
def duplicate_question(question_id):
    try:
        original = QBank.query.get(question_id)
        if not original:
            return jsonify({"ok": False, "error": "Question not found"}), 404
        new_json = copy.deepcopy(original.json)
        new_json.pop('id', None)
        new_json.pop('image', None)
        new_question, error = create_question_safely(
            original.type, original.topic, original.subtopic, original.level, new_json)
        if error:
            return jsonify({"ok": False, "error": error}), 400
        logger.info(f"Duplicated question {question_id} -> {new_question.id}")
        return jsonify({"ok": True, "question_id": new_question.id,
                        "message": f"Question duplicated. New ID: {new_question.id}"})
    except Exception as e:
        logger.exception(e)
        return jsonify({"ok": False, "error": str(e)}), 500


@question_bp.route("/duplicate/<int:question_id>", methods=["GET"])
@login_required
def duplicate_question_page(question_id):
    try:
        original = QBank.query.get(question_id)
        if not original:
            return redirect(url_for('question.list_questions_page'))
        new_json = copy.deepcopy(original.json)
        new_json.pop('id', None)
        new_json.pop('image', None)
        new_question, error = create_question_safely(
            original.type, original.topic, original.subtopic, original.level, new_json)
        if error:
            logger.error(f"Error duplicating question {question_id}: {error}")
            return redirect(url_for('question.list_questions_page'))
        logger.info(f"Duplicated question {question_id} -> {new_question.id}")
        return redirect(url_for('question.edit_question_redirect', question_id=new_question.id))
    except Exception as e:
        logger.exception(e)
        return redirect(url_for('question.list_questions_page'))


# ==================== UPLOAD MCQ ==================== #

def _parse_mcq_upload(text):
    """Parse a .txt file into MCQ question blocks.

    Format — each question= line starts a new block; opt#= lines add options:
        question=<stem latex>
        opt1=<option latex>
        opt2=<option latex>
        ...
    Empty lines and unrecognised keys are ignored.
    Returns: [{'question': str, 'options': [{'id': str, 'latex': str}, ...]}, ...]
    """
    blocks = []
    current = None
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or '=' not in line:
            continue
        key, _, value = line.partition('=')
        key = key.strip().lower()
        value = value.strip()
        if key == 'question':
            if current is not None:
                blocks.append(current)
            current = {'question': value, 'options': []}
        elif key.startswith('opt') and current is not None:
            current['options'].append({'id': key, 'latex': value})
    if current is not None:
        blocks.append(current)
    return blocks


@question_bp.route("/upload", methods=["GET"])
@login_required
def upload_page():
    return render_template("upload_mcq.html")


@question_bp.route("/api/upload-mcq", methods=["POST"])
@login_required
def upload_mcq():
    """Parse a .txt file of question=/opt#= blocks and save each as an MCQ."""
    from qb.handlers.mcq import MCQHandler

    topic    = (request.form.get('topic',    '') or '').strip()
    subtopic = (request.form.get('subtopic', '') or '').strip()
    level    = (request.form.get('level',    '') or '').strip()

    file = request.files.get('file')
    if not file or not file.filename.lower().endswith('.txt'):
        return jsonify({'ok': False, 'error': 'A .txt file is required'}), 400

    try:
        text = file.read().decode('utf-8')
    except Exception:
        return jsonify({'ok': False, 'error': 'Could not read file — ensure it is UTF-8 encoded'}), 400

    blocks = _parse_mcq_upload(text)
    if not blocks:
        return jsonify({'ok': False, 'error': 'No question= blocks found in file'}), 400

    results = []
    for n, block in enumerate(blocks, 1):
        preview = block['question'][:60] + ('…' if len(block['question']) > 60 else '')

        if not block['question']:
            results.append({'n': n, 'ok': False, 'error': 'Empty question text — skipped'})
            continue
        if not block['options']:
            results.append({'n': n, 'ok': False, 'preview': preview, 'error': 'No options found — skipped'})
            continue

        data = {
            'type': 'mcq',
            'topic': topic,
            'subtopic': subtopic,
            'level': level,
            'question': {
                'stem': {'latex': block['question']},
                'type': 'mcq',
                'input': {
                    'options': block['options'],
                    'shuffle': True,
                },
                'answer': {
                    'correct_option_id': 'opt1',
                },
            },
        }

        try:
            q, error = MCQHandler.save_question(data)
            if error:
                results.append({'n': n, 'ok': False, 'preview': preview, 'error': error})
            else:
                q.sync_required = True
                db.session.commit()
                results.append({'n': n, 'ok': True, 'id': q.id, 'preview': preview})
        except Exception as e:
            logger.exception("upload_mcq: error saving question %d", n)
            results.append({'n': n, 'ok': False, 'preview': preview, 'error': str(e)})

    saved  = sum(1 for r in results if r.get('ok'))
    failed = len(results) - saved
    return jsonify({'ok': True, 'results': results, 'saved': saved, 'failed': failed})


# ==================== UPLOAD FILL ==================== #

def _parse_fill_upload(text):
    """Parse a .txt file into Fill question blocks.

    Format:
        question=<stem latex>
        label1=<input_label latex>
        answer:<numeric value>
        label2=<input_label latex>
        answer:<numeric value>
    - answer: lines use colon separator
    - Missing or non-numeric answer defaults to 0
    - One or more label/answer pairs per question
    Returns: [{'question': str, 'blanks': [{'label': str, 'answer': float}, ...]}, ...]
    """
    blocks = []
    current = None
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        # answer: uses colon separator
        if line.lower().startswith('answer:'):
            _, _, value = line.partition(':')
            value = value.strip()
            if current is not None and current['blanks']:
                try:
                    current['blanks'][-1]['answer'] = float(value) if value else 0.0
                except ValueError:
                    current['blanks'][-1]['answer'] = 0.0
            continue
        if '=' not in line:
            continue
        key, _, value = line.partition('=')
        key = key.strip().lower()
        value = value.strip()
        if key == 'question':
            if current is not None:
                blocks.append(current)
            current = {'question': value, 'blanks': []}
        elif key.startswith('label') and current is not None:
            current['blanks'].append({'label': value, 'answer': 0.0})
    if current is not None:
        blocks.append(current)
    return blocks


@question_bp.route("/api/upload-fill", methods=["POST"])
@login_required
def upload_fill():
    """Parse a .txt file of fill question blocks and save each as a FILL question."""
    from qb.handlers.fill import FILLHandler

    topic    = (request.form.get('topic',    '') or '').strip()
    subtopic = (request.form.get('subtopic', '') or '').strip()
    level    = (request.form.get('level',    '') or '').strip()

    file = request.files.get('file')
    if not file or not file.filename.lower().endswith('.txt'):
        return jsonify({'ok': False, 'error': 'A .txt file is required'}), 400

    try:
        text = file.read().decode('utf-8')
    except Exception:
        return jsonify({'ok': False, 'error': 'Could not read file — ensure it is UTF-8 encoded'}), 400

    blocks = _parse_fill_upload(text)
    if not blocks:
        return jsonify({'ok': False, 'error': 'No question= blocks found in file'}), 400

    results = []
    for n, block in enumerate(blocks, 1):
        preview = block['question'][:60] + ('…' if len(block['question']) > 60 else '')

        if not block['question']:
            results.append({'n': n, 'ok': False, 'error': 'Empty question text — skipped'})
            continue
        if not block['blanks']:
            results.append({'n': n, 'ok': False, 'preview': preview, 'error': 'No label= entries found — skipped'})
            continue

        data = {
            'type': 'fill',
            'topic': topic,
            'subtopic': subtopic,
            'level': level,
            'question': {
                'stem': {'latex': block['question']},
                'type': 'fill',
                'input': {
                    'blanks': [
                        {
                            'id': f'blank{i + 1}',
                            'input_label': {'latex': blank['label']},
                            'response_type': 'numeric',
                        }
                        for i, blank in enumerate(block['blanks'])
                    ],
                },
                'answer': {
                    'correct': [
                        {
                            'blank_id': f'blank{i + 1}',
                            'response_type': 'numeric',
                            'accepted_numeric': [blank['answer']],
                        }
                        for i, blank in enumerate(block['blanks'])
                    ],
                },
            },
        }

        try:
            q, error = FILLHandler.save_question(data)
            if error:
                results.append({'n': n, 'ok': False, 'preview': preview, 'error': error})
            else:
                q.sync_required = True
                db.session.commit()
                results.append({'n': n, 'ok': True, 'id': q.id, 'preview': preview})
        except Exception as e:
            logger.exception("upload_fill: error saving question %d", n)
            results.append({'n': n, 'ok': False, 'preview': preview, 'error': str(e)})

    saved  = sum(1 for r in results if r.get('ok'))
    failed = len(results) - saved
    return jsonify({'ok': True, 'results': results, 'saved': saved, 'failed': failed})
