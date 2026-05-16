/**
 * quiz-calculator.js
 * Provides getCalculatorConfig() and CalculatorController.
 * No external dependencies.
 */

'use strict';

/**
 * Parse calculator configuration from a question object.
 * Returns { show: false } when tools.calculator is absent.
 * Silently falls back to safe defaults for unknown types/modes.
 *
 * @param {object} question
 * @returns {{ show: boolean, type?: string, angleMode?: string }}
 */
function getCalculatorConfig(question) {
    const calc = question?.tools?.calculator;
    if (calc === undefined || calc === null) return { show: false };

    const VALID_TYPES = ['basic', 'scientific'];
    const VALID_MODES = ['degrees', 'radians'];

    return {
        show:      true,
        type:      VALID_TYPES.includes(calc.type)       ? calc.type       : 'basic',
        angleMode: VALID_MODES.includes(calc.angle_mode) ? calc.angle_mode : 'degrees',
    };
}

// ────────────────────────────────────────────────────────────────────────────────

class CalculatorController {
    constructor() {
        this._modal     = null;   // lazily resolved from DOM
        this._type      = 'basic';
        this._angleMode = 'degrees';
        this._resetState();
    }

    _resetState() {
        this._current   = '0';
        this._prevVal   = null;
        this._pendingOp = null;
        this._replace   = false;  // next digit replaces current display
    }

    // ── Public API ──────────────────────────────────────────────────────────────

    /**
     * Open the calculator modal with the given config.
     * Rebuilds the keypad if type or angleMode changed.
     * @param {{ type: string, angleMode: string }} config
     */
    open(config) {
        if (!this._resolve()) return;
        this._type      = config.type      || 'basic';
        this._angleMode = config.angleMode || 'degrees';
        this._resetState();
        this._build();
        this._refreshDisplay();
        this._modal.style.display = 'flex';
    }

    /** Close the modal without clearing state. */
    close() {
        if (this._resolve()) this._modal.style.display = 'none';
    }

    /** Reset calculator inputs (called when moving to a new question). */
    clearState() {
        this._resetState();
        this._refreshDisplay();
    }

    // ── DOM helpers ─────────────────────────────────────────────────────────────

    _resolve() {
        if (!this._modal) this._modal = document.getElementById('calcModal');
        return !!this._modal;
    }

    _refreshDisplay() {
        const el = document.getElementById('calcDisplay');
        if (el) el.textContent = this._current;
    }

    // ── Input dispatcher ────────────────────────────────────────────────────────

    _handle(action) {
        if      (action.startsWith('digit:'))  this._onDigit(action.slice(6));
        else if (action.startsWith('op:'))     this._onOp(action.slice(3));
        else if (action.startsWith('fn:'))     this._onFn(action.slice(3));
        else switch (action) {
            case 'clear':        this._resetState();      break;
            case 'equals':       this._onEquals();        break;
            case 'sign':         this._onSign();          break;
            case 'percent':      this._onPercent();       break;
            case 'back':         this._onBack();          break;
            case 'toggle-angle': this._onToggleAngle();   break;
        }
        this._refreshDisplay();
    }

    // ── Input handlers ──────────────────────────────────────────────────────────

    _onDigit(d) {
        if (this._current === 'Error') this._resetState();
        if (this._replace) {
            this._current = d === '.' ? '0.' : d;
            this._replace = false;
        } else if (d === '.') {
            if (!this._current.includes('.')) this._current += '.';
        } else {
            this._current = this._current === '0' ? d : this._current + d;
        }
    }

    _onOp(op) {
        if (this._current === 'Error') return;
        const cur = parseFloat(this._current);
        if (this._pendingOp !== null && !this._replace) {
            const result  = this._calc(this._prevVal, this._pendingOp, cur);
            this._current = this._fmt(result);
        }
        this._prevVal   = parseFloat(this._current);
        this._pendingOp = op;
        this._replace   = true;
    }

    _onEquals() {
        if (this._pendingOp === null || this._current === 'Error') return;
        const cur       = parseFloat(this._current);
        const result    = this._calc(this._prevVal, this._pendingOp, cur);
        this._current   = this._fmt(result);
        this._prevVal   = null;
        this._pendingOp = null;
        this._replace   = true;
    }

