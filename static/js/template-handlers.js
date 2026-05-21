/**
 * Template Handlers
 * Handles interactivity for each question type.
 * Single source of truth for answer-checking and feedback across all rendering contexts.
 */

// ── FEVAL rule evaluation (self-contained, no dependency on quiz-feval.js) ─────
function _fevalEvaluateRules(rules, inputs) {
    const ns = Object.assign({}, inputs, {
        abs: Math.abs, round: Math.round, max: Math.max, min: Math.min,
        len: x => (typeof x === 'string' || Array.isArray(x)) ? x.length : 0,
        sum: arr => Array.isArray(arr) ? arr.reduce((a, b) => a + b, 0) : 0,
        isinstance: (val, type) => {
            if (type === 'int')   return Number.isInteger(val);
            if (type === 'float') return typeof val === 'number';
            if (type === 'str')   return typeof val === 'string';
            if (type === 'bool')  return typeof val === 'boolean';
            return false;
        },
        int: 'int', float: 'float', str: 'str', bool: 'bool'
    });

    // Interpolate {expression} placeholders in feedback using the variable namespace
    const _interpolate = (template) => {
        if (!template) return template;
        return template.replace(/\{([^}]+)\}/g, (_, expr) => {
            try {
                /* jshint evil:true */
                return eval(`(function(){with(ns){return(${expr});}})()`);
            } catch (e) {
                return `{${expr}}`;
            }
        });
    };

    let allCorrect = true;
    const results = rules.map((rule, i) => {
        try {
            // Rules are authored by authenticated admins only — eval is intentional here
            /* jshint evil:true */
            const passed = !!eval(`(function(){with(ns){return(${rule.expression});}})()`);
            if (!passed) allCorrect = false;
            return { passed, feedback: _interpolate(rule.feedback) || `Rule ${i + 1} not satisfied` };
        } catch (e) {
            allCorrect = false;
            return { passed: false, feedback: `Error in rule ${i + 1}: ${e.message}` };
        }
    });
    return { allCorrect, results };
}

// ── Base class ─────────────────────────────────────────────────────────────────
class TemplateHandler {
    constructor(container, question, readOnly = false) {
        this.container = container;
        this.question = question;
        this.readOnly = readOnly;
    }

    getAnswer()       { return null; }
    isCorrect(answer) { return false; }
    attachListeners() {}

    showFeedback(isCorrect, message) {
        this.container.querySelectorAll('.template-feedback').forEach(el => el.remove());
        if (!message) return;
        const div = document.createElement('div');
        div.className = `template-feedback ${isCorrect ? 'correct' : 'incorrect'}`;
        div.innerHTML = message;
        this.container.appendChild(div);
    }

    disable() {
        this.container.querySelectorAll('input, textarea').forEach(el => el.disabled = true);
    }
    enable() {
        this.container.querySelectorAll('input, textarea').forEach(el => el.disabled = false);
    }
}

// ── MCQ ────────────────────────────────────────────────────────────────────────
class TemplateHandlerMCQ extends TemplateHandler {
    getAnswer() {
        const sel = this.container.querySelector('.template-radio:checked');
        return sel ? sel.value : null;
    }

    _correctId() {
        return this.question.answer?.correct_option_id
            || this.question.input?.options?.[0]?.id
            || 'opt_0';
    }

    isCorrect(answer) {
        if (!answer) return false;
        return answer.toString() === this._correctId().toString();
    }

    showFeedback(isCorrect, message) {
        const correctId  = this._correctId();
        const selectedId = this.getAnswer();

        this.container.querySelectorAll('.template-option').forEach(optDiv => {
            const radio = optDiv.querySelector('.template-radio');
            if (!radio) return;
            const optId = radio.value;
            optDiv.classList.remove('correct-option', 'incorrect-option');
            let icon = optDiv.querySelector('.option-feedback-icon');
            if (!icon) {
                icon = document.createElement('span');
                icon.className = 'option-feedback-icon';
                optDiv.appendChild(icon);
            }
            if (optId === correctId) {
                optDiv.classList.add('correct-option');
                icon.textContent = '\u2713';
            } else if (optId === selectedId && !isCorrect) {
                optDiv.classList.add('incorrect-option');
                icon.textContent = '\u2717';
            } else {
                icon.textContent = '';
            }
        });

        if (message && !isCorrect) super.showFeedback(isCorrect, message);
        else this.container.querySelectorAll('.template-feedback').forEach(el => el.remove());
    }

