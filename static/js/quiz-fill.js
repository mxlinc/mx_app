/**
 * FILL (Fill in the Blank) question handler
 */

function getFILLQuestion() {
    "use strict";
    
    const stem_latex = document.getElementById('stem_latex').value.trim();
    
    if (!stem_latex) {
        throw new Error("Question (stem) is required.");
    }

    // Get blanks data
    const blankElements = document.querySelectorAll('.fill-blank');
    if (blankElements.length === 0) {
        throw new Error("At least one blank is required for FILL questions.");
    }

    const blanks = [];
    const correct = [];
    
    blankElements.forEach((blankEl, idx) => {
        const blankId = `blank${idx + 1}`;
        const rawLabel = blankEl.querySelector('.blank-label-latex').value;
        const pipeIdx = rawLabel.indexOf('|');
        const label_latex = (pipeIdx === -1 ? rawLabel : rawLabel.slice(0, pipeIdx)).trim();
        const label_after_latex = pipeIdx === -1 ? '' : rawLabel.slice(pipeIdx + 1).trim();
        const response_type = blankEl.querySelector('.blank-response-type').value;
        const placeholder = blankEl.querySelector('.blank-placeholder').value.trim();
        
        if (!response_type) {
            throw new Error(`Blank ${idx + 1}: response type is required.`);
        }

        const blank = {
            id: blankId,
            response_type: response_type,
            placeholder: placeholder || response_type
        };
        if (label_latex) {
            blank.input_label = { latex: label_latex, html: label_latex };
        }
        if (label_after_latex) {
            blank.label_after = { latex: label_after_latex, html: label_after_latex };
        }
        blanks.push(blank);

        // Get correct answers for this blank
        const correctAnswers = blankEl.querySelector('.blank-correct-answers').value.trim();
        const correctEl = {
            blank_id: blankId,
            response_type: response_type
        };

        if (response_type === 'text') {
            const answers = correctAnswers.split('\n').map(a => a.trim()).filter(a => a);
            if (answers.length === 0) {
                throw new Error(`Blank ${idx + 1}: at least one correct answer is required.`);
            }
            correctEl.accepted_text = answers;
            correctEl.case_sensitive = blankEl.querySelector('.blank-case-sensitive').checked;
        } else if (response_type === 'numeric') {
            const answers = correctAnswers.split(',').map(a => parseFloat(a.trim())).filter(a => !isNaN(a));
            if (answers.length === 0) {
                throw new Error(`Blank ${idx + 1}: at least one numeric answer is required.`);
            }
            correctEl.accepted_numeric = answers;
        } else if (response_type === 'fraction') {
            const fractions = [];
            correctAnswers.split('\n').forEach(line => {
                const match = line.trim().match(/^(\-?\d+)\s*\/\s*(\-?\d+)$/);
                if (match) {
                    fractions.push({
                        numerator: parseInt(match[1]),
                        denominator: parseInt(match[2])
                    });
                }
            });
            if (fractions.length === 0) {
                throw new Error(`Blank ${idx + 1}: at least one fraction answer (format: a/b) is required.`);
            }
            correctEl.accepted_fraction = fractions;
        }

        correct.push(correctEl);
    });

    const question = {
        type: 'fill',
        stem: {
            latex: stem_latex,
            html: stem_latex
        },
        input: {
            blanks: blanks
        },
        answer: {
            correct: correct
        }
    };

    // Add feedback if provided
    const feedbackLatex = document.getElementById('feedback_latex')?.value.trim();
    if (feedbackLatex) {
        question.stem.feedback = { latex: feedbackLatex };
    }

    return question;
}

