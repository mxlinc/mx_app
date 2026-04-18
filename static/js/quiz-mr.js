/**
 * MR (Multiple Response) Handler
 * Specific rendering and answer checking for MR type questions
 */

class QuizMR {
    constructor(common) {
        this.common = common || {};
        this.selectedOptions = new Set();
    }

    /**
     * Render MR-specific content with checkboxes
     * Assumes common.question is already populated
     */
    render() {
        console.log('MR.render() called');
        this.renderOptions();
        this.attachEventListeners();
    }

    /**
     * Shuffle an array (Fisher-Yates algorithm)
     */
    shuffleArray(array) {
        const arr = [...array];  // Create copy to avoid mutating original
        for (let i = arr.length - 1; i > 0; i--) {
            const j = Math.floor(Math.random() * (i + 1));
            [arr[i], arr[j]] = [arr[j], arr[i]];
        }
        return arr;
    }

    /**
     * Render MR options with checkboxes
     */
    renderOptions() {
        console.log('question.input:', this.common.question.input);
        if (this.common.question.input?.options) {
            console.log('Options found:', this.common.question.input.options.length);
            // Shuffle options if enabled
            let options = this.common.question.input.options;
            if (this.common.question.input?.shuffle) {
                console.log('Shuffling options');
                options = this.shuffleArray(options);
            }
            
            // Get number of correct options to select
            const correctOptionIds = this.common.question.answer?.correct_option_ids || [];
            const numCorrect = correctOptionIds.length;
            
            // Build options HTML with instruction prompt
            const promptHtml = `<p style="font-size: 0.85em; color: #666; margin-bottom: 12px; font-style: italic;">Select ${numCorrect} correct option${numCorrect > 1 ? 's' : ''}</p>`;
            
            const optionsHtml = options.map((opt, idx) => {
                const labelText = opt.html || opt.latex || opt.text || JSON.stringify(opt);
                return `
                    <div class="option" data-option-id="${opt.id}">
                        <input type="checkbox" id="opt${opt.id}" name="answer" value="${opt.id}" data-index="${idx}">
                        <label for="opt${opt.id}">${labelText}</label>
                        <span class="option-feedback-indicator"></span>
                    </div>
                `;
            }).join('');
            document.getElementById('optionsContainer').innerHTML = promptHtml + optionsHtml;
            console.log('Options rendered');
        } else {
            console.log('No options found');
            document.getElementById('optionsContainer').innerHTML = '<div style="background: orange; padding: 10px;">No options found</div>';
        }
    }

    /**
     * Attach MR-specific event listeners
     */
    attachEventListeners() {
        document.querySelectorAll('input[name="answer"]').forEach(input => {
            input.addEventListener('change', (e) => {
                if (e.target.checked) {
                    this.selectedOptions.add(e.target.value);
                } else {
                    this.selectedOptions.delete(e.target.value);
                }
                this.common.clearFeedback();
                // Clear per-option feedback indicators
                document.querySelectorAll('.option-feedback-indicator').forEach(indicator => {
                    indicator.textContent = '';
                    indicator.style.display = 'none';
                });
            });
        });
    }

    /**
     * Check MR answer
     */
    checkAnswer() {
        console.log('MR.checkAnswer() called');
        if (this.selectedOptions.size === 0) {
            alert('Please select at least one option');
            return;
        }

        // Get correct option IDs
        const correctOptionIds = this.common.question.answer?.correct_option_ids || [];
        console.log('Correct option IDs:', correctOptionIds);
        console.log('Selected options:', Array.from(this.selectedOptions));

        // Check if selection exactly matches correct options
        const correctSet = new Set(correctOptionIds);
        const isCorrect = this.selectedOptions.size === correctSet.size && 
                          Array.from(this.selectedOptions).every(id => correctSet.has(id));

        // Display per-option feedback
        this.displayPerOptionFeedback(correctOptionIds);

        // Show feedback
        if (isCorrect) {
            this.common.showFeedback('All correct answers selected!', true);
            
            // Disable submit button on correct answer
            const submitBtn = document.querySelector('[onclick*="checkAnswer"]');
            if (submitBtn) submitBtn.disabled = true;
        } else if (this.common.question.stem?.feedback?.html) {
            // Display question-level feedback on wrong answer
            this.common.showFeedback(this.common.question.stem.feedback.html, false);
        }
    }

    /**
     * Display feedback indicators next to each option
     */
    displayPerOptionFeedback(correctOptionIds) {
        const correctSet = new Set(correctOptionIds);
        
        document.querySelectorAll('.option').forEach((optionDiv) => {
            const optionId = optionDiv.getAttribute('data-option-id');
            const indicator = optionDiv.querySelector('.option-feedback-indicator');
            const isCorrect = correctSet.has(optionId);
            const isSelected = this.selectedOptions.has(optionId);
            
            if (!indicator) return;

            if (isCorrect && isSelected) {
                // Correct option - selected correctly
                optionDiv.classList.add('correct-option');
                optionDiv.classList.remove('incorrect-option');
                indicator.innerHTML = '<span style="color: #4CAF50; font-size: 1.2em; margin-left: 12px; font-weight: bold;">✓</span>';
                indicator.style.display = 'inline';
            } else if (!isCorrect && isSelected) {
                // Incorrect option - selected but shouldn't be
                optionDiv.classList.add('incorrect-option');
                optionDiv.classList.remove('correct-option');
                indicator.innerHTML = '<span style="color: #f44336; font-size: 1.2em; margin-left: 12px; font-weight: bold;">✗</span>';
                indicator.style.display = 'inline';
            } else if (isCorrect && !isSelected) {
                // Correct option - should have been selected but wasn't
                optionDiv.classList.add('incorrect-option');
                optionDiv.classList.remove('correct-option');
                indicator.innerHTML = '<span style="font-size: 0.85em; color: #ff9800; margin-left: 12px; font-style: italic; font-weight: 600;">You missed!</span>';
                indicator.style.display = 'inline';
            } else {
                // Not selected, not correct - nothing to show
                optionDiv.classList.remove('correct-option', 'incorrect-option');
                indicator.textContent = '';
                indicator.style.display = 'none';
            }
        });
    }

    /**
     * Validate MR form before saving
     * Returns true if valid, false otherwise
     * Displays error messages via common.showMessage()
     */
    validate(data) {
        console.log('MR.validate() called with data:', data);
        const errors = [];

        // Validate stem
        const stem = data.question.stem?.latex?.trim();
        if (!stem) {
            errors.push('Question stem is required');
        }

        // Parse options - they're already objects from collectData()
        const optionsArray = data.question.input?.options || [];

        // Validate option count
        if (optionsArray.length < 2) {
            errors.push('At least 2 options are required');
        }
        if (optionsArray.length > 6) {
            errors.push('Maximum 6 options allowed');
        }

        // Validate each option is not empty
        optionsArray.forEach((opt, idx) => {
            const latex = opt.latex?.trim();
            if (!latex) {
                errors.push(`Option ${idx + 1} is empty`);
            }
        });

        // Validate correct options
        const correctIds = data.question.answer?.correct_option_ids || [];
        if (correctIds.length < 2) {
            errors.push('At least 2 correct options must be selected');
        }
        if (correctIds.length >= optionsArray.length) {
            errors.push('At least one option must be incorrect');
        }

        // Show errors if any
        if (errors.length > 0) {
            const errorMsg = errors.join('\n');
            if (this.common && this.common.showMessage) {
                this.common.showMessage('✗ ' + errorMsg, 'error');
            } else {
                alert('Validation errors:\n' + errorMsg);
            }
            return false;
        }

        return true;
    }
}

