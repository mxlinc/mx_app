/**
 * Quiz Common Utilities
 * Admin/utility functions for question preview and navigation
 * 
 * Rendering tasks are now delegated to QuestionRenderer class
 */

// MathJax removed: LaTeX is converted to MathML server-side at save time.

class QuizCommon {
    constructor() {
        this.question = null;
        this.metadata = { topic: '', subtopic: '', level: '' };
        this.submitted = false;
    }

    /**
     * Fetch question from backend and unwrap nested structure
     */
    async fetchQuestion(questionId) {
        console.log('Fetching question:', questionId);
        try {
            const resp = await fetch(`/question/api/display/${questionId}`);
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
            const questionId = document.getElementById('questionId').textContent.trim();
            window.location.href = `/question/edit/${questionId}`;
        });

        document.getElementById('duplicateLink')?.addEventListener('click', (e) => {
            e.preventDefault();
            this.duplicateQuestion();
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
            window.location.href = `/question/builder?${params}`;
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
     * Duplicate the current question
     */
    async duplicateQuestion() {
        const questionId = document.getElementById('questionId').textContent.trim();
        
        try {
            const response = await fetch(`/question/api/duplicate/${questionId}`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                }
            });
            
            const result = await response.json();
            
            if (result.ok && result.question_id) {
                // Navigate to the duplicated question display page
                window.location.href = `/question/display/${result.question_id}`;
            } else {
                alert(result.error || 'Failed to duplicate question');
            }
        } catch (error) {
            console.error('Error duplicating question:', error);
            alert('Failed to duplicate question. Please try again.');
        }
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