function addBlankUI() {
    "use strict";
    const container = document.getElementById('fill-blanks-container');
    if (!container) return;
    
    const blankCount = container.querySelectorAll('.fill-blank').length + 1;
    
    const blankEl = document.createElement('div');
    blankEl.className = 'fill-blank';
    blankEl.innerHTML = `
        <div style="background: #f5f5f5; border: 1px solid #ddd; border-radius: 6px; padding: 12px; margin-bottom: 10px;">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px;">
                <span style="font-weight: 600; color: #333;">Blank ${blankCount}</span>
                <button type="button" class="remove-blank-btn" style="background: #f44336; color: white; padding: 4px 10px; border: none; border-radius: 4px; cursor: pointer; font-size: 0.8em;">
                    <i class="fas fa-trash"></i> Remove
                </button>
            </div>
            
            <div class="form-group" style="margin-bottom: 10px;">
                <label>Label <span class="input-type-label">(LaTeX &mdash; use | to add a suffix, e.g. <em>Total length | cm.</em>)</span></label>
                <input type="text" class="blank-label-latex" placeholder="e.g., The value of x is  OR  Total length | cm.">
            </div>
            
            <div class="form-row">
                <div class="form-group">
                    <label>Response Type</label>
                    <select class="blank-response-type" required>
                        <option value="text">Text</option>
                        <option value="numeric">Numeric</option>
                        <option value="fraction">Fraction</option>
                    </select>
                </div>
                <div class="form-group">
                    <label>Placeholder</label>
                    <input type="text" class="blank-placeholder" placeholder="e.g., enter answer">
                </div>
            </div>
            
            <div class="form-group" style="margin-bottom: 8px;">
                <label>Correct Answers <small>(one per line for text, comma-separated for numeric, format a/b for fractions)</small></label>
                <textarea class="blank-correct-answers" placeholder="Enter correct answer(s)" required style="height: 60px;"></textarea>
            </div>
            
            <div style="display: none;" class="text-options-only">
                <label style="display: flex; align-items: center; gap: 6px;">
                    <input type="checkbox" class="blank-case-sensitive">
                    Case sensitive
                </label>
            </div>
        </div>
    `;
    
    container.appendChild(blankEl);
    
    // Add remove listener
    blankEl.querySelector('.remove-blank-btn').addEventListener('click', (e) => {
        e.preventDefault();
        blankEl.remove();
        updateBlankLabels();
    });
    
    // Show/hide case sensitive option based on response type
    blankEl.querySelector('.blank-response-type').addEventListener('change', (e) => {
        const textOptions = blankEl.querySelector('.text-options-only');
        if (e.target.value === 'text') {
            textOptions.style.display = 'block';
        } else {
            textOptions.style.display = 'none';
        }
    });
}

function updateBlankLabels() {
    "use strict";
    const blanks = document.querySelectorAll('.fill-blank');
    blanks.forEach((blank, idx) => {
        blank.querySelector('span').textContent = `Blank ${idx + 1}`;
    });
}

/**
 * FILL (Fill in the Blank) Question Display Handler
 * Renders fill-in-the-blank blanks and checks answers
 */
class QuizFILL {
    constructor(common) {
        this.common = common || {};
        this.userAnswers = {};  // Store user answers by blank_id
    }

    /**
     * Calculate Greatest Common Divisor using Euclidean algorithm
     */
    gcd(a, b) {
        return b === 0 ? Math.abs(a) : this.gcd(b, a % b);
    }

    /**
     * Simplify a fraction to its lowest terms
     */
    simplifyFraction(numerator, denominator) {
        const divisor = this.gcd(numerator, denominator);
        return {
            numerator: numerator / divisor,
            denominator: denominator / divisor
        };
    }

    /**
     * Check if two fractions are equivalent
     */
    areFractionsEquivalent(frac1, frac2) {
        const simplified1 = this.simplifyFraction(frac1.numerator, frac1.denominator);
        const simplified2 = this.simplifyFraction(frac2.numerator, frac2.denominator);
        return simplified1.numerator === simplified2.numerator && 
               simplified1.denominator === simplified2.denominator;
    }

    /**
     * Render FILL-specific content
     */
    render() {
        console.log('QuizFILL.render() called');
        this.renderBlanks();
        this.attachEventListeners();
    }

    /**
     * Render blanks with input fields
     */
    renderBlanks() {
        console.log('question.input:', this.common.question.input);
        if (this.common.question.input?.blanks) {
            console.log('Blanks found:', this.common.question.input.blanks.length);
            
            const blanksHtml = this.common.question.input.blanks.map((blank) => {
                const labelText    = blank.input_label?.html || blank.input_label?.latex || '';
                const labelAfter   = blank.label_after?.html || blank.label_after?.latex || '';
                const inputId      = `blank_${blank.id}`;
                const placeholder  = blank.placeholder || 'Enter answer';
                const isInline     = !!labelAfter;

                let inputField = '';
                if (blank.response_type === 'fraction') {
                    inputField = `
                        <div style="display: inline-flex; flex-direction: column; align-items: center; gap: 8px; border: none; border-radius: 4px; padding: 0; overflow: visible;">
                            <input type="number" id="${inputId}_num" class="blank-input" placeholder="numerator" style="width: 80px; border: 2px solid #999; padding: 10px; text-align: center; font-size: 0.95em; background: white; border-radius: 4px;" title="Enter numerator">
                            <div style="width: 100px; height: 3px; background: black;"></div>
                            <input type="number" id="${inputId}_den" class="blank-input" placeholder="denominator" style="width: 80px; border: 2px solid #999; padding: 10px; text-align: center; font-size: 0.95em; background: white; border-radius: 4px;" title="Enter denominator">
                        </div>
                    `;
                } else if (blank.response_type === 'numeric') {
                    inputField = `<input type="number" id="${inputId}" class="blank-input" placeholder="${placeholder}" step="any" style="width: ${isInline ? '120px' : '100%; max-width: 250px'};">` ;
                } else {
                    inputField = `<input type="text" id="${inputId}" class="blank-input" placeholder="${placeholder}" style="width: ${isInline ? '160px' : '100%; max-width: 350px'};">` ;
                }

                if (isInline) {
                    return `
                        <div style="margin-bottom: 14px; display: flex; flex-wrap: wrap; align-items: baseline; gap: 6px;">
                            <span style="font-size: clamp(1em, 3vw, 1.3em); font-weight: 500; color: #1b3a6f; line-height: 1.5;">${labelText}</span>
                            ${inputField}
                            <span style="font-size: clamp(1em, 3vw, 1.3em); font-weight: 500; color: #1b3a6f; line-height: 1.5;">${labelAfter}</span>
                        </div>
                    `;
                }
                return `
                    <div style="margin-bottom: 14px;">
                        <label style="font-size: clamp(1em, 3vw, 1.3em); font-weight: 500; color: #1b3a6f; margin-bottom: 8px; display: block; line-height: 1.5; word-wrap: break-word; overflow-wrap: break-word; word-break: break-word;">${labelText}</label>
                        ${inputField}
                    </div>
                `;
            }).join('<div style="height: 1.2em;"></div>');
            
            document.getElementById('optionsContainer').innerHTML = blanksHtml;
            console.log('Blanks rendered');
        } else {
            console.log('No blanks found');
            document.getElementById('optionsContainer').innerHTML = '<div style="background: orange; padding: 10px;">No blanks found</div>';
        }
    }

