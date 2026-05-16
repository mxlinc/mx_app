/**
 * OHS (One HotSpot) Question Handler
 * Specific rendering and answer checking for OHS type questions
 */

class QuizOHS {
    constructor(common) {
        this.common = common || {};
        this.selectedHotspot = null;
        this.canvas = null;
        this.ctx = null;
        this.image = null;
        this.isAnswered = false;
    }

    /**
     * Render OHS-specific content
     * Assumes common.question is already populated
     */
    render() {
        console.log('OHS.render() called');
        this.renderHotspotCanvas();
        this.attachEventListeners();
    }

    /**
     * Render hotspot canvas with image (full width)
     */
    renderHotspotCanvas() {
        console.log('Rendering OHS canvas');
        
        const optionsContainer = document.getElementById('optionsContainer');
        if (!optionsContainer) return;
        
        // Ensure full width layout for OHS
        const optionsSection = optionsContainer.closest('.options-section');
        const optionsBand = optionsContainer.closest('.options-band');
        const qaRight = optionsContainer.closest('.qa-right');
        const qaLeft = optionsContainer.closest('.qa-grid')?.querySelector('.qa-left');
        const qaGrid = optionsContainer.closest('.qa-grid');
        
        if (optionsSection) {
            optionsSection.style.display = 'flex';
            optionsSection.style.flexDirection = 'column';
            optionsSection.style.gridTemplateColumns = 'unset'; // Override any 2-column grid
        }
        if (optionsBand) {
            optionsBand.style.flex = '1';
            optionsBand.style.minHeight = '0';
        }
        if (qaRight) {
            qaRight.style.flex = '1';
            qaRight.style.minHeight = '0';
        }
        if (qaGrid) {
            qaGrid.style.display = 'flex';
            qaGrid.style.flexDirection = 'column';
        }
        if (qaLeft) {
            qaLeft.style.flex = '0 0 auto';
        }
        
        // Ensure optionsContainer itself takes full width and height
        optionsContainer.style.width = '100%';
        optionsContainer.style.height = '100%';
        optionsContainer.style.flex = '1';
        optionsContainer.style.minHeight = '0';
        optionsContainer.style.display = 'flex';
        optionsContainer.style.flexDirection = 'column';
        
        // Create canvas element with full width layout
        const canvasHtml = `
            <style>
                .ohs-container {
                    display: flex;
                    flex-direction: column;
                    width: 100%;
                    height: 100%;
                    gap: 15px;
                    flex: 1;
                }
                .ohs-canvas-wrapper {
                    position: relative;
                    width: 100%;
                    height: 100%;
                    flex: 1;
                    background: #f9f9f9;
                    border: 2px solid #ddd;
                    border-radius: 8px;
                    overflow: hidden;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    min-height: 400px;
                }
                #ohsQuizCanvas {
                    display: block;
                    width: 100%;
                    height: 100%;
                    object-fit: contain;
                    cursor: none;
                }
                .ohs-custom-cursor {
                    position: absolute;
                    width: 20px;
                    height: 20px;
                    border: 2px solid #FF6B6B;
                    border-radius: 50%;
                    pointer-events: none;
                    transform: translate(-50%, -50%);
                    box-shadow: 0 0 0 2px rgba(255, 107, 107, 0.3);
                    animation: pulse 1s infinite;
                }
                @keyframes pulse {
                    0%, 100% { opacity: 1; }
                    50% { opacity: 0.5; }
                }
                .ohs-feedback {
                    padding: 15px;
                    background: #f0f0f0;
                    border-radius: 6px;
                    border-left: 4px solid #2196F3;
                    display: none;
                    flex-shrink: 0;
                }
                .ohs-feedback.show {
                    display: block;
                }
                .ohs-feedback.correct {
                    border-left-color: #4CAF50;
                    background: #e8f5e9;
                }
                .ohs-feedback.incorrect {
                    border-left-color: #f44336;
                    background: #ffebee;
                }
            </style>
            
            <div class="ohs-container">
                <!-- Canvas Wrapper (70% height, centered) -->
                <div class="ohs-canvas-wrapper">
                    <canvas id="ohsQuizCanvas" 
                            style="border: none; cursor: none;"
                            title="Click on the image to select the hotspot">
                    </canvas>
                    <div id="ohsCustomCursor" class="ohs-custom-cursor" style="display: none;"></div>
                </div>
                
                <!-- Feedback (Below Image) -->
                <div id="ohsFeedback" class="ohs-feedback"></div>
            </div>
        `;
        
        optionsContainer.innerHTML = canvasHtml;
        
        // Get canvas element
        this.canvas = document.getElementById('ohsQuizCanvas');
        if (!this.canvas) return;
        
        this.ctx = this.canvas.getContext('2d');
        
        // Load image
        const imageSrc = this.common.question.image?.src;
        if (!imageSrc) {
            optionsContainer.innerHTML = '<div style="color: red;">Error: No image found for this question</div>';
            return;
        }
        
        this.image = new Image();
        this.image.onload = () => {
            // Set canvas size to match image
            this.canvas.width = this.image.width;
            this.canvas.height = this.image.height;
            this.ctx.drawImage(this.image, 0, 0);
            console.log('Image loaded on canvas');
        };
        this.image.onerror = () => {
            console.error('Failed to load image:', imageSrc);
            optionsContainer.innerHTML = '<div style="color: red;">Error: Failed to load image</div>';
        };
        this.image.src = imageSrc;
    }

