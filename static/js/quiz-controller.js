/**
 * Quiz Controller
 * Manages quiz flow in 'execution' and 'preview' modes.
 * Rendering is fully delegated to UnifiedQuestionComponent — single source of truth.
 *
 * Execution mode: /quiz/execute?user=X&quiz=Y
 *   - Saves each answer to the backend after submit.
 *   - Shows completion panel after the last question.
 *
 * Preview mode: quiz_preview.html
 *   - No DB writes; shows CLOSE after the last question.
 */

// ── Streak tier config ─────────────────────────────────────────────────────────
const STREAK_TIERS = [
    { min:   2, max:   9, flames: '\uD83D\uDD25',                                                         cls: 'tier-1' },
    { min:  10, max:  19, flames: '\uD83D\uDD25\uD83D\uDD25',                                             cls: 'tier-2' },
    { min:  20, max:  49, flames: '\uD83D\uDD25\uD83D\uDD25\uD83D\uDD25',                                 cls: 'tier-3' },
    { min:  50, max:  99, flames: '\uD83D\uDD25\uD83D\uDD25\uD83D\uDD25\uD83D\uDD25',                   cls: 'tier-4' },
    { min: 100, max: Infinity, flames: '\uD83D\uDD25\uD83D\uDD25\uD83D\uDD25\uD83D\uDD25\uD83D\uDD25', cls: 'tier-5' },
];


class QuizController {
    constructor(options = {}) {
        this.mode            = options.mode || 'execution';
        this.quizId          = options.quizId;
        this.userId          = options.userId;        // execution only
        this.questions       = options.questions || [];
        this.currentIndex    = options.startingIndex || 0;
        this.answeredIds     = new Set(options.answeredIds || []);
        this.alreadyComplete = options.alreadyComplete || false;
        this.onClose         = options.onClose || null;

        this.component    = null;

        // DOM refs — set in initialize()
        this._container    = null;
        this._submitBtn    = null;
        this._nextBtn      = null;
        this._closeBtn     = null;
        this._progressText = null;
        this._qIdBadge     = null;
        this._completion   = null;

        // Streak
        this.initialStreak    = options.initialStreak || 0;
        this._streakBadge     = null;
        this._streakHideTimer = null;
    }

    initialize() {
        this._container    = document.getElementById('questionContainer');
        this._submitBtn    = document.getElementById('submitBtn');
        this._nextBtn      = document.getElementById('nextBtn');
        this._closeBtn     = document.getElementById('closeBtn');
        this._progressText = document.getElementById('progressText');
        this._qIdBadge     = document.getElementById('questionIdBadge');
        this._completion   = document.getElementById('completionPanel');
        this._streakBadge  = document.getElementById('streakBadge');

        if (!this._container) {
            console.error('QuizController: #questionContainer not found');
            return;
        }

        this._submitBtn?.addEventListener('click', () => this._handleSubmit());
        this._nextBtn?.addEventListener('click',   () => this._handleNext());
        this._closeBtn?.addEventListener('click',  () => this._handleClose());

        document.addEventListener('keydown', (e) => {
            if (e.key !== 'Enter') return;
            if (this._submitBtn && !this._submitBtn.disabled && this._submitBtn.style.display !== 'none') {
                this._handleSubmit();
            }
        });
        document.getElementById('completionCloseBtn')
            ?.addEventListener('click', () => this._handleClose());
        document.getElementById('completionResetBtn')
            ?.addEventListener('click', () => this._handleReset());
        document.getElementById('calcBtn')
            ?.addEventListener('click', () => {
                const q = this.questions[this.currentIndex];
                const cfg = getCalculatorConfig(q);
                if (cfg.show) calculatorController.open(cfg);
            });

        if (this.alreadyComplete) {
            this._showAlreadyCompletePanel();
        } else {
            this._loadQuestion();
        }

        // Seed streak badge from server value (execution mode only)
        if (this.mode === 'execution') {
            this._updateStreak(this.initialStreak);
        }
    }

    // ── Question loading ────────────────────────────────────────────────────────

    _loadQuestion() {
        if (this.currentIndex < 0 || this.currentIndex >= this.questions.length) return;

        const question = this.questions[this.currentIndex];

        // Calculator: show/hide button and reset state
        const calcCfg = getCalculatorConfig(question);
        const calcBtn = document.getElementById('calcBtn');
        if (calcBtn) calcBtn.style.display = calcCfg.show ? 'inline-block' : 'none';
        if (calcCfg.show) {
            calculatorController.clearState();
        } else {
            calculatorController.close();
        }

        this._container.innerHTML = '';
        this._showBtn('submitBtn');
        this._hideBtn('nextBtn');
        this._hideBtn('closeBtn');
        this._submitBtn.disabled = false;
        this._updateProgress(question);

        this.component = new UnifiedQuestionComponent({
            question,
            container: this._container,
            readOnly:  false,
        });
        this.component.render();
    }

    // ── Submit flow ─────────────────────────────────────────────────────────────

