/**
 * quiz-builder-form.js
 *
 * Shared builder logic used by both the standalone quiz builder page
 * (/question/builder) and the quiz question editor (/quiz/<id>/question-editor).
 *
 * Requires these globals to already be loaded:
 *   QuizMCQ (quiz-mcq.js), QuizMR (quiz-mr.js),
 *   addBlankUI, getFILLQuestion (quiz-fill.js),
 *   addFEVALVariable, addFEVALRule, collectFEVALData (quiz-feval.js)
 *
 * The page that includes this file must call initBuilderForm() after DOMContentLoaded.
 *
 * Hook: set window.onQuestionSaved = function(result) { ... } BEFORE calling
 * initBuilderForm() to override the default post-save redirect behaviour.
 * Signature: window.onQuestionSaved(result) where result = { ok, question_id, message, ... }
 */

// ===== State Management =====
let lastQuestion = {
    topic: '',
    subtopic: '',
    level: '',
    type: 'mcq'
};

let editingQuestionId = null;
let editingQuestionImage = null;

// ===== URL Parameter Handling =====
function getQueryParam(param) {
    const urlParams = new URLSearchParams(window.location.search);
    return urlParams.get(param);
}

// ===== Algebra Data Collection =====
function collectAlgebraData() {
    const accepted = document.getElementById('algebra-accepted').value
        .split('|')
        .map(s => s.replace(/\s+/g, ''))   // strip all spaces
        .filter(s => s.length > 0);
    const canonical  = document.getElementById('algebra-canonical').value.trim();
    const variables  = document.getElementById('algebra-variables').value
        .split(',')
        .map(s => s.trim())
        .filter(s => s.length > 0);
    const useSympy   = document.getElementById('algebra-use-sympy').checked;

    if (accepted.length === 0) throw new Error('Enter at least one accepted answer string');
    if (useSympy && !canonical)             throw new Error('Canonical form is required');
    if (useSympy && variables.length === 0)  throw new Error('Declare at least one variable (e.g. x)');

    // Parse label field: "label before | label after"
    const labelRaw    = document.getElementById('algebra-label').value;
    const pipeParts   = labelRaw.split('|');
    const labelBefore = pipeParts[0].trim();
    const labelAfter  = (pipeParts[1] || '').trim();

    const q = {
        type: 'algebra',
        stem: { latex: document.getElementById('stem_latex').value },
        answer: { accepted, canonical, variables, use_sympy: useSympy },
    };
    if (labelBefore) {
        q.input_label = { latex: labelBefore };
        if (labelAfter) q.label_after = { latex: labelAfter };
    }
    const fb = document.getElementById('feedback_latex').value.trim();
    if (fb) q.feedback = { latex: fb };
    return q;
}

// ===== Image Handling =====
function handleImagePreview() {
    const imageInput = document.getElementById('image');
    const file = imageInput.files[0];
    if (file && file.type.startsWith('image/')) {
        const reader = new FileReader();
        reader.onload = (e) => {
            const preview = document.getElementById('imagePreview');
            preview.src = e.target.result;
            preview.style.display = 'block';

            // If OHS type, initialize canvas
            if (document.getElementById('questionType').value.toLowerCase() === 'ohs') {
                setTimeout(() => {
                    initializeOHSCanvas();
                }, 100);
            }
        };
        reader.readAsDataURL(file);
        editingQuestionImage = null; // Clear cached server image when new file selected
    }
}

// ===== Messaging =====
function showMessage(text, type) {
    const messageDiv = document.getElementById('message');
    messageDiv.textContent = text;
    messageDiv.className = 'message show ' + type;

    // Auto-hide success messages after 3 seconds
    if (type === 'success') {
        setTimeout(() => {
            messageDiv.classList.remove('show');
        }, 3000);
    }
}

// ===== Data Collection =====
function collectImageDataUrl() {
    return new Promise((resolve) => {
        const fileInput = document.getElementById('image');
        if (!fileInput.files[0]) {
            resolve(null);
            return;
        }
        const reader = new FileReader();
        reader.onload = (e) => resolve(e.target.result);
        reader.readAsDataURL(fileInput.files[0]);
    });
}

