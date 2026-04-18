/**
 * Quiz Controller - Orchestrates quiz flow for preview and execution modes
 * Uses existing type-specific handlers (QuizMCQ, QuizMR, QuizFILL) for rendering
 * 
 * Handles:
 * - Question navigation (next, previous for execution, jump for preview)
 * - Answer submission and validation (delegated to type-specific handlers)
 * - Feedback display (delegated to type-specific handlers)
 * - API calls for execution mode (storing answers)
 * - State management
 */

class QuizController {
    constructor(config) {
        // Configuration
        this.mode = config.mode; // 'preview' or 'execution'
        this.quizId = config.quizId;
        this.quizTitle_text = config.quizTitle || 'Quiz';
        this.quizDescription = config.quizDescription || '';
        this.userId = config.userId; // For execution mode
        this.questions = config.questions; // Array of question objects
        this.onClose = config.onClose; // Callback when quiz closes
        
        // State
        this.currentIndex = 0;
        this.isSubmitted = false;
        this.currentHandler = null; // Current type-specific handler
        
        // DOM References
        this.container = document.getElementById('quizQuestionDisplay');
        this.stemContainer = document.getElementById('stemContainer');
        this.imageContainer = document.getElementById('imageContainer');
        this.questionImage = document.getElementById('questionImage');
        this.optionsContainer = document.getElementById('optionsContainer');
        this.feedbackContainer = document.getElementById('feedbackContainer');
        this.progressText = document.getElementById('progressText');
        this.questionJumpSelect = document.getElementById('questionJumpSelect');
        this.submitBtn = document.getElementById('submitBtn');
        this.nextBtn = document.getElementById('nextBtn');
        this.closeBtn = document.getElementById('closeBtn');
        this.quizTitleEl = document.getElementById('quizTitle');
        this.quizIdEl = document.getElementById('quizId');
        
        this.setupUI();
        this.attachEventListeners();
    }

    setupUI() {
        // Set top band info
        const modeLabel = this.mode === 'preview' ? 'Preview - ' : '';
        const titleWithDesc = this.quizDescription 
            ? `${this.quizTitle_text} - ${this.quizDescription}` 
            : this.quizTitle_text;
        this.quizTitleEl.textContent = `${modeLabel}${titleWithDesc}`;
        this.quizIdEl.textContent = `ID: ${this.quizId}`;

        // Setup question dropdown for preview mode only
        if (this.mode === 'preview') {
            this.questionJumpSelect.style.display = 'block';
            this.setupQuestionDropdown();
        } else {
            this.questionJumpSelect.style.display = 'none';
        }

        // Display first question
        this.displayQuestion();
    }

    setupQuestionDropdown() {
        this.questions.forEach((q, idx) => {
            const option = document.createElement('option');
            option.value = idx;
            option.textContent = `Question ${idx + 1}`;
            this.questionJumpSelect.appendChild(option);
        });

        this.questionJumpSelect.addEventListener('change', (e) => {
            const idx = parseInt(e.target.value);
            if (!isNaN(idx)) {
                this.jumpToQuestion(idx);
                this.questionJumpSelect.value = ''; // Reset dropdown
            }
        });
    }

    attachEventListeners() {
        // Fresh listeners
        this.submitBtn.addEventListener('click', (e) => {
            e.preventDefault();
            this.submitAnswer();
        });
        this.nextBtn.addEventListener('click', (e) => {
            e.preventDefault();
            this.nextQuestion();
        });
        this.closeBtn.addEventListener('click', (e) => {
            e.preventDefault();
            this.closeQuiz();
        });
    }

    displayQuestion() {
        if (this.currentIndex >= this.questions.length) {
            this.showCompletion();
            return;
        }

        const question = this.questions[this.currentIndex];
        this.isSubmitted = false;

        // Reset UI
        this.feedbackContainer.style.display = 'none';
        this.submitBtn.style.display = 'block';
        this.nextBtn.style.display = 'none';
        this.closeBtn.style.display = 'none';
        this.feedbackContainer.innerHTML = '';

        // Update progress
        this.progressText.textContent = `Question ${this.currentIndex + 1} of ${this.questions.length}`;

        // Populate stem
        const stemHtml = question.stem?.html || question.stem?.latex || '';
        this.stemContainer.innerHTML = stemHtml;

        // Populate image if exists
        if (question.image?.src) {
            this.imageContainer.style.display = 'block';
            this.questionImage.src = question.image.src;
            this.questionImage.alt = question.image.alt || 'Question image';
        } else {
            this.imageContainer.style.display = 'none';
        }

        // Use type-specific handler to render question
        this.renderWithTypeHandler(question);

        // Render MathJax
        this.renderMathJax();
    }

