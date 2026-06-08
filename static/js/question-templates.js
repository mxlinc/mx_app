class QuestionTemplates {
    static _shuffle(arr) {
        const a = arr.slice();
        for (let i = a.length - 1; i > 0; i--) {
            const j = Math.floor(Math.random() * (i + 1));
            [a[i], a[j]] = [a[j], a[i]];
        }
        return a;
    }
    static MCQ(question) {
        const raw = question.input?.options || [];
        // shuffle defaults to true unless explicitly false
        const options = question.input?.shuffle !== false ? QuestionTemplates._shuffle(raw) : raw;
        const html = options.map((opt, idx) => {
            const optId = opt.id || `opt_${idx}`;
            const txt = typeof opt === 'string' ? opt : (opt.html || opt.latex || opt.text || '');
            return `<div class="template-option template-mcq-option"><input type="radio" id="${optId}" name="answer" value="${optId}" class="template-radio"><label for="${optId}" class="template-option-label">${txt}</label></div>`;
        }).join('');
        const img = question.image_url ? `<div class="template-image"><img src="${question.image_url}" alt="Question image"></div>` : '';
        return `<div class="template-question template-mcq"><div class="template-stem">${question.stem || ''}</div>${img}<div class="template-options-container template-mcq-options">${html}</div></div>`;
    }
    static MR(question) {
        const raw = question.input?.options || [];
        // shuffle defaults to true unless explicitly false
        const options = question.input?.shuffle !== false ? QuestionTemplates._shuffle(raw) : raw;
        const html = options.map((opt, idx) => {
            const optId = opt.id || `opt_${idx}`;
            const txt = typeof opt === 'string' ? opt : (opt.html || opt.latex || opt.text || '');
            return `<div class="template-option template-mr-option"><input type="checkbox" id="${optId}" value="${optId}" class="template-checkbox"><label for="${optId}" class="template-option-label">${txt}</label></div>`;
        }).join('');
        const img = question.image_url ? `<div class="template-image"><img src="${question.image_url}" alt="Question image"></div>` : '';
        const numCorrect = (question.answer?.correct_option_ids || []).length;
        const hint = numCorrect > 0
            ? `<p class="template-mr-hint">Select ${numCorrect} correct option${numCorrect > 1 ? 's' : ''}</p>`
            : '';
        return `<div class="template-question template-mr"><div class="template-stem">${question.stem || ''}</div>${img}${hint}<div class="template-options-container template-mr-options">${html}</div></div>`;
    }
    static FILL(question) {
        const blanks = question.input?.blanks || [];
        const html = blanks.map((blank, idx) => {
            const blankId      = typeof blank === 'string' ? blank : (blank.id || `blank_${idx}`);
            const labelText    = typeof blank === 'string'
                ? `Blank ${idx + 1}:`
                : (blank.input_label?.html || blank.input_label?.latex || blank.label || `Blank ${idx + 1}:`);
            const labelAfter   = typeof blank === 'object' ? (blank.label_after?.html || blank.label_after?.latex || '') : '';
            const placeholder  = (typeof blank === 'object' && blank.placeholder) ? blank.placeholder : 'Enter answer';
            const responseType = (typeof blank === 'object' && blank.response_type) ? blank.response_type : 'text';
            const isInline     = !!labelAfter;

            let inputHtml;
            if (responseType === 'fraction' || responseType === 'simplest_fraction') {
                inputHtml = `<div class="template-fraction-input" data-blank-id="${blankId}"><input type="number" class="template-fraction-num" placeholder="" step="1"><div class="template-fraction-bar"></div><input type="number" class="template-fraction-den" placeholder="" step="1"></div>`;
            } else {
                const inputType  = responseType === 'numeric' ? 'number' : 'text';
                const widthStyle = isInline ? (responseType === 'numeric' ? 'width:120px' : 'width:160px') : '';
                inputHtml = `<input type="${inputType}" id="${blankId}" class="template-blank-input" placeholder="" data-blank-id="${blankId}"${responseType === 'numeric' ? ' step="any"' : ''}${widthStyle ? ` style="${widthStyle}"` : ''}>`;
            }

            if (isInline) {
                return `<div class="template-blank-wrapper template-blank-inline"><span class="template-blank-label">${labelText}</span>${inputHtml}<span class="template-blank-label-after">${labelAfter}</span></div>`;
            }
            return `<div class="template-blank-wrapper"><label class="template-blank-label">${labelText}</label>${inputHtml}</div>`;
        }).join('<div style="height: 1.2em;"></div>');
        const img = question.image_url ? `<div class="template-image"><img src="${question.image_url}" alt="Question image"></div>` : '';
        return `<div class="template-question template-fill"><div class="template-stem">${question.stem || ''}</div>${img}<div class="template-blanks-container">${html}</div></div>`;
    }
    static OHS(question) {
        if (!question.image_url) return '<div class="template-question template-ohs template-error">No image</div>';
        return `<div class="template-question template-ohs"><div class="template-stem">${question.stem || ''}</div><div class="template-ohs-container"><img id="template-ohs-image" src="${question.image_url}" alt="Question image" class="template-ohs-image" usemap="#ohs-map"><svg id="template-ohs-overlay" class="template-ohs-overlay" style="position: absolute; top: 0; left: 0;"></svg></div></div>`;
    }
    static FEVAL(question) {
        const blanks = question.input?.blanks || [];
        const html = blanks.map((blank, idx) => {
            const evalId = blank.variable_name || `var_${idx}`;
            const label  = blank.label || blank.variable_name || `Input ${idx + 1}`;
            return `<div class="template-feval-item"><div class="template-feval-input">${label}</div><input type="text" id="feval_${evalId}" class="template-feval-answer" placeholder="Enter value" data-eval-id="${evalId}"></div>`;
        }).join('');
        return `<div class="template-question template-feval"><div class="template-stem">${question.stem || ''}</div><div class="template-feval-container">${html}</div></div>`;
    }
    static ALGEBRA(question) {
        const labelBefore = question.input_label?.html || question.input_label?.latex || '';
        const labelAfter  = question.label_after?.html  || question.label_after?.latex  || '';
        const img = question.image_url ? `<div class="template-image"><img src="${question.image_url}" alt="Question image"></div>` : '';
        const inputEl = `<input type="text" id="algebra-answer" class="template-algebra-input"
                       autocomplete="off" autocorrect="off" autocapitalize="off" spellcheck="false">`;
        let fieldHtml;
        if (labelAfter) {
            fieldHtml = `<div class="template-blank-wrapper template-blank-inline">${labelBefore ? `<span class="template-blank-label">${labelBefore}</span>` : ''}${inputEl}<span class="template-blank-label-after">${labelAfter}</span></div>`;
        } else if (labelBefore) {
            fieldHtml = `<div class="template-blank-wrapper"><label class="template-blank-label">${labelBefore}</label>${inputEl}</div>`;
        } else {
            fieldHtml = inputEl;
        }
        return `<div class="template-question template-algebra"><div class="template-stem">${question.stem || ''}</div>${img}<div class="template-algebra-container">${fieldHtml}</div></div>`;
    }
    static getTemplate(question) {
        const q = Object.assign({}, question);
        if (q.stem && typeof q.stem === 'object') {
            q.stem = q.stem.html || q.stem.latex || q.stem.text || '';
        }
        // Normalise image: accept both image.src (backend) and image_url (legacy flat)
        if (!q.image_url && q.image?.src) {
            q.image_url = q.image.src;
        }
        const type = q.type?.toUpperCase();
        const template = this[type];
        if (!template) {
            console.warn('No template: ' + type);
            return '<div class="template-error">Unknown: ' + type + '</div>';
        }
        return template.call(this, q);
    }
}


// Ensure globally available
if (typeof window !== 'undefined') { window.QuestionTemplates = QuestionTemplates; }
