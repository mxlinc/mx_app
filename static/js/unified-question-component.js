/**
 * Unified Question Component
 * SINGLE SOURCE OF TRUTH for rendering all question types
 * Uses QuestionTemplates for HTML generation and TemplateHandlers for interactivity
 */

class UnifiedQuestionComponent {
    constructor(options = {}) {
        this.question = options.question;
        this.container = options.container;
        this.readOnly = options.readOnly || false;
        this.handler = null;
        this.lastIsCorrect = null;
        this.onAnswerChange = options.onAnswerChange || null;
    }

    /**
     * Main render method - generates and displays the question
     */
    render() {
        if (!this.question || !this.container) {
            console.error('UnifiedQuestionComponent: Missing question or container');
            return false;
        }

        try {
            // Generate template HTML
            const templateHtml = QuestionTemplates.getTemplate(this.question);
            
            // Clear container and insert template
            this.container.innerHTML = templateHtml;
            
            // Get the rendered template
            const templateElement = this.container.querySelector('.template-question');
            
            if (!templateElement) {
                console.error('Template did not render properly');
                return false;
            }

            // Create handler for this question type
            this.handler = getTemplateHandler(
                this.question.type,
                templateElement,
                this.question,
                this.readOnly
            );

            // Attach event listeners
            this.handler.attachListeners();

            // Note: MathJax typesetting is handled by the caller after render() returns.

            console.log(`Question rendered: ${this.question.type}`);
            return true;
        } catch (error) {
            console.error('Error rendering question:', error);
            this.container.innerHTML = `<div class="template-error">Error rendering question: ${error.message}</div>`;
            return false;
        }
    }

    /**
     * Get current answer
     */
    getAnswer() {
        if (!this.handler) return null;
        return this.handler.getAnswer();
    }

    /**
     * Check if answer is correct
     */
    isAnswerCorrect() {
        const answer = this.getAnswer();
        if (!this.handler) return false;
        return this.handler.isCorrect(answer);
    }

    /**
     * Submit answer and show feedback
     */
    async submitAnswer() {
        const answer = this.getAnswer();

        // Algebra type uses an async two-step check (string match → sympy).
        // All other types use the synchronous isCorrect() path.
        // Guard answer for checkAsync — null answer falls back to isAnswerCorrect() which returns false.
        const isCorrect = (this.handler.checkAsync && answer)
            ? await this.handler.checkAsync(answer)
            : this.isAnswerCorrect();

        this.lastIsCorrect = isCorrect;
        const feedbackHtml = !isCorrect
            ? (this.question.stem?.feedback?.html || this.question.answer?.feedback?.html || null)
            : null;
        const message = isCorrect 
            ? '\u2713 Correct!' 
            : feedbackHtml;  // null if no custom feedback

        this.handler.showFeedback(isCorrect, message);
        this.handler.disable();

        return isCorrect;
    }

    /**
     * Reset the question
     */
    reset() {
        if (this.container) {
            this.container.innerHTML = '';
        }
        this.handler = null;
        this.render();
    }

    /**
     * Enable/disable inputs
     */
    disable() {
        if (this.handler) {
            this.handler.disable();
        }
    }

    enable() {
        if (this.handler) {
            this.handler.enable();
        }
    }
}