    attachListeners() {
        if (this.readOnly) { this.disable(); return; }
        const radios = this.container.querySelectorAll('.template-radio');
        radios.forEach(radio => {
            radio.addEventListener('change', e => {
                radios.forEach(r => r.closest('.template-option').classList.remove('selected'));
                e.target.closest('.template-option').classList.add('selected');
            });
        });
    }
}

// ── MR ─────────────────────────────────────────────────────────────────────────
class TemplateHandlerMR extends TemplateHandler {
    getAnswer() {
        const checked = Array.from(this.container.querySelectorAll('.template-checkbox:checked'))
            .map(el => el.value);
        return checked.length > 0 ? checked : null;
    }

    isCorrect(answer) {
        if (!answer) return false;
        const correctIds = this.question.answer?.correct_option_ids || [];
        if (!correctIds.length) return false;
        const selected = new Set(answer.map(String));
        const correct  = new Set(correctIds.map(String));
        if (selected.size !== correct.size) return false;
        return [...selected].every(id => correct.has(id));
    }

    showFeedback(isCorrect, message) {
        const correctIds  = new Set((this.question.answer?.correct_option_ids || []).map(String));
        const selectedIds = new Set((this.getAnswer() || []).map(String));

        this.container.querySelectorAll('.template-option').forEach(optDiv => {
            const cb = optDiv.querySelector('.template-checkbox');
            if (!cb) return;
            const optId = String(cb.value);
            optDiv.classList.remove('correct-option', 'incorrect-option');
            let icon = optDiv.querySelector('.option-feedback-icon');
            if (!icon) {
                icon = document.createElement('span');
                icon.className = 'option-feedback-icon';
                optDiv.appendChild(icon);
            }
            if (correctIds.has(optId)) {
                optDiv.classList.add('correct-option');
                icon.textContent = '\u2713';
            } else if (selectedIds.has(optId)) {
                optDiv.classList.add('incorrect-option');
                icon.textContent = '\u2717';
            } else {
                icon.textContent = '';
            }
        });

        if (message && !isCorrect) super.showFeedback(isCorrect, message);
    }

    attachListeners() {
        if (this.readOnly) { this.disable(); return; }
        this.container.querySelectorAll('.template-checkbox').forEach(cb => {
            cb.addEventListener('change', e => {
                e.target.closest('.template-option').classList.toggle('selected', e.target.checked);
            });
        });
    }
}

// ── FILL ───────────────────────────────────────────────────────────────────────
class TemplateHandlerFILL extends TemplateHandler {
    getAnswer() {
        const answers = {};
        let incomplete = false;
        this.container.querySelectorAll('.template-blank-input').forEach((input, idx) => {
            const key = input.dataset.blankId || `blank_${idx}`;
            const val = input.value.trim();
            if (!val) incomplete = true;
            answers[key] = val;
        });
        this.container.querySelectorAll('.template-fraction-input').forEach(widget => {
            const key = widget.dataset.blankId;
            if (!key) return;
            const num = widget.querySelector('.template-fraction-num')?.value.trim() || '';
            const den = widget.querySelector('.template-fraction-den')?.value.trim() || '';
            if (!num || !den) incomplete = true;
            answers[key] = `${num}/${den}`;
        });
        if (Object.keys(answers).length === 0 || incomplete) return null;
        return answers;
    }

    _checkBlank(userValue, entry) {
        const rt = entry.response_type || 'text';
        if (rt === 'numeric') {
            const n = parseFloat(userValue);
            return !isNaN(n) && (entry.accepted_numeric || []).some(ca => Math.abs(parseFloat(ca) - n) < 1e-9);
        }
        if (rt === 'fraction') {
            const parts = userValue.split('/');
            if (parts.length !== 2) return false;
            const [num, den] = parts.map(Number);
            if (!Number.isFinite(num) || !Number.isFinite(den) || den === 0) return false;
            const gcd = (a, b) => b === 0 ? Math.abs(a) : gcd(b, a % b);
            const g1 = gcd(num, den);
            const userN = num / g1, userD = den / g1;
            return (entry.accepted_fraction || []).some(ca => {
                if (ca.denominator === 0) return false;
                const g2 = gcd(ca.numerator, ca.denominator);
                return (ca.numerator / g2) === userN && (ca.denominator / g2) === userD;
            });
        }
        // text
        const norm = s => s.replace(/\s+/g, '').toLowerCase();
        return (entry.accepted_text || []).some(ca => norm(ca) === norm(userValue));
    }

