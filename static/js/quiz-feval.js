/**
 * FEVAL (Fill with Evaluation) question type handler
 * Manages variables, rules, and quiz-time evaluation
 */

// ===== FEVAL Question Builder Functions =====

/**
 * Add a new variable input field
 */
function addFEVALVariable() {
    const container = document.getElementById('feval-variables-container');
    const varIndex = container.children.length;
    const varId = `feval-var-${Date.now()}-${Math.random()}`;
    
    const varElement = document.createElement('div');
    varElement.id = varId;
    varElement.style.cssText = 'background: white; padding: 12px; border-radius: 6px; margin-bottom: 10px; border: 1px solid #e0e0e0;';
    varElement.innerHTML = `
        <div style="display: grid; grid-template-columns: 1fr 2fr 40px; gap: 10px; align-items: end;">
            <div>
                <label style="font-size: 0.85em; color: #666; font-weight: 500; display: block; margin-bottom: 4px;">Variable Name</label>
                <input type="text" class="feval-var-name" placeholder="e.g., a, b, x" style="width: 100%; padding: 6px; border: 1px solid #ddd; border-radius: 4px; font-family: monospace;" value="">
            </div>
            <div>
                <label style="font-size: 0.85em; color: #666; font-weight: 500; display: block; margin-bottom: 4px;">Label (for student)</label>
                <input type="text" class="feval-var-label" placeholder="e.g., First integer" style="width: 100%; padding: 6px; border: 1px solid #ddd; border-radius: 4px;">
            </div>
            <button type="button" class="feval-var-delete" style="background: #f44336; color: white; padding: 6px 12px; border: none; border-radius: 4px; cursor: pointer; font-size: 0.85em; height: 34px;">
                <i class="fas fa-trash"></i>
            </button>
        </div>
    `;
    
    // Add delete handler
    varElement.querySelector('.feval-var-delete').addEventListener('click', (e) => {
        e.preventDefault();
        varElement.remove();
    });
    
    container.appendChild(varElement);
}

/**
 * Add a new rule input field
 */
function addFEVALRule() {
    const container = document.getElementById('feval-rules-container');
    const ruleIndex = container.children.length;
    const ruleId = `feval-rule-${Date.now()}-${Math.random()}`;
    
    const ruleElement = document.createElement('div');
    ruleElement.id = ruleId;
    ruleElement.style.cssText = 'background: white; padding: 12px; border-radius: 6px; margin-bottom: 10px; border: 1px solid #e0e0e0;';
    ruleElement.innerHTML = `
        <div style="display: grid; grid-template-columns: 1fr auto; gap: 10px; margin-bottom: 10px; align-items: end;">
            <div>
                <label style="font-size: 0.85em; color: #666; font-weight: 500; display: block; margin-bottom: 4px;">Rule Expression (Python)</label>
                <input type="text" class="feval-rule-expr" placeholder="e.g., a + b == -7  or  isinstance(a, int)" style="width: 100%; padding: 8px; border: 1px solid #ddd; border-radius: 4px; font-family: monospace;">
            </div>
            <button type="button" class="feval-rule-delete" style="background: #f44336; color: white; padding: 6px 12px; border: none; border-radius: 4px; cursor: pointer; font-size: 0.85em; height: 36px;">
                <i class="fas fa-trash"></i>
            </button>
        </div>
        <div>
            <label style="font-size: 0.85em; color: #666; font-weight: 500; display: block; margin-bottom: 4px;">Feedback Template</label>
            <input type="text" class="feval-rule-feedback" placeholder="e.g., Sum is {a+b}, not -7" style="width: 100%; padding: 8px; border: 1px solid #ddd; border-radius: 4px;">
            <small style="color: #999; display: block; margin-top: 4px; font-size: 0.8em;">Use {expression} to embed values: {a}, {a+b}, {a*b}, etc.</small>
        </div>
    `;
    
    // Add delete handler
    ruleElement.querySelector('.feval-rule-delete').addEventListener('click', (e) => {
        e.preventDefault();
        ruleElement.remove();
    });
    
    container.appendChild(ruleElement);
}

// ===== Initialize Buttons =====
document.addEventListener('DOMContentLoaded', () => {
    const addVarBtn = document.getElementById('addFEVALVariableBtn');
    if (addVarBtn) {
        addVarBtn.addEventListener('click', (e) => {
            e.preventDefault();
            addFEVALVariable();
        });
    }
    
    const addRuleBtn = document.getElementById('addFEVALRuleBtn');
    if (addRuleBtn) {
        addRuleBtn.addEventListener('click', (e) => {
            e.preventDefault();
            addFEVALRule();
        });
    }
});

// ===== Data Collection for FEVAL =====