    /**
     * Attach event listeners for canvas interaction
     */
    attachEventListeners() {
        const canvas = this.canvas;
        const wrapper = canvas?.parentElement;
        if (!canvas || !wrapper) return;
        
        // Track mouse movement for custom cursor
        wrapper.addEventListener('mousemove', (e) => {
            if (this.isAnswered) return;
            
            const cursor = document.getElementById('ohsCustomCursor');
            if (cursor) {
                const rect = wrapper.getBoundingClientRect();
                cursor.style.left = (e.clientX - rect.left) + 'px';
                cursor.style.top = (e.clientY - rect.top) + 'px';
                cursor.style.display = 'block';
            }
        });
        
        wrapper.addEventListener('mouseleave', () => {
            const cursor = document.getElementById('ohsCustomCursor');
            if (cursor) cursor.style.display = 'none';
        });
        
        // Click to select
        canvas.addEventListener('click', (e) => {
            if (this.isAnswered) return;
            
            // Get click position relative to canvas display
            const canvasRect = canvas.getBoundingClientRect();
            const wrapperRect = wrapper.getBoundingClientRect();
            
            // Position within the displayed canvas
            const displayX = e.clientX - canvasRect.left;
            const displayY = e.clientY - canvasRect.top;
            
            // Scale to actual canvas coordinates
            const scaleX = canvas.width / canvasRect.width;
            const scaleY = canvas.height / canvasRect.height;
            const actualX = displayX * scaleX;
            const actualY = displayY * scaleY;
            
            // Store selected position
            this.selectedHotspot = {
                x: actualX,
                y: actualY
            };
            
            // Draw dark circle on canvas at click location
            this.drawClickCircle(actualX, actualY);
            
            // Clear previous feedback
            this.clearFeedback();
        });
    }

    /**
     * Draw dark circle on canvas at click location
     */
    drawClickCircle(x, y) {
        if (!this.canvas || !this.image) return;
        
        // Redraw image
        this.ctx.drawImage(this.image, 0, 0);
        
        // Draw filled dark circle at click location
        const radius = 20;
        this.ctx.strokeStyle = '#333333';
        this.ctx.lineWidth = 3;
        this.ctx.fillStyle = 'rgba(0, 0, 0, 0.3)';
        
        this.ctx.beginPath();
        this.ctx.arc(x, y, radius, 0, 2 * Math.PI);
        this.ctx.fill();
        this.ctx.stroke();
    }

    /**
     * Clear feedback
     */
    clearFeedback() {
        const feedback = document.getElementById('ohsFeedback');
        if (feedback) {
            feedback.classList.remove('show', 'correct', 'incorrect');
            feedback.innerHTML = '';
        }
    }

    /**
     * Show feedback message
     */
    showFeedback(message, isCorrect) {
        const feedback = document.getElementById('ohsFeedback');
        if (feedback) {
            feedback.innerHTML = message;
            feedback.classList.add('show');
            feedback.classList.add(isCorrect ? 'correct' : 'incorrect');
        }
    }

    /**
     * Check if click is within the hotspot
     */
    checkAnswer() {
        console.log('OHS.checkAnswer() called');
        
        if (!this.selectedHotspot) {
            alert('Please click on the image to select a hotspot');
            return false;
        }

        // Get hotspot definition
        const hotspot = this.common.question.image?.hotspot;
        if (!hotspot) {
            console.error('No hotspot defined in question');
            this.common.showFeedback('Error: Hotspot not defined', false);
            return false;
        }

        // Check if click is within hotspot area
        const clickX = this.selectedHotspot.x;
        const clickY = this.selectedHotspot.y;
        
        this.isCorrect = 
            clickX >= hotspot.x &&
            clickX <= hotspot.x + hotspot.width &&
            clickY >= hotspot.y &&
            clickY <= hotspot.y + hotspot.height;

        // Mark as answered
        this.isAnswered = true;
        
        // Draw correct and user answers on canvas
        this.drawAnswerVisualization(hotspot, this.isCorrect);
        
        // Show feedback
        if (this.isCorrect) {
            this.common.showFeedback('✓ Correct! You selected the right area.', true);
        } else {
            this.common.showFeedback('✗ Incorrect. The green rectangle shows the correct area.', false);
        }

        // Disable further interactions
        this.canvas.style.cursor = 'not-allowed';
        const wrapper = this.canvas.parentElement;
        wrapper.style.pointerEvents = 'none';

        return true; // Answer was submitted successfully
    }

    /**
     * Get whether the answer is correct
     */
    isAnswerCorrect() {
        return this.isCorrect || false;
    }

    /**
     * Draw visualization of correct answer and user selection
     */
    drawAnswerVisualization(hotspot, isCorrect) {
        if (!this.canvas || !this.image) return;
        
        // Redraw image
        this.ctx.drawImage(this.image, 0, 0);
        
        // Draw correct hotspot (green)
        this.ctx.strokeStyle = '#4CAF50';
        this.ctx.lineWidth = 4;
        this.ctx.fillStyle = 'rgba(76, 175, 80, 0.15)';
        this.ctx.fillRect(hotspot.x, hotspot.y, hotspot.width, hotspot.height);
        this.ctx.strokeRect(hotspot.x, hotspot.y, hotspot.width, hotspot.height);
        
        // Add "CORRECT" label
        this.ctx.fillStyle = '#4CAF50';
        this.ctx.font = 'bold 14px Arial';
        this.ctx.fillText('CORRECT', hotspot.x + 8, hotspot.y - 8);
        
        // If incorrect, draw user's selection (dark circle) again
        if (!isCorrect && this.selectedHotspot) {
            const radius = 20;
            this.ctx.strokeStyle = '#333333';
            this.ctx.lineWidth = 3;
            this.ctx.fillStyle = 'rgba(0, 0, 0, 0.3)';
            this.ctx.beginPath();
            this.ctx.arc(this.selectedHotspot.x, this.selectedHotspot.y, radius, 0, 2 * Math.PI);
            this.ctx.fill();
            this.ctx.stroke();
        }
    }
}