async function collectData() {
    /**
     * Strip leading option labels like A), B), 1), etc. from option text
     */
    function stripOptionLabel(text) {
        // Match patterns like: A), a), 1), (A), etc.
        return text.replace(/^[\s]*([A-Za-z0-9]+\s*[\)\)]|[\(\s]*[A-Za-z0-9]+\s*[\)\)])\s*/g, '').trim();
    }

    const questionType = document.getElementById('questionType').value.toLowerCase();

    let question;
    if (questionType === 'mcq') {
        // Collect MCQ data
        question = {
            type: 'mcq',
            stem: { latex: document.getElementById('stem_latex').value },
            input: {
                options: document.getElementById('options').value
                    .split('\n')
                    .filter(o => o.trim())
                    .map((o, i) => ({ id: `opt${i+1}`, latex: stripOptionLabel(o) })),
                shuffle: document.getElementById('shuffle').checked
            },
            answer: {}
        };

        // Add feedback if provided
        const feedbackLatex = document.getElementById('feedback_latex').value.trim();
        if (feedbackLatex) {
            question.stem.feedback = { latex: feedbackLatex };
        }

        // Determine correct option
        const customCorrect = document.getElementById('correct').value.trim();
        if (customCorrect) {
            const strippedCorrect = stripOptionLabel(customCorrect);
            const matchingOption = question.input.options.find(opt =>
                opt.latex === strippedCorrect
            );
            if (matchingOption) {
                question.answer.correct_option_id = matchingOption.id;
            } else {
                question.answer.correct_option_id = 'opt1';
            }
        } else {
            question.answer.correct_option_id = 'opt1';
        }
    } else if (questionType === 'mr') {
        // Collect MR data
        question = {
            type: 'mr',
            stem: { latex: document.getElementById('stem_latex').value },
            input: {
                options: document.getElementById('mr-options').value
                    .split('\n')
                    .filter(o => o.trim())
                    .map((o, i) => ({ id: `opt${i+1}`, latex: stripOptionLabel(o) })),
                shuffle: document.getElementById('mr-shuffle').checked
            },
            answer: {}
        };

        // Add feedback if provided
        const feedbackLatex = document.getElementById('feedback_latex').value.trim();
        if (feedbackLatex) {
            question.stem.feedback = { latex: feedbackLatex };
        }

        // Get checked correct options
        const checkedCorrect = Array.from(document.querySelectorAll('#mr-correct-options input[type="checkbox"]:checked'))
            .map(checkbox => checkbox.value);

        if (checkedCorrect.length < 2) {
            throw new Error('MR questions require at least 2 correct options');
        }

        question.answer.correct_option_ids = checkedCorrect;
    } else if (questionType === 'fill') {
        // Collect FILL data
        question = getFILLQuestion();
    } else if (questionType === 'feval') {
        // Collect FEVAL data
        question = collectFEVALData();
    } else if (questionType === 'algebra') {
        question = collectAlgebraData();
    } else if (questionType === 'ohs') {
        // Collect OHS data
        if (!ohsHotspot) {
            throw new Error('OHS questions require a hotspot. Please draw a rectangle on the image.');
        }

        question = {
            type: 'ohs',
            input: {},
            image: {
                alt: '',
                hotspot: {
                    id: 'hs1',
                    x: Math.round(ohsHotspot.x),
                    y: Math.round(ohsHotspot.y),
                    width: Math.round(ohsHotspot.width),
                    height: Math.round(ohsHotspot.height)
                }
            },
            answer: {
                correct_hotspot_id: 'hs1'
            }
        };

        // Add stem if provided
        const stemLatex = document.getElementById('stem_latex').value.trim();
        if (stemLatex) {
            question.stem = { latex: stemLatex };

            // Add feedback if provided
            const feedbackLatex = document.getElementById('feedback_latex').value.trim();
            if (feedbackLatex) {
                question.stem.feedback = { latex: feedbackLatex };
            }
        }
    } else {
        throw new Error(`Unknown question type: ${questionType}`);
    }

    const imageDataUrl = await collectImageDataUrl();

    return {
        type: questionType,
        topic: document.getElementById('topic').value,
        subtopic: document.getElementById('subtopic').value,
        level: document.getElementById('level').value,
        question: question,
        image_data_url: imageDataUrl,
        id: editingQuestionId
    };
}