    _onFn(fn) {
        if (this._current === 'Error') return;
        const x = parseFloat(this._current);
        const toRad   = v => this._angleMode === 'degrees' ? v * Math.PI / 180 : v;
        const fromRad = v => this._angleMode === 'degrees' ? v * 180 / Math.PI : v;
        let r;
        switch (fn) {
            case 'sin':   r = Math.sin(toRad(x));     break;
            case 'cos':   r = Math.cos(toRad(x));     break;
            case 'tan':   r = Math.tan(toRad(x));     break;
            case 'asin':  r = fromRad(Math.asin(x));  break;
            case 'acos':  r = fromRad(Math.acos(x));  break;
            case 'atan':  r = fromRad(Math.atan(x));  break;
            case 'log':   r = Math.log10(x);          break;
            case 'ln':    r = Math.log(x);            break;
            case 'sqrt':  r = Math.sqrt(x);           break;
            case 'sq':    r = x * x;                  break;
            case 'cube':  r = x * x * x;              break;
            case 'inv':   r = x !== 0 ? 1 / x : NaN; break;
            case 'fact':  r = this._factorial(Math.round(x)); break;
            case 'pi':    this._current = String(Math.PI); this._replace = true; return;
            case 'e':     this._current = String(Math.E);  this._replace = true; return;
            case 'abs':   r = Math.abs(x);            break;
            case 'exp10': r = Math.pow(10, x);        break;
            case 'exp':   r = Math.exp(x);            break;
            default:      return;
        }
        this._current = (isFinite(r) && !isNaN(r)) ? this._fmt(r) : 'Error';
        this._replace = true;
    }

    _onSign() {
        if (this._current === '0' || this._current === 'Error') return;
        this._current = this._current.startsWith('-')
            ? this._current.slice(1)
            : '-' + this._current;
    }

    _onPercent() {
        if (this._current === 'Error') return;
        this._current = this._fmt(parseFloat(this._current) / 100);
        this._replace = true;
    }

    _onBack() {
        if (this._replace || this._current === 'Error') {
            this._resetState();
            return;
        }
        this._current = this._current.length > 1
            ? this._current.slice(0, -1)
            : '0';
    }

    _onToggleAngle() {
        this._angleMode = this._angleMode === 'degrees' ? 'radians' : 'degrees';
        const btn = document.getElementById('calcAngleToggle');
        if (btn) btn.textContent = this._angleMode === 'degrees' ? 'DEG' : 'RAD';
    }

    // ── Math ────────────────────────────────────────────────────────────────────

    _calc(a, op, b) {
        switch (op) {
            case '+': return a + b;
            case '-': return a - b;
            case '*': return a * b;
            case '/': return b !== 0 ? a / b : NaN;
            case '^': return Math.pow(a, b);
            default:  return b;
        }
    }

    _fmt(n) {
        if (!isFinite(n) || isNaN(n)) return 'Error';
        // Suppress floating-point noise by rounding to 10 sig figs
        return String(parseFloat(n.toPrecision(10)));
    }

    _factorial(n) {
        if (!isFinite(n) || n < 0 || n > 170) return NaN;
        let r = 1;
        for (let i = 2; i <= n; i++) r *= i;
        return r;
    }

    // ── UI builder ──────────────────────────────────────────────────────────────

    _build() {
        const wrap = document.getElementById('calcContainer');
        if (!wrap) return;
        wrap.innerHTML = '';

        // Title bar
        const titleBar = document.createElement('div');
        titleBar.className = 'calc-titlebar';
        titleBar.innerHTML =
            `<span>${this._type === 'scientific' ? 'Scientific Calculator' : 'Calculator'}</span>` +
            `<button type="button" class="calc-x" id="calcXBtn">&#10005;</button>`;
        wrap.appendChild(titleBar);

        // Display
        const dispWrap = document.createElement('div');
        dispWrap.className = 'calc-display-wrap';
        dispWrap.innerHTML = `<span class="calc-display" id="calcDisplay">0</span>`;
        wrap.appendChild(dispWrap);

        // Keypad
        const pad = document.createElement('div');
        pad.className = 'calc-pad';
        wrap.appendChild(pad);

        (this._type === 'scientific' ? this._sciKeys() : this._basicKeys())
            .forEach(k => {
                const btn = document.createElement('button');
                btn.type = 'button';
                btn.textContent = k.l;
                btn.className = 'calc-btn' + (k.c ? ' calc-' + k.c : '');
                btn.dataset.action = k.a;
                if (k.id)  btn.id = k.id;
                if (k.w2)  btn.style.gridColumn = 'span 2';
                pad.appendChild(btn);
            });

        // Angle button label must match current mode
        const angleBtn = document.getElementById('calcAngleToggle');
        if (angleBtn) angleBtn.textContent = this._angleMode === 'degrees' ? 'DEG' : 'RAD';

        // Close button
        document.getElementById('calcXBtn')
            ?.addEventListener('click', () => this.close());

        // Event delegation — one listener for all keypad buttons
        pad.addEventListener('click', e => {
            const btn = e.target.closest('[data-action]');
            if (btn) this._handle(btn.dataset.action);
        });
    }