/**
 * Collect FEVAL question data from form
 * Called by main quiz builder's collectData() function
 */
function collectFEVALData() {
    // Collect variables
    const variables = [];
    const allVarElements = document.querySelectorAll('#feval-variables-container > div');
    
    if (allVarElements.length === 0) {
        throw new Error('At least one variable is required for FEVAL questions');
    }
    
    allVarElements.forEach((varElement, idx) => {
        const varName = varElement.querySelector('.feval-var-name').value.trim();
        const varLabel = varElement.querySelector('.feval-var-label').value.trim();
        
        if (varName) {
            variables.push({
                id: `blank_${varName}`,
                variable_name: varName,
                label: varLabel || varName,
                type: 'numeric',
                placeholder: `e.g., ${idx === 0 ? '5' : idx === 1 ? '-12' : '3'}`
            });
        }
    });
    
    // Collect rules
    const rules = [];
    const allRuleElements = document.querySelectorAll('#feval-rules-container > div');
    
    if (allRuleElements.length === 0) {
        throw new Error('At least one rule is required for FEVAL questions');
    }
    
    allRuleElements.forEach((ruleElement, idx) => {
        const expression = ruleElement.querySelector('.feval-rule-expr').value.trim();
        const feedback = ruleElement.querySelector('.feval-rule-feedback').value.trim();
        
        if (expression) {
            rules.push({
                id: `rule_${idx + 1}`,
                expression: expression,
                feedback: feedback || `Rule ${idx + 1} failed`
            });
        }
    });
    
    if (variables.length === 0) {
        throw new Error(`No variables found. ${allVarElements.length} variable rows exist but all are empty. Please fill in the variable names.`);
    }
    
    if (rules.length === 0) {
        throw new Error(`No rules found. ${allRuleElements.length} rule rows exist but all are empty. Please fill in rule expressions.`);
    }
    
    // Log for debugging
    console.log('FEVAL Data collected:', { 
        variables: variables.map(v => v.variable_name), 
        rules: rules.map(r => r.expression) 
    });
    
    const question = {
        type: 'feval',
        stem: { latex: document.getElementById('stem_latex').value },
        input: {
            blanks: variables
        },
        answer: {
            rules: rules
        }
    };
    
    // Add feedback if provided
    const feedbackLatex = document.getElementById('feedback_latex').value.trim();
    if (feedbackLatex) {
        question.stem.feedback = { latex: feedbackLatex };
    }
    
    return question;
}

// ===== FEVAL Quiz Execution Functions =====

/**
 * Evaluate FEVAL rules for a question
 * Called during quiz execution
 */
function evaluateFEVALRules(rules, userInputs) {
    /**
     * Evaluate all rules and return results
     * Returns: { allCorrect: boolean, results: [{ ruleIndex, passed, feedback }] }
     */
    
    const results = [];
    const safeNamespace = { ...userInputs };
    
    // Add type constants (use these with isinstance)
    safeNamespace.int = 'int';
    safeNamespace.float = 'float';
    safeNamespace.str = 'str';
    safeNamespace.bool = 'bool';
    
    // Add safe functions to namespace
    safeNamespace.abs = Math.abs;
    safeNamespace.round = Math.round;
    safeNamespace.max = Math.max;
    safeNamespace.min = Math.min;
    safeNamespace.len = (x) => (typeof x === 'string' || Array.isArray(x)) ? x.length : 0;
    safeNamespace.sum = (arr) => Array.isArray(arr) ? arr.reduce((a, b) => a + b, 0) : 0;
    safeNamespace.isinstance = (val, type) => {
        if (type === 'int') {
            return Number.isInteger(val);
        }
        if (type === 'float') {
            return typeof val === 'number';
        }
        if (type === 'str') {
            return typeof val === 'string';
        }
        if (type === 'bool') {
            return typeof val === 'boolean';
        }
        return typeof val === typeof type;
    };
    
    let allCorrect = true;
    
    for (let i = 0; i < rules.length; i++) {
        const rule = rules[i];
        let passed = false;
        let feedback = rule.feedback || `Rule ${i + 1} failed`;
        
        try {
            // Evaluate rule expression
            const expression = rule.expression;
            const result = eval(`(function() {
                with (safeNamespace) {
                    try {
                        return (${expression});
                    } catch(e) {
                        throw new Error('Execution error: ' + e.message);
                    }
                }
            })()`);
            
            passed = !!result;
            
            // Evaluate feedback template if provided
            if (feedback && feedback.includes('{')) {
                try {
                    feedback = evaluateFeedbackTemplate(feedback, userInputs);
                } catch (e) {
                    feedback = rule.feedback || feedback;
                }
            }
        } catch (e) {
            passed = false;
            feedback = `Error evaluating rule: ${e.message}`;
            console.error(`FEVAL Rule ${i + 1} error:`, e);
        }
        
        results.push({
            ruleIndex: i,
            passed: passed,
            feedback: feedback
        });
        
        if (!passed) {
            allCorrect = false;
        }
    }
    
    return {
        allCorrect: allCorrect,
        results: results
    };
}