    async _handleSubmit() {
        if (!this.component) return;

        const answer = this.component.getAnswer();
        if (!answer) {
            alert('Please provide an answer');
            return;
        }

        // Grey out submit immediately so it can't be double-clicked
        this._submitBtn.disabled = true;

        // Show feedback and lock the question inputs
        await this.component.submitAnswer();

        const question  = this.questions[this.currentIndex];
        const isCorrect = this.component.lastIsCorrect;
        const isLast    = this.currentIndex === this.questions.length - 1;

        if (this.mode === 'execution') {
            await this._saveAnswer(question, answer, isCorrect);
        }

        this._hideBtn('submitBtn');

        if (isLast && this.mode !== 'execution') {
            this._showBtn('closeBtn');
        } else {
            this._showBtn('nextBtn');
        }
    }

    _handleNext() {
        if (this.currentIndex === this.questions.length - 1 && this.mode === 'execution') {
            this._completeQuiz();
        } else if (this.currentIndex < this.questions.length - 1) {
            this.currentIndex++;
            this._loadQuestion();
        }
    }

    _handleClose() {
        if (this.onClose) {
            this.onClose('completed');
        } else if (this.mode === 'execution') {
            window.location.href = '/student-new';
        } else {
            window.location.href = '/';
        }
    }

    // ── Backend save ────────────────────────────────────────────────────────────

    async _completeQuiz() {
        try {
            const res  = await fetch('/quiz/api/complete-quiz', {
                method:  'POST',
                headers: { 'Content-Type': 'application/json' },
                body:    JSON.stringify({ user_id: this.userId, quiz_id: this.quizId }),
            });
            const data = res.ok ? await res.json() : {};
            const scoreText = (data.correct != null && data.total != null)
                ? `${data.correct} out of ${data.total}`
                : '';
            this._showCompletionWithScore(scoreText);
        } catch (err) {
            console.error('Error completing quiz:', err);
            this._showCompletionWithScore('');
        }
    }

    async _saveAnswer(question, answer, isCorrect) {
        try {
            const userAnswerStr    = this._answerToString(question, answer);
            const correctAnswerStr = this._extractCorrectAnswer(question);
            const payload = {
                user_id:           this.userId,
                quiz_id:           this.quizId,
                question_id:       question.id,
                question_sequence: this.currentIndex,
                user_answer:       userAnswerStr,
                correct_answer:    correctAnswerStr,
                is_correct:        isCorrect,
            };
            const res = await fetch('/quiz/api/submit-answer', {
                method:  'POST',
                headers: { 'Content-Type': 'application/json' },
                body:    JSON.stringify(payload),
            });
            if (res.ok) {
                const data = await res.json();
                this._updateStreak(data.streak ?? 0);
            } else {
                console.error('Failed to save answer, status:', res.status);
            }
        } catch (err) {
            console.error('Error saving answer:', err);
        }
    }

    _updateStreak(streak) {
        if (this.mode !== 'execution' || !this._streakBadge) return;
        clearTimeout(this._streakHideTimer);

        const flamesEl = document.getElementById('streakFlames');
        const countEl  = document.getElementById('streakCount');
        const wasVisible = this._streakBadge.style.display !== 'none';

        this._streakBadge.classList.remove('broken', 'tier-1', 'tier-2', 'tier-3', 'tier-4', 'tier-5');

        if (streak === 0) {
            if (wasVisible) {
                // 💔 flash before hiding
                flamesEl.textContent = '\uD83D\uDC94';
                countEl.textContent  = '+0';
                this._streakBadge.classList.add('broken');
                this._streakBadge.style.display = 'flex';
                this._streakHideTimer = setTimeout(() => {
                    this._streakBadge.style.display = 'none';
                    this._streakBadge.classList.remove('broken');
                }, 1200);
            }
            return;
        }

        const tier = STREAK_TIERS.find(t => streak >= t.min && streak <= t.max);
        if (!tier) {
            // Below minimum threshold — keep hidden
            this._streakBadge.style.display = 'none';
            return;
        }

        this._streakBadge.classList.add(tier.cls);
        flamesEl.textContent = tier.flames;
        countEl.textContent  = streak;
        this._streakBadge.style.display = 'flex';
    }

    /**
     * Look up option text by its id from question.input.options.
     */
    _optionText(question, optId) {
        const opt = (question.input?.options || []).find(o => (o.id || '') === String(optId));
        if (!opt) return String(optId);
        return typeof opt === 'string' ? opt : (opt.html || opt.latex || opt.text || String(optId));
    }

    /**
     * Get the display label for a FILL blank (prefers latex, strips HTML tags as fallback).
     */
    _blankLabel(blank, idx) {
        const raw = blank.input_label?.latex
            || blank.input_label?.html?.replace(/<[^>]*>/g, '')
            || blank.label
            || `Blank ${idx + 1}`;
        return raw.trim().replace(/:$/, '').trim();  // remove trailing colon for cleaner "Label: value" format
    }