    /**
     * Attach event listeners to blank inputs
     */
    attachEventListeners() {
        document.querySelectorAll('.blank-input').forEach(input => {
            input.addEventListener('change', () => {
                this.common.clearFeedback();
                // Clear per-blank feedback indicators
                document.querySelectorAll('.blank-feedback-indicator').forEach(indicator => {
                    indicator.remove();
                });
            });
        });
    }

    /**
     * Check FILL answers
     */
    checkAnswer() {
        console.log('QuizFILL.checkAnswer() called');
        
        // Collect user answers
        this.userAnswers = {};
        const blanks = this.common.question.input?.blanks || [];
        let hasEmptyField = false;
        let emptyFieldLabel = '';
        
        blanks.forEach((blank) => {
            const inputId = `blank_${blank.id}`;
            
            if (blank.response_type === 'fraction') {
                const num = document.getElementById(`${inputId}_num`)?.value.trim();
                const den = document.getElementById(`${inputId}_den`)?.value.trim();
                if (!num || !den) {
                    hasEmptyField = true;
                    emptyFieldLabel = blank.input_label?.latex || blank.id;
                    return;
                }
                // Store fraction as "numerator/denominator" string
                this.userAnswers[blank.id] = `${num}/${den}`;
            } else if (blank.response_type === 'numeric') {
                const value = document.getElementById(inputId)?.value.trim();
                if (!value) {
                    hasEmptyField = true;
                    emptyFieldLabel = blank.input_label?.latex || blank.id;
                    return;
                }
                this.userAnswers[blank.id] = parseFloat(value);
            } else {
                // text
                const value = document.getElementById(inputId)?.value.trim();
                if (!value) {
                    hasEmptyField = true;
                    emptyFieldLabel = blank.input_label?.latex || blank.id;
                    return;
                }
                this.userAnswers[blank.id] = value;
            }
        });
        
        if (hasEmptyField) {
            this.common.showFeedback(`Please fill in all answers`, false);
            return false;
        }

        // Check answers
        let allCorrect = true;
        const blankFeedback = {}; // Store feedback per blank
        const correctAnswers = this.common.question.answer?.correct || [];

        correctAnswers.forEach((correct) => {
            const blankId = correct.blank_id;
            const userAnswer = this.userAnswers[blankId];

            if (!userAnswer && userAnswer !== 0) {
                allCorrect = false;
                blankFeedback[blankId] = { isCorrect: false, correctDisplay: 'No answer provided' };
                return;
            }

            let isCorrect = false;
            if (correct.response_type === 'text') {
                const acceptedAnswers = correct.accepted_text || [];
                const normalize = s => s.replace(/\s+/g, '').toLowerCase();
                const userVal = normalize(userAnswer);
                isCorrect = acceptedAnswers.some(ans => normalize(ans) === userVal);
            } else if (correct.response_type === 'numeric') {
                const acceptedValues = correct.accepted_numeric || [];
                isCorrect = acceptedValues.includes(userAnswer);
            } else if (correct.response_type === 'fraction') {
                const acceptedFractions = correct.accepted_fraction || [];
                // Parse fraction string "numerator/denominator" back to object for comparison
                const fractionMatch = userAnswer.match(/^(-?\d+)\s*\/\s*(-?\d+)$/);
                if (!fractionMatch) {
                    isCorrect = false;
                } else {
                    const userFrac = {
                        numerator: parseInt(fractionMatch[1]),
                        denominator: parseInt(fractionMatch[2])
                    };
                    isCorrect = acceptedFractions.some(frac => 
                        this.areFractionsEquivalent(userFrac, frac)
                    );
                }
            }

            if (isCorrect) {
                blankFeedback[blankId] = { isCorrect: true, correctDisplay: '' };
            } else {
                allCorrect = false;
                let correctDisplay = '';
                
                if (correct.response_type === 'text') {
                    const acceptedAnswers = correct.accepted_text || [];
                    correctDisplay = acceptedAnswers.join(' or ');
                } else if (correct.response_type === 'numeric') {
                    const acceptedValues = correct.accepted_numeric || [];
                    correctDisplay = acceptedValues.join(' or ');
                } else if (correct.response_type === 'fraction') {
                    const acceptedFractions = correct.accepted_fraction || [];
                    correctDisplay = acceptedFractions.map(f => `${f.numerator}/${f.denominator}`).join(' or ');
                }
                
                blankFeedback[blankId] = { isCorrect: false, correctDisplay };
            }
        });

        // Display per-blank feedback
        this.displayPerBlankFeedback(blanks, blankFeedback);

        // Store allCorrect for isAnswerCorrect() method
        this.isCorrect = allCorrect;

        // Display question-level feedback on wrong answer if available
        if (!allCorrect && this.common.question.stem?.feedback?.html) {
            this.common.showFeedback(this.common.question.stem.feedback.html, false);
        }

        return true; // Answer was submitted successfully
    }