    isCorrect(answer) {
        if (!answer) return false;
        const blanks     = this.question.input?.blanks || [];
        const correctArr = this.question.answer?.correct || [];
        if (!blanks.length) return false;
        return blanks.every((blank, idx) => {
            const blankId = blank.id || `blank_${idx}`;
            return correctArr[idx] ? this._checkBlank(answer[blankId] || '', correctArr[idx]) : false;
        });
    }

    _formatCorrectAnswer(entry) {
        const rt = entry.response_type || 'text';
        if (rt === 'fraction' && entry.accepted_fraction?.length) {
            const f = entry.accepted_fraction[0];
            return { html: true, value: `<span class="hint-fraction"><span class="hint-fraction-num">${f.numerator}</span><span class="hint-fraction-bar"></span><span class="hint-fraction-den">${f.denominator}</span></span>` };
        }
        if (rt === 'numeric' && entry.accepted_numeric?.length) {
            return String(entry.accepted_numeric[0]);
        }
        if (entry.accepted_text?.length) {
            return entry.accepted_text[0];
        }
        return '';
    }

    showFeedback(isCorrect, message) {
        const blanks     = this.question.input?.blanks || [];
        const correctArr = this.question.answer?.correct || [];
        const answer     = this.getAnswer() || {};

        blanks.forEach((blank, idx) => {
            const blankId  = blank.id || `blank_${idx}`;
            const ok       = correctArr[idx] ? this._checkBlank(answer[blankId] || '', correctArr[idx]) : false;
            const inputEl  = this.container.querySelector(`.template-blank-input[data-blank-id="${blankId}"]`);
            const widgetEl = this.container.querySelector(`.template-fraction-input[data-blank-id="${blankId}"]`);
            const targetEl = inputEl || widgetEl;
            const wrapper  = targetEl?.closest('.template-blank-wrapper');
            if (!wrapper) return;

            // Apply colour state
            if (inputEl)  { inputEl.classList.toggle('correct-answer', ok);  inputEl.classList.toggle('incorrect-answer', !ok); }
            if (widgetEl) { widgetEl.classList.toggle('correct-answer', ok); widgetEl.classList.toggle('incorrect-answer', !ok); }

            // Remove old feedback rows before re-inserting
            wrapper.querySelectorAll('.blank-feedback-row').forEach(el => el.remove());

            // Feedback row (appears below the input line)
            const feedbackRow = document.createElement('div');
            feedbackRow.className = 'blank-feedback-row';

            const icon = document.createElement('span');
            icon.className = `blank-feedback-icon ${ok ? 'correct' : 'incorrect'}`;
            icon.textContent = ok ? '\u2713' : '\u2717';
            feedbackRow.appendChild(icon);

            // Correct-answer hint on wrong
            if (!ok && correctArr[idx]) {
                const hint = document.createElement('span');
                hint.className = 'blank-correct-hint';
                const formatted = this._formatCorrectAnswer(correctArr[idx]);
                if (formatted && formatted.html) {
                    hint.innerHTML = 'correct answer: <span class="blank-correct-value">' + formatted.value + '</span>';
                } else {
                    hint.innerHTML = 'correct answer: <span class="blank-correct-value">' + (formatted || '') + '</span>';
                }
                feedbackRow.appendChild(hint);
            }

            wrapper.appendChild(feedbackRow);
        });

        if (message && !isCorrect) super.showFeedback(isCorrect, message);
    }

    attachListeners() {
        if (this.readOnly) { this.disable(); return; }
        this.container.querySelectorAll('.template-blank-input').forEach(input => {
            input.addEventListener('focus', () => input.closest('.template-blank-wrapper')?.classList.add('focused'));
            input.addEventListener('blur',  () => input.closest('.template-blank-wrapper')?.classList.remove('focused'));
        });
    }
}

