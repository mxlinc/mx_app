/**
 * Question Renderer - Unified rendering for question components
 * 
 * Handles common rendering tasks (stem, image, feedback) across all contexts:
 * - Individual question preview (quiz-display.html)
 * - Quiz preview mode (quiz-preview.html)
 * - Quiz execution mode (quiz-execution.html)
 * 
 * This ensures consistent rendering regardless of context.
 */

class QuestionRenderer {
    /**
     * Render question stem (common to all question types)
     * @param {Object} question - Question object with stem property
     * @param {string} containerId - ID of container element
     */
    static renderStem(question, containerId = 'stemContainer') {
        const container = document.getElementById(containerId);
        if (!container) {
            console.warn(`Stem container "${containerId}" not found`);
            return;
        }

        // Use pre-processed HTML from backend (LaTeX formatting already converted)
        // Backend latex_to_html() handles all LaTeX text formatting and preserves math mode
        const stemHtml = question.stem?.html || question.stem?.latex || '';
        container.innerHTML = stemHtml;
        console.log('Stem rendered:', stemHtml.substring(0, 50) + '...');
    }

    /**
     * Render question image (common to image-supporting types)
     * @param {Object} question - Question object with image property
     * @param {string} containerSelector - CSS selector for image container div
     * @param {string} imgSelector - CSS selector for img element
     * @param {boolean} skipForType - If true, skip rendering for this question type (e.g., 'ohs')
     * @returns {boolean} - True if image was rendered, false otherwise
     */
    static renderImage(question, containerSelector = '#imageContainer', imgSelector = '#questionImage', skipForType = null) {
        const container = document.querySelector(containerSelector);
        const imgElement = document.querySelector(imgSelector);

        if (!container || !imgElement) {
            console.warn(`Image elements not found: container="${containerSelector}", img="${imgSelector}"`);
            return false;
        }

        // Check if should skip rendering for specific type (e.g., OHS renders on canvas)
        if (skipForType && question.type?.toLowerCase() === skipForType.toLowerCase()) {
            container.style.display = 'none';
            return false;
        }

        // Check if question has image
        if (!question.image?.src) {
            container.style.display = 'none';
            return false;
        }

        // Render image
        container.style.display = 'block';
        let imageSrc = question.image.src;
        if (imageSrc.startsWith('./')) {
            imageSrc = imageSrc.substring(1);
        }
        imgElement.src = imageSrc;
        imgElement.alt = question.image.alt || 'Question image';
        
        // Handle image load error
        imgElement.onerror = () => {
            console.error('Failed to load image:', imageSrc);
            container.style.display = 'none';
        };

        console.log('Image rendered:', imageSrc);
        return true;
    }

    /**
     * Display feedback message
     * @param {string} html - Feedback HTML content
     * @param {boolean} isCorrect - Whether answer was correct
     * @param {string} containerId - ID of feedback container
     */
    static renderFeedback(html, isCorrect, containerId = 'feedbackContainer') {
        const container = document.getElementById(containerId);
        if (!container) {
            console.warn(`Feedback container "${containerId}" not found`);
            return;
        }

        container.innerHTML = html;
        container.style.display = 'block';
        container.className = isCorrect ? 'feedback correct' : 'feedback incorrect';

        // Trigger MathJax to render feedback content
        this.renderMathJax(50);
    }

    /**
     * Clear feedback display
     * @param {string} containerId - ID of feedback container
     */
    static clearFeedback(containerId = 'feedbackContainer') {
        const container = document.getElementById(containerId);
        if (!container) {
            console.warn(`Feedback container "${containerId}" not found`);
            return;
        }

        container.innerHTML = '';
        container.style.display = 'none';
    }

    /**
     * Trigger MathJax rendering for LaTeX content
     * @param {number} delay - Delay in ms before rendering (default 100ms)
     */
    static renderMathJax(delay = 100) {
        setTimeout(() => {
            if (window.MathJax && window.MathJax.typesetPromise) {
                MathJax.typesetPromise()
                    .catch(err => console.log('MathJax error:', err));
            } else {
                console.warn('MathJax not available');
            }
        }, delay);
    }

    /**
     * Get a common object for passing to handlers
     * This object provides the handler with rendering capabilities
     * @param {Object} question - Question object
     * @param {Object} options - Additional options
     * @returns {Object} - Common object for handler
     */
    static getHandlerCommon(question, options = {}) {
        return {
            question: question,
            clearFeedback: (containerId = 'feedbackContainer') => {
                this.clearFeedback(containerId);
            },
            showFeedback: (html, isCorrect, containerId = 'feedbackContainer') => {
                this.renderFeedback(html, isCorrect, containerId);
            },
            renderMathJax: (delay = 100) => {
                this.renderMathJax(delay);
            },
            ...options
        };
    }
}