    /**
     * Get whether the answer is correct
     */
    isAnswerCorrect() {
        return this.isCorrect || false;
    }

    /**
     * Expose answers for getHandlerAnswer() in quiz-controller
     */
    get answers() {
        return this.userAnswers;
    }

    /**
     * Display feedback indicators next to each blank
     */
    displayPerBlankFeedback(blanks, blankFeedback) {
        blanks.forEach((blank) => {
            const feedback = blankFeedback[blank.id];
            if (!feedback) return;

            const inputId = `blank_${blank.id}`;
            const container = document.getElementById(inputId)?.closest('div[style*="margin-bottom"]') || 
                             document.getElementById(`${inputId}_num`)?.closest('div[style*="display: inline-flex"]')?.closest('div');
            
            if (!container) return;

            // Remove existing feedback indicator if present
            const existingFeedback = container.querySelector('.blank-feedback-indicator');
            if (existingFeedback) existingFeedback.remove();

            // Create feedback indicator
            const indicator = document.createElement('span');
            indicator.className = 'blank-feedback-indicator';
            
            // Get all input elements for this blank (handles both single inputs and fraction numerator/denominator)
            const inputElement = document.getElementById(inputId);
            const fracNumElement = document.getElementById(`${inputId}_num`);
            const fracDenElement = document.getElementById(`${inputId}_den`);
            
            if (feedback.isCorrect) {
                // Apply correct styling to input(s)
                if (inputElement) {
                    inputElement.classList.add('correct-answer');
                    inputElement.classList.remove('incorrect-answer');
                }
                if (fracNumElement) {
                    fracNumElement.classList.add('correct-answer');
                    fracNumElement.classList.remove('incorrect-answer');
                }
                if (fracDenElement) {
                    fracDenElement.classList.add('correct-answer');
                    fracDenElement.classList.remove('incorrect-answer');
                }
                indicator.innerHTML = '<span style="color: #4CAF50; font-size: 1.3em; margin-left: 12px; font-weight: bold;">✓</span>';
            } else {
                // Apply incorrect styling to input(s)
                if (inputElement) {
                    inputElement.classList.add('incorrect-answer');
                    inputElement.classList.remove('correct-answer');
                }
                if (fracNumElement) {
                    fracNumElement.classList.add('incorrect-answer');
                    fracNumElement.classList.remove('correct-answer');
                }
                if (fracDenElement) {
                    fracDenElement.classList.add('incorrect-answer');
                    fracDenElement.classList.remove('correct-answer');
                }
                const correctText = feedback.correctDisplay ? `${feedback.correctDisplay}` : 'No answer provided';
                indicator.innerHTML = `<span style="color: #f44336; font-size: 1.3em; margin-left: 12px; font-weight: bold;">✗</span> 
                                       <span style="color: #666; font-size: 0.9em; margin-left: 8px;">${correctText}</span>`;
            }
            
            indicator.style.display = 'inline-flex';
            indicator.style.alignItems = 'center';
            indicator.style.marginTop = '4px';
            
            const inputEl = inputElement || fracNumElement?.closest('div');
            if (inputEl) {
                inputEl.parentElement.appendChild(indicator);
            }
        });
    }
}