// ── OHS ────────────────────────────────────────────────────────────────────────
class TemplateHandlerOHS extends TemplateHandler {
    constructor(container, question, readOnly = false) {
        super(container, question, readOnly);
        this._hotspot    = question.image?.hotspot || null;
        this._selected   = null;   // { dx, dy, hit } in display coords
        this._locked     = false;
        this._followerEl = null;
        this._selectionEl = null;
        this._feedbackEl  = null;
    }

    getAnswer() {
        if (!this._selected) return null;
        return this._selected.hit ? (this._hotspot?.id || 'hs1') : '__miss__';
    }

    isCorrect(answer) {
        if (!answer) return false;
        return answer === (this.question.answer?.correct_hotspot_id || 'hs1');
    }

    attachListeners() {
        const img = this.container.querySelector('.template-ohs-image');
        const svg = this.container.querySelector('.template-ohs-overlay');
        if (!img || !svg) return;

        const ns  = 'http://www.w3.org/2000/svg';
        const mk  = (tag, attrs) => {
            const el = document.createElementNS(ns, tag);
            for (const [k, v] of Object.entries(attrs)) el.setAttribute(k, v);
            return el;
        };
        const tr  = (g, x, y) => g.setAttribute('transform', `translate(${x},${y})`);

        // ── Follower group: pulsing ring + dot, follows cursor ──────────
        const followerG  = mk('g', { class: 'ohs-follower', transform: 'translate(0,0)' });
        followerG.style.cssText = 'display:none; pointer-events:none';
        const pulseRing  = mk('circle', { class: 'ohs-pulse-ring', cx: '0', cy: '0', r: '14',
            fill: 'none', stroke: 'rgba(44,110,158,0.55)', 'stroke-width': '2' });
        const followerDot = mk('circle', { cx: '0', cy: '0', r: '4',
            fill: 'rgba(44,110,158,0.5)' });
        followerG.append(pulseRing, followerDot);
        svg.appendChild(followerG);
        this._followerEl = followerG;

        // ── Selection group: solid blue dot with white border ───────────
        const selG      = mk('g', { class: 'ohs-selection', transform: 'translate(0,0)' });
        selG.style.cssText = 'display:none; pointer-events:none';
        const selShadow = mk('circle', { cx: '0', cy: '0', r: '13',
            fill: 'white', filter: 'drop-shadow(0 2px 5px rgba(0,0,0,0.32))' });
        const selInner  = mk('circle', { cx: '0', cy: '0', r: '8', fill: '#1565C0' });
        const selRing   = mk('circle', { cx: '0', cy: '0', r: '12',
            fill: 'none', stroke: 'white', 'stroke-width': '2.5' });
        selG.append(selShadow, selInner, selRing);
        svg.appendChild(selG);
        this._selectionEl = selG;

        // ── Feedback group: hotspot rect shown after submit ─────────────
        const feedG = mk('g', { class: 'ohs-feedback' });
        feedG.style.cssText = 'display:none; pointer-events:none';
        svg.appendChild(feedG);
        this._feedbackEl = feedG;

        // ── Sync SVG dimensions to rendered image size ──────────────────
        const syncSize = () => {
            svg.setAttribute('width',  img.width);
            svg.setAttribute('height', img.height);
        };
        if (img.complete && img.naturalWidth) syncSize();
        else img.addEventListener('load', syncSize);

        if (this.readOnly) return;

        // ── Interaction ─────────────────────────────────────────────────
        const getPos = e => {
            const r = svg.getBoundingClientRect();
            return { dx: e.clientX - r.left, dy: e.clientY - r.top };
        };

        svg.addEventListener('mousemove', e => {
            if (this._locked) return;
            const { dx, dy } = getPos(e);
            tr(followerG, dx, dy);
            followerG.style.display = '';
        });

        svg.addEventListener('mouseleave', () => {
            followerG.style.display = 'none';
        });

        svg.addEventListener('click', e => {
            if (this._locked) return;
            const { dx, dy } = getPos(e);
            const sx = img.naturalWidth  ? img.width  / img.naturalWidth  : 1;
            const sy = img.naturalHeight ? img.height / img.naturalHeight : 1;
            const nx = dx / sx;
            const ny = dy / sy;
            const hs  = this._hotspot;
            const hit = hs && nx >= hs.x && nx <= hs.x + hs.width
                           && ny >= hs.y && ny <= hs.y + hs.height;
            this._selected = { dx, dy, hit };
            tr(selG, dx, dy);
            selG.style.display = '';
            followerG.style.display = 'none';
        });
    }

