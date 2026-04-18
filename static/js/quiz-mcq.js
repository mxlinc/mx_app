/**
 * MCQ (Multiple Choice Question) Handler
 * Specific rendering and answer checking for MCQ type questions
 */

class QuizMCQ {
    constructor(common) {
        this.common = common || {};
        this.selectedOption = null;
    }

    /**
     * Render MCQ-specific content
     * Assumes common.question is already populated
     */
    render() {
        console.log('MCQ.render() called');
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
     * Render MCQ options with radio buttons
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
            const optionsHtml = options.map((opt, idx) => {
                const labelText = opt.html || opt.latex || opt.text || JSON.stringify(opt);
                return `
                    <div class="option" data-option-id="${opt.id}">
                        <input type="radio" id="opt${opt.id}" name="answer" value="${opt.id}" data-index="${idx}">
                        <label for="opt${opt.id}">${labelText}</label>
                        <span class="option-feedback-indicator"></span>
                    </div>
                `;
            }).join('');
            document.getElementById('optionsContainer').innerHTML = optionsHtml;
            console.log('Options rendered');
        } else {
            console.log('No options found');
            document.getElementById('optionsContainer').innerHTML = '<div style="background: orange; padding: 10px;">No options found</div>';
        }
    }

    /**
     * Attach MCQ-specific event listeners
     */
    attachEventListeners() {
        document.querySelectorAll('input[name="answer"]').forEach(input => {
            input.addEventListener('change', (e) => {
                this.selectedOption = e.target.value;
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
     * Check MCQ answer
     */
    checkAnswer() {
        console.log('MCQ.checkAnswer() called');
        if (!this.selectedOption) {
            alert('Please select an option');
            return;
        }

        // Determine correct option
        let correctOptionId = null;
        let correctOptionDisplay = null;
        
        if (this.common.question.answer?.correct_option_id) {
            correctOptionId = this.common.question.answer.correct_option_id;
        } else if (this.common.question.answer?.correct_option_text) {
            // Fallback: Find the option with matching text
            const correctOption = this.common.question.input.options.find(opt => 
                opt.latex === this.common.question.answer.correct_option_text || 
                opt.html === this.common.question.answer.correct_option_text
            );
            correctOptionId = correctOption?.id;
        }

        // Get display text for correct option
        if (correctOptionId) {
            const correctOption = this.common.question.input.options.find(opt => opt.id === correctOptionId);
            if (correctOption) {
                correctOptionDisplay = correctOption.html || correctOption.latex;
            }
        }

        // Display per-option feedback
        this.displayPerOptionFeedback(correctOptionId);

        // Check if answer is incorrect and display feedback if available
        const isCorrect = this.selectedOption === correctOptionId;
        if (!isCorrect && this.common.question.stem?.feedback?.html) {
            // Display question-level feedback on wrong answer
            this.common.showFeedback(this.common.question.stem.feedback.html, false);
        }

        // Disable submit button on correct answer
        if (isCorrect) {
            const submitBtn = document.querySelector('[onclick*="checkAnswer"]');
            if (submitBtn) submitBtn.disabled = true;
        }
    }

    /**
     * Display feedback indicators next to each option
     */
    displayPerOptionFeedback(correctOptionId) {
        document.querySelectorAll('.option').forEach((optionDiv) => {
            const optionId = optionDiv.getAttribute('data-option-id');
            const indicator = optionDiv.querySelector('.option-feedback-indicator');
            
            if (!indicator) return;

            if (optionId === correctOptionId) {
                // Correct option - add green styling to the option itself
                optionDiv.classList.add('correct-option');
                optionDiv.classList.remove('incorrect-option');
                indicator.innerHTML = '<span style="color: #4CAF50; font-size: 1.2em; margin-left: 12px; font-weight: bold;">✓</span>';
                indicator.style.display = 'inline';
            } else if (optionId === this.selectedOption) {
                // Selected but incorrect - add red styling to the option itself
                optionDiv.classList.add('incorrect-option');
                optionDiv.classList.remove('correct-option');
                indicator.innerHTML = '<span style="color: #f44336; font-size: 1.2em; margin-left: 12px; font-weight: bold;">✗</span>';
                indicator.style.display = 'inline';
            } else {
                // Not selected - remove any styling classes
                optionDiv.classList.remove('correct-option', 'incorrect-option');
                indicator.textContent = '';
                indicator.style.display = 'none';
            }
        });
    }

    /**
     * Validate MCQ form before saving
     * Returns true if valid, false otherwise
     * Displays error messages via common.showMessage()
     */
    validate(data) {
        console.log('MCQ.validate() called with data:', data);
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

        // Validate correct option if specified (need to check DOM since it's from builder form)
        const correctInput = document.getElementById('correct')?.value?.trim();
        if (correctInput) {
            const optionLatexValues = optionsArray.map(opt => opt.latex);
            const found = optionLatexValues.some(latex => latex === correctInput);
            if (!found) {
                errors.push('Correct option must match one of the listed options exactly');
            }
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

        console.log('MCQ validation passed');
        return true;
    }
}

// Create singleton instance (will be initialized in quiz_display.html)
let quizMCQ;