// ===== Save Flow =====
async function save() {
    try {
        const data = await collectData();

        // Type-specific validation
        let validator;
        const questionType = data.type.toUpperCase();

        switch (questionType) {
            case 'MCQ':
                validator = new QuizMCQ({showMessage: showMessage});
                break;
            case 'MR':
                validator = new QuizMR({showMessage: showMessage});
                break;
            case 'FILL':
                validator = { validate: () => true };
                break;
            case 'FEVAL':
                validator = { validate: () => true };
                break;
            case 'ALGEBRA':
                validator = { validate: () => true };
                break;
            case 'OHS':
                // OHS questions need image on CREATE, but not on EDIT if image already exists
                if (!data.image_data_url && !data.id) {
                    showMessage('✗ OHS questions require an image. Please upload one.', 'error');
                    return;
                }
                validator = { validate: () => true };
                break;
            default:
                showMessage('✗ Unknown question type: ' + questionType, 'error');
                return;
        }

        // Validate before saving
        if (!validator.validate(data)) {
            return; // Validation errors already displayed
        }

        const response = await fetch('/question/api/save', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });
        const text = await response.text();
        let result;
        try {
            result = JSON.parse(text);
        } catch (parseError) {
            showMessage('✗ Error saving question: server returned non-JSON response.', 'error');
            console.error('Server response:', text);
            return;
        }

        if (result.ok) {
            showMessage('✓ ' + result.message, 'success');
            // Save state for next question
            lastQuestion = {
                topic: data.topic,
                subtopic: data.subtopic,
                level: data.level,
                type: 'mcq'
            };
            if (result.question_id) {
                if (typeof window.onQuestionSaved === 'function') {
                    // Custom hook — e.g. quiz editor refreshes the right panel
                    window.onQuestionSaved(result);
                } else {
                    // Default: navigate to full-screen display page
                    setTimeout(() => {
                        window.location.href = `/question/display/${result.question_id}`;
                    }, 500);
                }
            }
        } else {
            const errorMessage = result.errors ? result.errors.join('; ') : 'Error saving question';
            showMessage('✗ ' + errorMessage, 'error');
        }
    } catch (error) {
        showMessage('✗ Error saving question: ' + error.message, 'error');
        console.error('Save error:', error);
    }
}

// ===== MR Correct Options Management =====
function updateMRCorrectOptions() {
    function stripOptionLabel(text) {
        return text.replace(/^[\s]*([A-Za-z0-9]+\s*[\)\)]|[\(\s]*[A-Za-z0-9]+\s*[\)\)])\s*/g, '').trim();
    }

    const optionsText = document.getElementById('mr-options').value;
    const options = optionsText.split('\n').filter(o => o.trim());
    const container = document.getElementById('mr-correct-options');

    if (options.length === 0) {
        container.innerHTML = '<p style="color: #999; text-align: center; margin: 30px 0;">Enter options above to select correct ones</p>';
        return;
    }

    const checkboxesHtml = options.map((opt, i) => {
        const optId = `opt${i+1}`;
        const strippedOpt = stripOptionLabel(opt);
        return `
            <div style="margin-bottom: 8px; display: flex; align-items: center; gap: 8px;">
                <input type="checkbox" id="correct_${optId}" value="${optId}" style="cursor: pointer;">
                <label for="correct_${optId}" style="cursor: pointer; margin: 0; flex: 1;">${strippedOpt}</label>
            </div>
        `;
    }).join('');

    container.innerHTML = checkboxesHtml;
}

// ===== OHS (One HotSpot) Handlers =====
let ohsHotspot = null;  // Stores current hotspot: {x, y, width, height}
let ohsDrawing = false;
let ohsStartX, ohsStartY;