    showFeedback(isCorrect, message) {
        this._locked = true;
        if (this._followerEl) this._followerEl.style.display = 'none';

        const img = this.container.querySelector('.template-ohs-image');
        const svg = this.container.querySelector('.template-ohs-overlay');
        if (img && svg && this._hotspot && this._feedbackEl) {
            const hs = this._hotspot;
            const sx = img.naturalWidth  ? img.width  / img.naturalWidth  : 1;
            const sy = img.naturalHeight ? img.height / img.naturalHeight : 1;
            const ns = 'http://www.w3.org/2000/svg';
            const rect = document.createElementNS(ns, 'rect');
            rect.setAttribute('x',            hs.x * sx);
            rect.setAttribute('y',            hs.y * sy);
            rect.setAttribute('width',        hs.width  * sx);
            rect.setAttribute('height',       hs.height * sy);
            rect.setAttribute('rx',           '4');
            rect.setAttribute('stroke-width', '2.5');
            rect.setAttribute('fill',   'rgba(76,175,80,0.25)');
            rect.setAttribute('stroke', '#4caf50');
            this._feedbackEl.innerHTML = '';
            this._feedbackEl.appendChild(rect);
            this._feedbackEl.style.display = '';
        }

        // If incorrect, turn the selection ball red
        if (!isCorrect && this._selectionEl) {
            const circles = this._selectionEl.querySelectorAll('circle');
            if (circles[1]) circles[1].setAttribute('fill', '#f44336');
        }

        const band = message || (!isCorrect ? '\u2717 Incorrect' : null);
        if (band) super.showFeedback(isCorrect, band);
    }
}

// ── FEVAL ──────────────────────────────────────────────────────────────────────
class TemplateHandlerFEVAL extends TemplateHandler {
    getAnswer() {
        const answers = {};
        let incomplete = false;
        this.container.querySelectorAll('.template-feval-answer').forEach(input => {
            const key = input.dataset.evalId;
            if (key) {
                const val = input.value.trim();
                if (!val) incomplete = true;
                answers[key] = val;
            }
        });
        if (Object.keys(answers).length === 0 || incomplete) return null;
        return answers;
    }

    _toNumeric(answer) {
        const out = {};
        for (const [k, v] of Object.entries(answer)) {
            const n = parseFloat(v);
            out[k] = isNaN(n) ? v : n;
        }
        return out;
    }

    isCorrect(answer) {
        if (!answer) return false;
        const rules = this.question.answer?.rules || [];
        if (!rules.length) return false;
        return _fevalEvaluateRules(rules, this._toNumeric(answer)).allCorrect;
    }

    showFeedback(isCorrect, message) {
        const answer          = this.getAnswer() || {};
        const rules           = this.question.answer?.rules || [];
        const { allCorrect, results } = _fevalEvaluateRules(rules, this._toNumeric(answer));

        this.container.querySelectorAll('.template-feval-answer').forEach(input => {
            input.classList.toggle('correct-answer',   allCorrect);
            input.classList.toggle('incorrect-answer', !allCorrect);
        });

        const feedbackMsg = message || (
            !allCorrect
                ? results.filter(r => !r.passed).map(r => r.feedback).join('<br>')
                : null
        );
        if (feedbackMsg && !isCorrect) super.showFeedback(isCorrect, feedbackMsg);
    }

    attachListeners() {
        if (this.readOnly) { this.disable(); return; }
        this.container.querySelectorAll('.template-feval-answer').forEach(input => {
            input.addEventListener('focus', () => input.closest('.template-feval-item')?.classList.add('focused'));
            input.addEventListener('blur',  () => input.closest('.template-feval-item')?.classList.remove('focused'));
        });
    }
}

// ── ALGEBRA ────────────────────────────────────────────────────────────────────
class TemplateHandlerALGEBRA extends TemplateHandler {
    getAnswer() {
        const input = this.container.querySelector('.template-algebra-input');
        const val = input ? input.value.trim() : '';
        return val || null;
    }

    _normalize(s) {
        return (s || '').replace(/\s+/g, '').toLowerCase();
    }