    _basicKeys() {
        return [
            { l: 'C',  a: 'clear',   c: 'fn' },
            { l: '±',  a: 'sign',    c: 'fn' },
            { l: '%',  a: 'percent', c: 'fn' },
            { l: '÷',  a: 'op:/',    c: 'op' },
            { l: '7',  a: 'digit:7' },
            { l: '8',  a: 'digit:8' },
            { l: '9',  a: 'digit:9' },
            { l: '×',  a: 'op:*',   c: 'op' },
            { l: '4',  a: 'digit:4' },
            { l: '5',  a: 'digit:5' },
            { l: '6',  a: 'digit:6' },
            { l: '−',  a: 'op:-',   c: 'op' },
            { l: '1',  a: 'digit:1' },
            { l: '2',  a: 'digit:2' },
            { l: '3',  a: 'digit:3' },
            { l: '+',  a: 'op:+',   c: 'op' },
            { l: '0',  a: 'digit:0', w2: true },
            { l: '.',  a: 'digit:.' },
            { l: '=',  a: 'equals', c: 'op' },
        ];
    }

    _sciKeys() {
        return [
            // ── Scientific function rows (4 cols each) ──────────────────────────
            { l: 'sin',   a: 'fn:sin',        c: 'fn' },
            { l: 'cos',   a: 'fn:cos',        c: 'fn' },
            { l: 'tan',   a: 'fn:tan',        c: 'fn' },
            { l: 'DEG',   a: 'toggle-angle',  c: 'fn toggle', id: 'calcAngleToggle' },

            { l: 'sin⁻¹', a: 'fn:asin',       c: 'fn' },
            { l: 'cos⁻¹', a: 'fn:acos',       c: 'fn' },
            { l: 'tan⁻¹', a: 'fn:atan',       c: 'fn' },
            { l: 'π',     a: 'fn:pi',         c: 'fn' },

            { l: 'log',   a: 'fn:log',        c: 'fn' },
            { l: 'ln',    a: 'fn:ln',         c: 'fn' },
            { l: '√',     a: 'fn:sqrt',       c: 'fn' },
            { l: 'e',     a: 'fn:e',          c: 'fn' },

            { l: 'x²',    a: 'fn:sq',         c: 'fn' },
            { l: 'xʸ',    a: 'op:^',          c: 'fn' },
            { l: '1/x',   a: 'fn:inv',        c: 'fn' },
            { l: 'n!',    a: 'fn:fact',       c: 'fn' },

            // ── Standard numeric rows ───────────────────────────────────────────
            { l: 'C',  a: 'clear',   c: 'fn' },
            { l: '±',  a: 'sign',    c: 'fn' },
            { l: '⌫',  a: 'back',    c: 'fn' },
            { l: '÷',  a: 'op:/',    c: 'op' },

            { l: '7',  a: 'digit:7' },
            { l: '8',  a: 'digit:8' },
            { l: '9',  a: 'digit:9' },
            { l: '×',  a: 'op:*',   c: 'op' },

            { l: '4',  a: 'digit:4' },
            { l: '5',  a: 'digit:5' },
            { l: '6',  a: 'digit:6' },
            { l: '−',  a: 'op:-',   c: 'op' },

            { l: '1',  a: 'digit:1' },
            { l: '2',  a: 'digit:2' },
            { l: '3',  a: 'digit:3' },
            { l: '+',  a: 'op:+',   c: 'op' },

            { l: '0',  a: 'digit:0', w2: true },
            { l: '.',  a: 'digit:.' },
            { l: '=',  a: 'equals', c: 'op' },
        ];
    }
}

// ── Singleton accessible by quiz-controller.js ──────────────────────────────
const calculatorController = new CalculatorController();