function initializeOHSCanvas() {
    const imagePreview = document.getElementById('imagePreview');
    const canvas = document.getElementById('ohsCanvas');
    const placeholder = document.getElementById('ohsCanvasPlaceholder');

    if (!imagePreview || !imagePreview.src) {
        canvas.style.display = 'none';
        placeholder.style.display = 'block';
        return;
    }

    // Load image and set up canvas
    const img = new Image();
    img.onload = () => {
        canvas.width = img.width;
        canvas.height = img.height;
        canvas.style.display = 'block';
        placeholder.style.display = 'none';

        // Draw image on canvas
        const ctx = canvas.getContext('2d');
        ctx.drawImage(img, 0, 0);

        // Draw existing hotspot if any
        if (ohsHotspot) {
            drawHotspotRect(ohsHotspot);
        }

        // Re-attach event listeners
        attachOHSCanvasListeners();
    };
    img.src = imagePreview.src;
}

function attachOHSCanvasListeners() {
    const canvas = document.getElementById('ohsCanvas');

    canvas.addEventListener('mousedown', (e) => {
        ohsDrawing = true;
        const rect = canvas.getBoundingClientRect();
        ohsStartX = e.clientX - rect.left;
        ohsStartY = e.clientY - rect.top;
    });

    canvas.addEventListener('mousemove', (e) => {
        if (!ohsDrawing) return;

        const rect = canvas.getBoundingClientRect();
        const currentX = e.clientX - rect.left;
        const currentY = e.clientY - rect.top;

        // Redraw canvas
        const imagePreview = document.getElementById('imagePreview');
        const img = new Image();
        img.onload = () => {
            const ctx = canvas.getContext('2d');
            ctx.clearRect(0, 0, canvas.width, canvas.height);
            ctx.drawImage(img, 0, 0);

            // Draw preview rectangle
            const width = currentX - ohsStartX;
            const height = currentY - ohsStartY;
            drawHotspotRect({
                x: width < 0 ? currentX : ohsStartX,
                y: height < 0 ? currentY : ohsStartY,
                width: Math.abs(width),
                height: Math.abs(height)
            }, true);
        };
        img.src = imagePreview.src;
    });

    canvas.addEventListener('mouseup', (e) => {
        if (!ohsDrawing) return;
        ohsDrawing = false;

        const rect = canvas.getBoundingClientRect();
        const endX = e.clientX - rect.left;
        const endY = e.clientY - rect.top;

        // Calculate hotspot coordinates
        const x = Math.min(ohsStartX, endX);
        const y = Math.min(ohsStartY, endY);
        const width = Math.abs(endX - ohsStartX);
        const height = Math.abs(endY - ohsStartY);

        if (width > 10 && height > 10) {  // Minimum size threshold
            ohsHotspot = { x, y, width, height };
            updateOHSDisplay();
        } else {
            showMessage('Hotspot too small. Please draw a larger rectangle.', 'error');
        }
    });

    canvas.addEventListener('mouseleave', () => {
        ohsDrawing = false;
    });
}

function drawHotspotRect(hotspot, isPreview = false) {
    const canvas = document.getElementById('ohsCanvas');
    const ctx = canvas.getContext('2d');

    // Draw rectangle
    ctx.strokeStyle = isPreview ? 'rgba(255, 193, 7, 0.7)' : 'rgba(76, 175, 80, 0.7)';
    ctx.lineWidth = 2;
    ctx.strokeRect(hotspot.x, hotspot.y, hotspot.width, hotspot.height);

    // Fill with semi-transparent color
    ctx.fillStyle = isPreview ? 'rgba(255, 193, 7, 0.1)' : 'rgba(76, 175, 80, 0.1)';
    ctx.fillRect(hotspot.x, hotspot.y, hotspot.width, hotspot.height);
}

function updateOHSDisplay() {
    const coordsDisplay = document.getElementById('ohsCoordinatesDisplay');
    const clearBtn = document.getElementById('ohsClearBtn');

    if (ohsHotspot) {
        document.getElementById('ohsCoordX').textContent = Math.round(ohsHotspot.x);
        document.getElementById('ohsCoordY').textContent = Math.round(ohsHotspot.y);
        document.getElementById('ohsCoordW').textContent = Math.round(ohsHotspot.width);
        document.getElementById('ohsCoordH').textContent = Math.round(ohsHotspot.height);

        coordsDisplay.style.display = 'block';
        clearBtn.style.display = 'inline-block';
        showMessage('✓ Hotspot defined!', 'success');
    } else {
        coordsDisplay.style.display = 'none';
        clearBtn.style.display = 'none';
    }
}