    /**
     * Use existing type-specific handlers for consistent rendering
     */
    renderWithTypeHandler(question) {
        const type = question.type?.toLowerCase() || 'mcq';
        
        // Create a common-like object for the handler
        const common = {
            question: question,
            clearFeedback: () => {
                if (this.feedbackContainer) {
                    this.feedbackContainer.innerHTML = '';
                    this.feedbackContainer.style.display = 'none';
                }
            }
        };

        // Instantiate and render with appropriate handler
        switch (type) {
            case 'mcq':
                this.currentHandler = new QuizMCQ(common);
                this.currentHandler.render();
                break;
            case 'mr':
                this.currentHandler = new QuizMR(common);
                this.currentHandler.render();
                break;
            case 'fill':
                this.currentHandler = new QuizFILL(common);
                this.currentHandler.render();
                break;
            default:
                console.warn(`Unknown question type: ${type}`);
        }
    }

    async submitAnswer() {
        console.log('submitAnswer() called');
        const question = this.questions[this.currentIndex];
        const type = question.type?.toLowerCase() || 'mcq';

        try {
            // Use handler's checkAnswer method
            if (!this.currentHandler) {
                console.error('No handler initialized');
                return;
            }

            const result = this.currentHandler.checkAnswer();
            if (result === false) {
                // Handler showed alert or validation failed
                return;
            }

            this.isSubmitted = true;

            // For execution mode, call API to store answer
            if (this.mode === 'execution') {
                const userAnswer = this.getHandlerAnswer();
                const isCorrect = this.currentHandler.isAnswerCorrect ? this.currentHandler.isAnswerCorrect() : false;
                await this.saveAnswerToDatabase(question, userAnswer, isCorrect);
            }

            // Show next/close button
            if (this.currentIndex === this.questions.length - 1) {
                this.closeBtn.style.display = 'block';
            } else {
                this.nextBtn.style.display = 'block';
            }
            this.submitBtn.style.display = 'none';

        } catch (error) {
            console.error('Error submitting answer:', error);
            alert('Error submitting answer: ' + error.message);
        }
    }

    /**
     * Get answer from current handler
     */
    getHandlerAnswer() {
        if (!this.currentHandler) return null;
        
        const type = this.questions[this.currentIndex].type?.toLowerCase() || 'mcq';
        
        switch (type) {
            case 'mcq':
                return this.currentHandler.selectedOption;
            case 'mr':
                return this.currentHandler.selectedOptions || [];
            case 'fill':
                return this.currentHandler.answers || {};
            default:
                return null;
        }
    }

    async saveAnswerToDatabase(question, userAnswer, isCorrect) {
        try {
            const payload = {
                quiz_id: this.quizId,
                user_id: this.userId,
                question_id: question.id,
                question_type: question.type,
                user_answer: userAnswer,
                is_correct: isCorrect,
                feedback: this.feedbackContainer?.textContent || ''
            };

            const response = await fetch('/quiz/submit-answer', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(payload)
            });

            if (!response.ok) {
                console.error('Failed to save answer');
            }
        } catch (error) {
            console.error('Error saving answer to database:', error);
        }
    }

    nextQuestion() {
        this.currentIndex++;
        this.displayQuestion();
    }

    jumpToQuestion(index) {
        if (this.mode === 'preview' && index >= 0 && index < this.questions.length) {
            this.currentIndex = index;
            this.displayQuestion();
        }
    }

    async closeQuiz() {
        if (this.onClose) {
            this.onClose(this.mode);
        }
    }

    showCompletion() {
        this.container.innerHTML = `
            <div style="display: flex; flex-direction: column; align-items: center; justify-content: center; height: 100vh; background: #F7F6F3;">
                <div style="text-align: center; background: white; padding: 40px; border-radius: 12px; box-shadow: 0 8px 24px rgba(0, 0, 0, 0.1);">
                    <h1 style="color: #2F4A5C; margin-bottom: 20px;">Quiz Complete!</h1>
                    <p style="color: #666; font-size: 1.1em; margin-bottom: 30px;">Thank you for completing the quiz.</p>
                    <button onclick="window.location.href='/quiz/admin-return?from=${this.mode}'" 
                            style="background: #667eea; color: white; padding: 12px 30px; border: none; border-radius: 6px; cursor: pointer; font-size: 1em; font-weight: 600;">
                        Back to Admin
                    </button>
                </div>
            </div>
        `;
    }

    renderMathJax(delay = 100) {
        setTimeout(() => {
            if (window.MathJax && window.MathJax.typesetPromise) {
                MathJax.typesetPromise().catch(err => console.log('MathJax error:', err));
            }
        }, delay);
    }
}