/**
 * Evaluate feedback template expressions
 * Replaces {expression} with evaluated results
 */
function evaluateFeedbackTemplate(template, userInputs) {
    const safeNamespace = { ...userInputs };
    
    // Add type constants
    safeNamespace.int = 'int';
    safeNamespace.float = 'float';
    safeNamespace.str = 'str';
    safeNamespace.bool = 'bool';
    
    // Add safe functions
    safeNamespace.abs = Math.abs;
    safeNamespace.round = Math.round;
    safeNamespace.max = Math.max;
    safeNamespace.min = Math.min;
    safeNamespace.sum = (arr) => Array.isArray(arr) ? arr.reduce((a, b) => a + b, 0) : 0;
    safeNamespace.isinstance = (val, type) => {
        if (type === 'int') {
            return Number.isInteger(val);
        }
        if (type === 'float') {
            return typeof val === 'number';
        }
        if (type === 'str') {
            return typeof val === 'string';
        }
        if (type === 'bool') {
            return typeof val === 'boolean';
        }
        return typeof val === typeof type;
    };
    
    return template.replace(/\{([^}]+)\}/g, (match, expression) => {
        try {
            const result = eval(`(function() { with (safeNamespace) { return (${expression}); } })()`);
            return result;
        } catch (e) {
            console.warn(`Failed to evaluate template expression: ${expression}`, e);
            return match;
        }
    });
}

/**
 * Load FEVAL question data when editing
 */
function loadFEVALQuestion(questionJson) {
    // Clear existing variables and rules
    document.getElementById('feval-variables-container').innerHTML = '';
    document.getElementById('feval-rules-container').innerHTML = '';
    
    // Load variables
    const blanks = questionJson.input?.blanks || [];
    blanks.forEach(blank => {
        addFEVALVariable();
        const lastVar = document.querySelector('#feval-variables-container > div:last-child');
        lastVar.querySelector('.feval-var-name').value = blank.variable_name || '';
        lastVar.querySelector('.feval-var-label').value = blank.label || '';
    });
    
    // Load rules
    const rules = questionJson.answer?.rules || [];
    rules.forEach(rule => {
        addFEVALRule();
        const lastRule = document.querySelector('#feval-rules-container > div:last-child');
        lastRule.querySelector('.feval-rule-expr').value = rule.expression || '';
        lastRule.querySelector('.feval-rule-feedback').value = rule.feedback || '';
    });
    
    // Load general feedback if present
    if (questionJson.feedback?.latex) {
        document.getElementById('feedback_latex').value = questionJson.feedback.latex;
    }
}

// ===== FEVAL Quiz Renderer Class =====

/**
 * QuizFEVAL - Runtime quiz handler for FEVAL questions
 * Renders variable inputs and evaluates rules
 */
class QuizFEVAL {
    constructor(common) {
        this.common = common || {};
        this.responses = {};  // Store user answers by variable name
    }

    /**
     * Render FEVAL question with variable input fields
     */
    render() {
        console.log('QuizFEVAL.render() called');
        this.renderVariables();
        this.attachEventListeners();
    }

    /**
     * Render input fields for all variables
     */
    renderVariables() {
        console.log('question.input:', this.common.question.input);
        
        if (this.common.question.input?.blanks) {
            console.log('Variables found:', this.common.question.input.blanks.length);
            
            const variablesHtml = this.common.question.input.blanks.map((blank) => {
                const label = blank.label || blank.variable_name;
                const varName = blank.variable_name;
                const inputId = `feval_${varName}`;
                const placeholder = blank.placeholder || 'Enter value';
                
                return `
                    <div style="margin-bottom: 16px;">
                        <label style="font-size: clamp(1em, 3vw, 1.3em); font-weight: 500; color: #1b3a6f; margin-bottom: 8px; display: block; line-height: 1.5;">${label}</label>
                        <input type="number" id="${inputId}" class="feval-input" placeholder="${placeholder}" step="any" style="width: 100%; max-width: 250px; padding: 10px; border: 2px solid #ccc; border-radius: 4px; font-size: 1em;">
                    </div>
                `;
            }).join('');
            
            document.getElementById('optionsContainer').innerHTML = variablesHtml;
            console.log('Variables rendered');
        } else {
            console.log('No variables found');
            document.getElementById('optionsContainer').innerHTML = '<div style="background: orange; padding: 10px;">No variables found</div>';
        }
    }