// ===== Clear Form =====
function clearForm() {
    document.getElementById('stem_latex').value = '';
    document.getElementById('feedback_latex').value = '';
    document.getElementById('options').value = '';
    document.getElementById('correct').value = '';
    document.getElementById('mr-options').value = '';
    document.getElementById('mr-shuffle').checked = true;
    document.getElementById('image').value = '';
    document.getElementById('imagePreview').style.display = 'none';
    document.getElementById('discardImageBtn').style.display = 'none';
    document.getElementById('shuffle').checked = true;

    // Clear MR correct options
    document.getElementById('mr-correct-options').innerHTML = '<p style="color: #999; text-align: center; margin: 30px 0;">Enter options above to select correct ones</p>';

    // Clear FILL blanks
    const fillBlankContainer = document.getElementById('fill-blanks-container');
    if (fillBlankContainer) {
        fillBlankContainer.innerHTML = '';
    }

    // Clear OHS hotspot
    ohsHotspot = null;
    const ohsCanvas = document.getElementById('ohsCanvas');
    if (ohsCanvas) {
        ohsCanvas.style.display = 'none';
    }
    const ohsPlaceholder = document.getElementById('ohsCanvasPlaceholder');
    if (ohsPlaceholder) {
        ohsPlaceholder.style.display = 'block';
    }
    const coordsDisplay = document.getElementById('ohsCoordinatesDisplay');
    if (coordsDisplay) {
        coordsDisplay.style.display = 'none';
    }
    const clearBtn = document.getElementById('ohsClearBtn');
    if (clearBtn) {
        clearBtn.style.display = 'none';
    }

    // Clear FEVAL variables and rules
    const fevalVarsContainer = document.getElementById('feval-variables-container');
    if (fevalVarsContainer) {
        fevalVarsContainer.innerHTML = '';
    }
    const fevalRulesContainer = document.getElementById('feval-rules-container');
    if (fevalRulesContainer) {
        fevalRulesContainer.innerHTML = '';
    }

    editingQuestionId = null;
    editingQuestionImage = null;
    document.getElementById('editModeBar').style.display = 'none';
    document.getElementById('message').classList.remove('show');
}

// ===== Discard Flow =====
function discard() {
    // Save current metadata
    lastQuestion = {
        topic: document.getElementById('topic').value,
        subtopic: document.getElementById('subtopic').value,
        level: document.getElementById('level').value,
        type: document.getElementById('questionType').value.toLowerCase()
    };

    // Clear form
    clearForm();

    // Restore metadata
    document.getElementById('topic').value = lastQuestion.topic;
    document.getElementById('subtopic').value = lastQuestion.subtopic;
    document.getElementById('level').value = lastQuestion.level;

    // Clear edit mode if present
    if (editingQuestionId) {
        editingQuestionId = null;
        editingQuestionImage = null;
        document.getElementById('editModeBar').style.display = 'none';
    }

    showMessage('✓ Question discarded. Metadata retained.', 'success');
}

// ===== Discard Image =====
function discardImage() {
    document.getElementById('image').value = '';
    document.getElementById('imagePreview').style.display = 'none';
    document.getElementById('discardImageBtn').style.display = 'none';
    editingQuestionImage = null;
    showMessage('✓ Image removed.', 'success');
}

