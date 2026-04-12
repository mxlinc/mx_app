/**
 * MCQ (Multiple Choice Question) Handler
 * Specific rendering and answer checking for MCQ type questions
 */

class QuizMCQ {
    constructor(common) {
        this.common = common;
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
     * Render MCQ options with radio buttons
     */
    renderOptions() {
        console.log('question.input:', this.common.question.input);
        if (this.common.question.input?.options) {
            console.log('Options found:', this.common.question.input.options.length);
            const optionsHtml = this.common.question.input.options.map((opt, idx) => {
                const labelText = opt.html || opt.latex || opt.text || JSON.stringify(opt);
                return `
                    <div class="option">
                        <input type="radio" id="opt${opt.id}" name="answer" value="${opt.id}" data-index="${idx}">
                        <label for="opt${opt.id}">${labelText}</label>
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

        // Show feedback
        if (this.selectedOption === correctOptionId) {
            this.common.showFeedback('✓ Correct!', true);
        } else {
            const correctAnswerHtml = correctOptionDisplay ? 
                `Not quite right. The correct answer is: ${correctOptionDisplay}` :
                'Not quite right. Try again or move on.';
            this.common.showFeedback(correctAnswerHtml, false);
        }
    }
}

// Create singleton instance (will be initialized in quiz_display.html)
let quizMCQ;