    /**
     * Attach event listeners to variable inputs
     */
    attachEventListeners() {
        document.querySelectorAll('.feval-input').forEach(input => {
            input.addEventListener('change', () => {
                this.common.clearFeedback();
            });
        });
    }

    /**
     * Check FEVAL answers by evaluating rules
     */
    checkAnswer() {
        console.log('QuizFEVAL.checkAnswer() called');
        
        // Collect user inputs
        this.responses = {};
        const blanks = this.common.question.input?.blanks || [];
        let hasEmptyField = false;
        let emptyFieldLabel = '';
        
        blanks.forEach((blank) => {
            const inputId = `feval_${blank.variable_name}`;
            const value = document.getElementById(inputId)?.value.trim();
            
            if (!value) {
                hasEmptyField = true;
                emptyFieldLabel = blank.label || blank.variable_name;
                return;
            }
            
            this.responses[blank.variable_name] = parseFloat(value);
        });
        
        if (hasEmptyField) {
            this.common.showFeedback(`Please fill in all answers`, false);
            return false;
        }
        
        // Evaluate rules
        const rules = this.common.question.answer?.rules || [];
        const evaluation = evaluateFEVALRules(rules, this.responses);
        
        console.log('FEVAL evaluation results:', evaluation);
        
        // Display input styling and per-input feedback
        this.displayFEVALFeedback(blanks, evaluation);
        
        // Build feedback message from failed rules
        let feedbackHtml = '';
        
        if (evaluation.allCorrect) {
            // All rules satisfied = CORRECT ANSWER
            this.isCorrect = true;
            feedbackHtml = '<strong style="color: green;">✓ All rules satisfied!</strong>';
            this.common.showFeedback(feedbackHtml, true);
            return true;  // Correct answer
        } else {
            // Some rules not satisfied = INCORRECT ANSWER
            this.isCorrect = false;
            const failedRules = evaluation.results.filter(r => !r.passed);
            feedbackHtml = failedRules.map(r => `<div style="color: #d32f2f; margin: 8px 0;">${r.feedback}</div>`).join('');
            this.common.showFeedback(feedbackHtml, false);
            return false;  // Incorrect answer
        }
    }

    /**
     * Display feedback styling for FEVAL inputs (similar to FILL)
     */
    displayFEVALFeedback(blanks, evaluation) {
        // Clear existing feedback indicators
        document.querySelectorAll('.feval-feedback-indicator').forEach(el => el.remove());
        
        blanks.forEach((blank) => {
            const inputId = `feval_${blank.variable_name}`;
            const inputElement = document.getElementById(inputId);
            
            if (!inputElement) return;
            
            // Determine if this blank's answers satisfy all rules (conservative: all rules must pass)
            // For FEVAL, we mark inputs based on whether all rules pass
            const allRulesPassed = evaluation.allCorrect;
            
            // Apply styling based on correctness
            if (allRulesPassed) {
                inputElement.classList.add('correct-answer');
                inputElement.classList.remove('incorrect-answer');
                
                // Add checkmark indicator
                const indicator = document.createElement('span');
                indicator.className = 'feval-feedback-indicator';
                indicator.innerHTML = '<span style="color: #4CAF50; font-size: 1.3em; margin-left: 12px; font-weight: bold;">✓</span>';
                indicator.style.display = 'inline-flex';
                indicator.style.alignItems = 'center';
                
                inputElement.parentElement.appendChild(indicator);
            } else {
                inputElement.classList.add('incorrect-answer');
                inputElement.classList.remove('correct-answer');
                
                // Add X indicator
                const indicator = document.createElement('span');
                indicator.className = 'feval-feedback-indicator';
                indicator.innerHTML = '<span style="color: #f44336; font-size: 1.3em; margin-left: 12px; font-weight: bold;">✗</span>';
                indicator.style.display = 'inline-flex';
                indicator.style.alignItems = 'center';
                
                inputElement.parentElement.appendChild(indicator);
            }
        });
    }

    /**
     * Get whether the answer is correct
     */
    isAnswerCorrect() {
        return this.isCorrect || false;
    }
}

// Export functions for use in main builder
window.collectFEVALData = collectFEVALData;
window.evaluateFEVALRules = evaluateFEVALRules;
window.evaluateFeedbackTemplate = evaluateFeedbackTemplate;
window.loadFEVALQuestion = loadFEVALQuestion;
window.addFEVALVariable = addFEVALVariable;
window.addFEVALRule = addFEVALRule;
window.QuizFEVAL = QuizFEVAL;