// ===== Load Question for Editing =====
async function loadQuestionForEdit(questionId) {
    try {
        const response = await fetch(`/question/api/display/${questionId}`);
        const data = await response.json();

        if (!data.ok) {
            showMessage('✗ Failed to load question', 'error');
            return;
        }

        const question = data.question;

        editingQuestionId = questionId;

        // Show edit mode bar
        document.getElementById('editModeBar').style.display = 'block';
        document.getElementById('displayId').textContent = questionId;
        const previewBtn = document.getElementById('previewBtn');
        if (previewBtn) previewBtn.href = `/question/display/${questionId}`;

        // Populate common fields
        const stemValue = question.stem?.latex || question.stem || '';
        document.getElementById('stem_latex').value = stemValue;

        // Populate feedback if present
        const feedbackValue = question.stem?.feedback?.latex || question.feedback?.latex || '';
        document.getElementById('feedback_latex').value = feedbackValue;

        document.getElementById('topic').value = data.topic || '';
        document.getElementById('subtopic').value = data.subtopic || '';
        document.getElementById('level').value = data.level || '';

        const questionType = (data.type || 'mcq').toLowerCase();

        // Switch the type dropdown
        document.getElementById('questionType').value = questionType;
        // Trigger the change event to show the correct section
        const changeEvent = new Event('change', { bubbles: true });
        document.getElementById('questionType').dispatchEvent(changeEvent);

        // Handle image
        if (question.image?.src) {
            editingQuestionImage = question.image.src;
            const preview = document.getElementById('imagePreview');
            preview.src = editingQuestionImage;
            preview.style.display = 'block';
            document.getElementById('discardImageBtn').style.display = 'block';
        }

        // Load type-specific fields
        if (questionType === 'mcq') {
            if (question.input?.options) {
                document.getElementById('options').value = question.input.options
                    .map(o => o.latex)
                    .join('\n');
            }
            document.getElementById('shuffle').checked = question.input?.shuffle !== false;
            const correctId = question.answer?.correct_option_id;
            const correctOpt = (question.input?.options || []).find(o => o.id === correctId);
            document.getElementById('correct').value = correctOpt ? correctOpt.latex : '';
        } else if (questionType === 'mr') {
            if (question.input?.options) {
                document.getElementById('mr-options').value = question.input.options
                    .map(o => o.latex)
                    .join('\n');
            }
            document.getElementById('mr-shuffle').checked = question.input?.shuffle !== false;

            updateMRCorrectOptions();
            const correctIds = question.answer?.correct_option_ids || [];
            correctIds.forEach(id => {
                const checkbox = document.getElementById(`correct_${id}`);
                if (checkbox) {
                    checkbox.checked = true;
                }
            });
        } else if (questionType === 'fill') {
            const blanksContainer = document.getElementById('fill-blanks-container');
            if (blanksContainer) {
                blanksContainer.innerHTML = '';

                if (question.input?.blanks && Array.isArray(question.input.blanks)) {
                    question.input.blanks.forEach((blank, idx) => {
                        addBlankUI();
                        const blankEl = blanksContainer.querySelector('.fill-blank:last-child');

                        if (blankEl) {
                            const _lbefore = blank.input_label?.latex || '';
                            const _lafter  = blank.label_after?.latex  || '';
                            blankEl.querySelector('.blank-label-latex').value = _lafter ? `${_lbefore} | ${_lafter}` : _lbefore;
                            blankEl.querySelector('.blank-response-type').value = blank.response_type || 'text';
                            blankEl.querySelector('.blank-placeholder').value = blank.placeholder || '';

                            const correctAnswer = question.answer?.correct?.[idx];
                            if (correctAnswer) {
                                if (correctAnswer.response_type === 'text' && correctAnswer.accepted_text) {
                                    blankEl.querySelector('.blank-correct-answers').value = correctAnswer.accepted_text.join('\n');
                                    blankEl.querySelector('.blank-case-sensitive').checked = correctAnswer.case_sensitive !== false;
                                } else if (correctAnswer.response_type === 'numeric' && correctAnswer.accepted_numeric) {
                                    blankEl.querySelector('.blank-correct-answers').value = correctAnswer.accepted_numeric.join(', ');
                                } else if (correctAnswer.response_type === 'fraction' && correctAnswer.accepted_fraction) {
                                    blankEl.querySelector('.blank-correct-answers').value = correctAnswer.accepted_fraction
                                        .map(f => `${f.numerator}/${f.denominator}`)
                                        .join('\n');
                                }
                            }

                            const textOptions = blankEl.querySelector('.text-options-only');
                            if (textOptions) {
                                textOptions.style.display = blank.response_type === 'text' ? 'block' : 'none';
                            }
                        }
                    });
                }
            }
        } else if (questionType === 'ohs') {
            if (question.image?.hotspot) {
                ohsHotspot = question.image.hotspot;
                updateOHSDisplay();
                setTimeout(() => {
                    initializeOHSCanvas();
                }, 100);
            }
        } else if (questionType === 'feval') {
            if (question.input?.blanks && Array.isArray(question.input.blanks)) {
                const varsContainer = document.getElementById('feval-variables-container');
                if (varsContainer) {
                    varsContainer.innerHTML = '';

                    question.input.blanks.forEach((blank, blankIdx) => {
                        addFEVALVariable();
                        const varEl = varsContainer.children[varsContainer.children.length - 1];

                        if (varEl) {
                            const nameInput = varEl.querySelector('input.feval-var-name');
                            const labelInput = varEl.querySelector('input.feval-var-label');
                            if (nameInput) nameInput.value = blank.variable_name || '';
                            if (labelInput) labelInput.value = blank.label || '';
                        }
                    });
                }
            }

            if (question.answer?.rules && Array.isArray(question.answer.rules)) {
                const rulesContainer = document.getElementById('feval-rules-container');
                if (rulesContainer) {
                    rulesContainer.innerHTML = '';

                    question.answer.rules.forEach((rule, ruleIdx) => {
                        addFEVALRule();
                        const ruleEl = rulesContainer.children[rulesContainer.children.length - 1];

                        if (ruleEl) {
                            const exprInput = ruleEl.querySelector('input.feval-rule-expr');
                            const feedbackInput = ruleEl.querySelector('input.feval-rule-feedback');
                            if (exprInput) exprInput.value = rule.expression || '';
                            if (feedbackInput) feedbackInput.value = rule.feedback || '';
                        }
                    });
                }
            }
        } else if (questionType === 'algebra') {
            const ans = question.answer || {};
            document.getElementById('algebra-accepted').value = (ans.accepted || []).join(' | ');
            document.getElementById('algebra-canonical').value = ans.canonical || '';
            document.getElementById('algebra-variables').value = (ans.variables || []).join(', ');
            document.getElementById('algebra-use-sympy').checked = ans.use_sympy !== false;

            const lb = question.input_label?.latex || '';
            const la = question.label_after?.latex  || '';
            document.getElementById('algebra-label').value = la ? `${lb} | ${la}` : lb;
        }

        showMessage('✓ Question loaded for editing', 'success');
    } catch (error) {
        showMessage('✗ Error loading question: ' + error.message, 'error');
        console.error(error);
    }
}

