/**
 * Quiz Common Utilities
 * Shared functionality across all question types
 */

// Initialize MathJax configuration immediately
window.MathJax = {
    tex: {
        inlineMath: [['$', '$'], ['\\(', '\\)']],
        displayMath: [['$$', '$$'], ['\\[', '\\]']]
    },
    svg: {
        fontCache: 'global'
    }
};

class QuizCommon {
    constructor() {
        this.question = null;
        this.metadata = { topic: '', subtopic: '', level: '' };
        this.submitted = false;
    }

    /**
     * Initialize MathJax (already done above, but kept for API completeness)
     */
    initMathJax() {
        console.log('MathJax already initialized');
    }

    /**
     * Fetch question from backend and unwrap nested structure
     */
    async fetchQuestion(questionId) {
        console.log('Fetching question:', questionId);
        try {
            const resp = await fetch(`/quiz/get-display/${questionId}`);
            console.log('Fetch response status:', resp.status);
            if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
            const data = await resp.json();
            console.log('Raw response:', data);
            
            // Backend wraps question in "question" key
            this.question = data.question || data;
            console.log('Extracted question object:', this.question);
            
            // Save metadata
            this.metadata.topic = this.question.topic || '';
            this.metadata.subtopic = this.question.subtopic || '';
            this.metadata.level = this.question.level || '';
            
            return this.question;
        } catch (e) {
            console.error('Failed to load question:', e);
            throw e;
        }
    }

    /**
     * Render question stem (common to all types)
     */
    renderStem() {
        console.log('question.stem:', this.question.stem);
        const stemHtml = this.question.stem?.html || this.question.stem?.latex || this.question.stem || 'No stem found';
        console.log('Stem HTML:', stemHtml);
        document.getElementById('stemContainer').innerHTML = stemHtml;
    }

    /**
     * Render question image (common to types that use images)
     */
    renderImage() {
        const imageContainer = document.getElementById('imageContainer');
        if (!imageContainer) return false; // No image container in this layout

        if (this.question.image?.src) {
            console.log('Image found:', this.question.image.src);
            imageContainer.style.display = 'block';
            let imageSrc = this.question.image.src;
            if (imageSrc.startsWith('./')) imageSrc = imageSrc.substring(1);
            document.getElementById('questionImage').src = imageSrc;
            document.getElementById('questionImage').onerror = () => {
                console.error('Failed to load image:', imageSrc);
                imageContainer.style.display = 'none';
            };
            return true;
        } else {
            console.log('No image in question.image');
            imageContainer.style.display = 'none';
            return false;
        }
    }

    /**
     * Add no-image class for CSS adjustments when no image present
     */
    setNoImageClass() {
        const qaGrid = document.querySelector('.qa-grid');
        if (qaGrid) {
            qaGrid.classList.add('no-image');
        }
    }

    /**
     * Show feedback message
     */
    showFeedback(message, isCorrect) {
        const feedbackDiv = document.getElementById('feedbackContainer');
        feedbackDiv.innerHTML = message;
        feedbackDiv.className = isCorrect ? 'feedback show correct' : 'feedback show incorrect';
        this.submitted = true;
        document.getElementById('submitBtn').disabled = true;

        // Trigger MathJax to render feedback content
        setTimeout(() => {
            if (window.MathJax && window.MathJax.typesetPromise) {
                window.MathJax.typesetPromise().catch(err => console.log('MathJax error:', err));
            }
        }, 50);
    }

    /**
     * Clear feedback and reset submit button
     */
    clearFeedback() {
        document.getElementById('feedbackContainer').classList.remove('show');
        this.submitted = false;
        document.getElementById('submitBtn').disabled = false;
    }

    /**
     * Trigger MathJax rendering
     */
    renderMathJax(delay = 100) {
        setTimeout(() => {
            console.log('Rendering MathJax');
            if (window.MathJax && window.MathJax.typesetPromise) {
                window.MathJax.typesetPromise().catch(err => console.log('MathJax error:', err));
            }
        }, delay);
    }

    /**
     * Display question JSON in modal
     */
    showJson() {
        const orderedQuestion = this.reorderQuestion(this.question);
        const jsonStr = JSON.stringify(orderedQuestion, null, 2);
        const highlighted = this.syntaxHighlightJson(jsonStr);
        document.getElementById('jsonContent').innerHTML = highlighted;
        document.getElementById('jsonModal').classList.add('show');
    }

    /**
     * Reorder question fields to match schema
     */
    reorderQuestion(question) {
        const fieldOrder = ["id", "type", "stem", "image", "input", "answer", "topic", "subtopic", "level"];
        const ordered = {};
        
        for (let field of fieldOrder) {
            if (field in question) {
                ordered[field] = question[field];
            }
        }
        
        return ordered;
    }

    /**
     * Syntax highlight JSON for display
     */
    syntaxHighlightJson(json) {
        json = json.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
        return json.replace(/("(\\u[a-zA-Z0-9]{4}|\\[^u]|[^\\"])*"(\s*:)?|\b(true|false|null)\b|-?\d+(?:\.\d*)?(?:[eE][+\-]?\d+)?)/g, (match) => {
            var cls = 'json-number';
            if (/^"/.test(match)) {
                if (/:$/.test(match)) {
                    cls = 'json-key';
                } else {
                    cls = 'json-string';
                }
            } else if (/true|false/.test(match)) {
                cls = 'json-boolean';
            } else if (/null/.test(match)) {
                cls = 'json-null';
            }
            return `<span class="${cls}">${match}</span>`;
        });
    }

    /**
     * Setup navigation event listeners
     */
    setupNavigation() {
        document.getElementById('editLink')?.addEventListener('click', (e) => {
            e.preventDefault();
            window.location.href = `/quiz/builder?id=${document.getElementById('questionId').textContent.trim()}`;
        });

        document.getElementById('jsonLink')?.addEventListener('click', (e) => {
            e.preventDefault();
            this.showJson();
        });

        document.getElementById('newLink')?.addEventListener('click', (e) => {
            e.preventDefault();
            const params = new URLSearchParams({
                topic: this.metadata.topic,
                subtopic: this.metadata.subtopic,
                level: this.metadata.level
            });
            window.location.href = `/quiz/builder?${params}`;
        });

        document.getElementById('closeJsonBtn')?.addEventListener('click', () => {
            document.getElementById('jsonModal').classList.remove('show');
        });

        window.addEventListener('click', (e) => {
            const jsonModal = document.getElementById('jsonModal');
            if (e.target === jsonModal) {
                jsonModal.classList.remove('show');
            }
        });
    }

    /**
     * Get question ID from DOM
     */
    getQuestionId() {
        return document.getElementById('questionId').textContent.trim();
    }
}

// Create singleton instance
const quizCommon = new QuizCommon();