    _stringMatch(answer) {
        const accepted = this.question.answer?.accepted || [];
        const norm = this._normalize(answer);
        return accepted.some(a => this._normalize(a) === norm);
    }

    // Synchronous path — string match only (used by isAnswerCorrect in read-only/preview)
    isCorrect(answer) {
        if (!answer) return false;
        return this._stringMatch(answer);
    }

    // Async path — string match first, then optional sympy fallback
    async checkAsync(answer) {
        if (!answer) return false;
        if (this._stringMatch(answer)) return true;
        console.log('[ALGEBRA] string match failed, question.answer=', JSON.stringify(this.question.answer));
        if (!this.question.answer?.use_sympy) {
            console.log('[ALGEBRA] use_sympy is falsy — skipping sympy check');
            return false;
        }
        console.log('[ALGEBRA] sending to sympy:', { user_expr: answer, correct_expr: this.question.answer?.canonical, variables: this.question.answer?.variables });

        // Show validating indicator next to the input
        const input = this.container?.querySelector('.template-algebra-input');
        let indicator = null;
        if (input) {
            indicator = document.createElement('span');
            indicator.className = 'algebra-validating';
            indicator.textContent = 'Validating\u2026';
            input.insertAdjacentElement('afterend', indicator);
        }

        try {
            const res = await fetch('/quiz/api/check-expr-equiv', {
                method:  'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    user_expr:    answer,
                    correct_expr: this.question.answer?.canonical || '',
                    variables:    this.question.answer?.variables || [],
                }),
            });
            if (!res.ok) { console.log('[ALGEBRA] fetch not ok:', res.status); return false; }
            const data = await res.json();
            console.log('[ALGEBRA] sympy result:', data);
            return !!data.equivalent;
        } catch (err) {
            console.log('[ALGEBRA] fetch error:', err);
            return false;
        } finally {
            if (indicator) indicator.remove();
        }
    }

    showFeedback(isCorrect, message) {
        const input = this.container.querySelector('.template-algebra-input');
        if (input) {
            input.classList.toggle('correct-answer',   isCorrect);
            input.classList.toggle('incorrect-answer', !isCorrect);

            const wrapper = input.closest('.template-blank-wrapper');

            // Remove stale feedback rows
            (wrapper || input.parentElement).querySelectorAll('.blank-feedback-row').forEach(el => el.remove());

            // Build inline feedback row (✓/✗ + correct-answer hint)
            const feedbackRow = document.createElement('div');
            feedbackRow.className = 'blank-feedback-row';

            const icon = document.createElement('span');
            icon.className = `blank-feedback-icon ${isCorrect ? 'correct' : 'incorrect'}`;
            icon.textContent = isCorrect ? '\u2713' : '\u2717';
            feedbackRow.appendChild(icon);

            if (!isCorrect) {
                const firstCorrect = (this.question.answer?.accepted || [])[0] || '';
                if (firstCorrect) {
                    const hint = document.createElement('span');
                    hint.className = 'blank-correct-hint';
                    hint.innerHTML = 'correct answer: <span class="blank-correct-value">' + firstCorrect + '</span>';
                    feedbackRow.appendChild(hint);
                }
            }

            if (wrapper) {
                wrapper.appendChild(feedbackRow);
            } else {
                input.insertAdjacentElement('afterend', feedbackRow);
            }
        }
        if (message && !isCorrect) super.showFeedback(isCorrect, message);
    }

    attachListeners() {
        if (this.readOnly) { this.disable(); return; }
        const input = this.container.querySelector('.template-algebra-input');
        input?.addEventListener('focus', () => input.closest('.template-algebra-container')?.classList.add('focused'));
        input?.addEventListener('blur',  () => input.closest('.template-algebra-container')?.classList.remove('focused'));
    }
}

// ── Factory ────────────────────────────────────────────────────────────────────
function getTemplateHandler(type, container, question, readOnly) {
    const map = {
        MCQ:     TemplateHandlerMCQ,
        MR:      TemplateHandlerMR,
        FILL:    TemplateHandlerFILL,
        OHS:     TemplateHandlerOHS,
        FEVAL:   TemplateHandlerFEVAL,
        ALGEBRA: TemplateHandlerALGEBRA,
    };
    const Cls = map[type?.toUpperCase()] || TemplateHandler;
    return new Cls(container, question, readOnly);
}