// ===== Format Helper =====
async function loadFormatSnippets() {
    try {
        const res = await fetch('/quiz/api/format-snippets');
        const data = await res.json();
        if (!data.ok) return;
        const select = document.getElementById('formatHelper');
        data.snippets.forEach(s => {
            const opt = document.createElement('option');
            opt.value = s.snippet;
            opt.textContent = s.item;
            select.appendChild(opt);
        });
    } catch (e) {
        console.error('Failed to load format snippets', e);
    }
}

// ===== initBuilderForm =====
// Call this from DOMContentLoaded after the page DOM is ready.
// Attaches all event listeners for the builder form.
function initBuilderForm() {
    // Save / Discard / Discard Image buttons
    document.getElementById('saveBtn').addEventListener('click', save);
    document.getElementById('discardBtn').addEventListener('click', discard);
    document.getElementById('discardImageBtn').addEventListener('click', discardImage);

    // Image upload box
    const imageUploadBox = document.querySelector('.image-upload-box');
    const imageInput = document.getElementById('image');

    ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
        imageUploadBox.addEventListener(eventName, (e) => {
            e.preventDefault();
            e.stopPropagation();
        }, false);
    });

    ['dragenter', 'dragover'].forEach(eventName => {
        imageUploadBox.addEventListener(eventName, () => {
            imageUploadBox.style.borderColor = '#0077cc';
            imageUploadBox.style.background = '#f0f7ff';
        });
    });

    ['dragleave', 'drop'].forEach(eventName => {
        imageUploadBox.addEventListener(eventName, () => {
            imageUploadBox.style.borderColor = '#ddd';
            imageUploadBox.style.background = '#fafafa';
        });
    });

    imageUploadBox.addEventListener('drop', (e) => {
        const dt = e.dataTransfer;
        const files = dt.files;
        imageInput.files = files;
        handleImagePreview();
    });

    imageInput.addEventListener('change', handleImagePreview);

    // Handle Ctrl+V clipboard paste
    document.addEventListener('paste', (e) => {
        const items = e.clipboardData.items;
        for (let item of items) {
            if (item.type.startsWith('image/')) {
                e.preventDefault();
                const file = item.getAsFile();
                const dataTransfer = new DataTransfer();
                dataTransfer.items.add(file);
                imageInput.files = dataTransfer.files;
                handleImagePreview();
                showMessage('✓ Image pasted from clipboard', 'success');
                break;
            }
        }
    });

    // Question type switching
    document.getElementById('questionType').addEventListener('change', (e) => {
        const type = e.target.value.toLowerCase();
        const mcqSection    = document.getElementById('mcq-section');
        const mrSection     = document.getElementById('mr-section');
        const fillSection   = document.getElementById('fill-section');
        const ohsSection    = document.getElementById('ohs-section');
        const fevalSection  = document.getElementById('feval-section');
        const algebraSection = document.getElementById('algebra-section');
        const addBlankBtn   = document.getElementById('addBlankBtn');

        // Hide all type-specific sections first
        [mrSection, fillSection, ohsSection, fevalSection, algebraSection].forEach(s => {
            if (s) s.style.display = 'none';
        });

        if (type === 'mcq') {
            mcqSection.style.display = 'block';
            lastQuestion.type = 'mcq';
        } else if (type === 'mr') {
            mcqSection.style.display = 'none';
            mrSection.style.display = 'block';
            lastQuestion.type = 'mr';
            updateMRCorrectOptions();
        } else if (type === 'fill') {
            mcqSection.style.display = 'none';
            fillSection.style.display = 'block';
            lastQuestion.type = 'fill';
            if (!editingQuestionId && document.getElementById('fill-blanks-container').children.length === 0) {
                addBlankUI();
            }
        } else if (type === 'ohs') {
            mcqSection.style.display = 'none';
            ohsSection.style.display = 'block';
            lastQuestion.type = 'ohs';
            setTimeout(() => { initializeOHSCanvas(); }, 100);
        } else if (type === 'feval') {
            mcqSection.style.display = 'none';
            fevalSection.style.display = 'block';
            lastQuestion.type = 'feval';
            if (!editingQuestionId) {
                if (document.getElementById('feval-variables-container').children.length === 0) {
                    addFEVALVariable();
                }
                if (document.getElementById('feval-rules-container').children.length === 0) {
                    addFEVALRule();
                }
            }
        } else if (type === 'algebra') {
            mcqSection.style.display = 'none';
            algebraSection.style.display = 'block';
            lastQuestion.type = 'algebra';
        }

        // Clear form when switching types — but NOT when editing an existing question
        if (!editingQuestionId) {
            clearForm();
        }
    });

    // Add Blank button (FILL)
    const addBlankBtn = document.getElementById('addBlankBtn');
    if (addBlankBtn) {
        addBlankBtn.addEventListener('click', (e) => {
            e.preventDefault();
            addBlankUI();
        });
    }

    // MR options change listener
    document.getElementById('mr-options').addEventListener('keyup', updateMRCorrectOptions);

    // OHS clear button
    document.getElementById('ohsClearBtn')?.addEventListener('click', (e) => {
        e.preventDefault();
        ohsHotspot = null;
        updateOHSDisplay();
        initializeOHSCanvas();
        showMessage('Hotspot cleared', 'success');
    });

    // Format helper copy
    document.getElementById('formatHelper').addEventListener('change', function () {
        const snippet = this.value;
        if (!snippet) return;
        this.value = '';
        const clean = snippet.replace('§', '');
        navigator.clipboard.writeText(clean).then(() => {
            const label = document.getElementById('formatHelperLabel');
            label.textContent = 'Copied!';
            setTimeout(() => { label.textContent = 'Copy:'; }, 1500);
        });
    });

    // Load format snippets
    loadFormatSnippets();
}