    /**
     * Format one correct-answer entry from question.answer.correct[i].
     * Mirrors the logic in TemplateHandlerFILL._formatCorrectAnswer.
     */
    _formatCorrectEntry(entry) {
        if (!entry) return '';
        const rt = entry.response_type || 'text';
        if ((rt === 'fraction' || rt === 'simplest_fraction') && entry.accepted_fraction?.length) {
            const f = entry.accepted_fraction[0];
            return `${f.numerator}/${f.denominator}`;
        }
        if (rt === 'numeric' && entry.accepted_numeric?.length) {
            return String(entry.accepted_numeric[0]);
        }
        if (entry.accepted_text?.length) return entry.accepted_text[0];
        return '';
    }

    /**
     * Convert the raw answer (option id / id array / blank map) to a human-readable string.
     */
    _answerToString(question, answer) {
        const type = (question.type || '').toLowerCase();
        if (type === 'mcq') return this._optionText(question, answer);
        if (type === 'mr')  return Array.isArray(answer)
            ? answer.map(id => this._optionText(question, id)).join('; ')
            : String(answer);
        if (type === 'fill') {
            const blanks = question.input?.blanks || [];
            return blanks.map((blank, idx) => {
                const blankId = blank.id || `blank_${idx}`;
                const label   = this._blankLabel(blank, idx);
                const val     = (answer && answer[blankId] != null) ? answer[blankId] : '';
                return `${label}: ${val}`;
            }).join('; ');
        }
        // ohs / feval — answer is already a primitive or small object
        return typeof answer === 'object' ? JSON.stringify(answer) : String(answer);
    }

    /**
     * Extract the correct answer value from the question JSON as a human-readable string.
     */
    _extractCorrectAnswer(question) {
        const type = (question.type || '').toLowerCase();
        if (type === 'mcq') {
            const id = question.answer?.correct_option_id;
            return id != null ? this._optionText(question, id) : null;
        }
        if (type === 'mr') {
            const ids = question.answer?.correct_option_ids ?? [];
            return ids.map(id => this._optionText(question, id)).join('; ');
        }
        if (type === 'fill') {
            const blanks     = question.input?.blanks || [];
            const correctArr = question.answer?.correct || [];
            return blanks.map((blank, idx) => {
                const blankId = blank.id || `blank_${idx}`;
                const label   = this._blankLabel(blank, idx);
                // correct entries may be keyed by blank_id or simply ordered
                const entry   = correctArr.find(e => e.blank_id === blankId) ?? correctArr[idx];
                return `${label}: ${this._formatCorrectEntry(entry)}`;
            }).join('; ');
        }
        // ohs / feval — rules-based, no single correct value
        return null;
    }

    // ── UI helpers ──────────────────────────────────────────────────────────────

    _updateProgress(question) {
        const n = this.currentIndex + 1;
        const t = this.questions.length;
        if (this._progressText) this._progressText.textContent = `Question ${n} of ${t}`;
        if (this._qIdBadge)     this._qIdBadge.textContent = question?.id ? `[${question.id}]` : '';
    }

    _showCompletionPanel() {
        calculatorController.close();
        document.querySelector('.question-container')?.style.setProperty('display', 'none');
        document.querySelector('.button-row')?.style.setProperty('display', 'none');
        if (this._completion) this._completion.style.display = 'flex';
    }

    _showCompletionWithScore(scoreText) {
        const msgEl    = document.getElementById('completionMessage');
        const iconEl   = document.getElementById('completionIcon');
        const scoreEl  = document.getElementById('completionScore');
        const retakeEl = document.getElementById('completionRetake');
        if (msgEl)    msgEl.textContent  = 'Thank you for completing the quiz!';
        if (iconEl)   iconEl.textContent = '✓';
        if (scoreEl)  scoreEl.textContent = scoreText ? `You scored ${scoreText}.` : '';
        if (retakeEl) retakeEl.style.display = 'block';
        this._showCompletionPanel();
    }

    _showAlreadyCompletePanel() {
        const msgEl  = document.getElementById('completionMessage');
        const iconEl = document.getElementById('completionIcon');
        const resetBtn = document.getElementById('completionResetBtn');
        if (msgEl)   msgEl.textContent  = 'This quiz has already been completed.';
        if (iconEl)  iconEl.textContent = '✓';
        if (resetBtn) resetBtn.style.display = 'inline-block';
        this._showCompletionPanel();
    }

    async _handleReset() {
        const btn = document.getElementById('completionResetBtn');
        if (btn) { btn.disabled = true; btn.textContent = 'Resetting…'; }
        try {
            const res = await fetch('/quiz/api/reset-execution', {
                method:  'POST',
                headers: { 'Content-Type': 'application/json' },
                body:    JSON.stringify({ user_id: this.userId, quiz_id: this.quizId }),
            });
            if (res.ok) {
                window.location.reload();
            } else {
                alert('Reset failed. Please try again.');
                if (btn) { btn.disabled = false; btn.textContent = 'Reset & Retake'; }
            }
        } catch (err) {
            console.error('Reset error:', err);
            alert('Reset failed. Please try again.');
            if (btn) { btn.disabled = false; btn.textContent = 'Reset & Retake'; }
        }
    }

    _showBtn(id) {
        const el = document.getElementById(id);
        if (el) el.style.display = 'inline-block';
    }

    _hideBtn(id) {
        const el = document.getElementById(id);
        if (el) el.style.display = 'none';
    }

}
