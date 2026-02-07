#!/usr/bin/env python3
"""
SLATE Guided Workflow UI Component
===================================

Generates the HTML and JavaScript for the guided workflow submission interface.
This component integrates with the main dashboard template.

The UI provides:
- Step-by-step job submission wizard
- Job template selection cards
- Pipeline progress visualization
- AI-powered contextual help
"""


def get_guided_workflow_css() -> str:
    """Return CSS styles for the guided workflow component."""
    return '''
        /* ═══════════════════════════════════════════════════════════════
           Guided Workflow Component Styles
           ═══════════════════════════════════════════════════════════════ */

        /* Modal Overlay */
        .workflow-guide-overlay {
            position: fixed;
            inset: 0;
            background: rgba(0, 0, 0, 0.85);
            backdrop-filter: blur(8px);
            z-index: 1000;
            display: none;
            justify-content: center;
            align-items: center;
            opacity: 0;
            transition: opacity 0.3s ease;
        }
        .workflow-guide-overlay.active {
            display: flex;
            opacity: 1;
        }

        /* Guide Container */
        .workflow-guide {
            background: var(--sl-bg-surface);
            border: 1px solid var(--sl-border);
            border-radius: var(--sl-radius-lg);
            width: 90%;
            max-width: 720px;
            max-height: 85vh;
            overflow: hidden;
            display: flex;
            flex-direction: column;
            box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.5),
                        inset 0 1px 0 rgba(184, 115, 51, 0.1);
        }

        /* Guide Header */
        .guide-header {
            padding: var(--sl-space-4) var(--sl-space-5);
            border-bottom: 1px solid var(--sl-border);
            display: flex;
            align-items: center;
            justify-content: space-between;
            background: linear-gradient(135deg, rgba(184, 115, 51, 0.05) 0%, transparent 50%);
        }
        .guide-header h2 {
            font-size: 1.1rem;
            font-weight: 600;
            color: var(--sl-text-primary);
            display: flex;
            align-items: center;
            gap: var(--sl-space-2);
        }
        .guide-header h2::before {
            content: '';
            width: 8px;
            height: 8px;
            background: var(--sl-copper);
            border-radius: 50%;
            animation: pulse-copper 2s infinite;
        }
        @keyframes pulse-copper {
            0%, 100% { opacity: 1; transform: scale(1); }
            50% { opacity: 0.5; transform: scale(1.2); }
        }

        .guide-close {
            background: transparent;
            border: none;
            color: var(--sl-text-secondary);
            cursor: pointer;
            padding: var(--sl-space-1);
            border-radius: var(--sl-radius-sm);
            transition: all 0.2s;
        }
        .guide-close:hover {
            background: var(--sl-bg-hover);
            color: var(--sl-text-primary);
        }

        /* Progress Bar */
        .guide-progress {
            padding: var(--sl-space-3) var(--sl-space-5);
            background: var(--sl-bg-inset);
            display: flex;
            align-items: center;
            gap: var(--sl-space-2);
        }
        .progress-track {
            flex: 1;
            height: 4px;
            background: var(--sl-bg-surface);
            border-radius: 2px;
            overflow: hidden;
        }
        .progress-fill {
            height: 100%;
            background: linear-gradient(90deg, var(--sl-copper), var(--sl-copper-light));
            border-radius: 2px;
            transition: width 0.5s ease;
        }
        .progress-label {
            font-size: 0.7rem;
            color: var(--sl-text-secondary);
            min-width: 60px;
            text-align: right;
        }

        /* Step Content */
        .guide-content {
            flex: 1;
            padding: var(--sl-space-5);
            overflow-y: auto;
        }
        .guide-content h3 {
            font-size: 1rem;
            font-weight: 600;
            margin-bottom: var(--sl-space-2);
            color: var(--sl-text-primary);
        }
        .guide-content p {
            color: var(--sl-text-secondary);
            font-size: 0.85rem;
            margin-bottom: var(--sl-space-4);
            line-height: 1.6;
        }

        /* Category/Template Cards */
        .guide-cards {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
            gap: var(--sl-space-3);
        }
        .guide-card {
            background: var(--sl-bg-inset);
            border: 1px solid var(--sl-border);
            border-radius: var(--sl-radius-md);
            padding: var(--sl-space-4);
            cursor: pointer;
            transition: all 0.2s;
            position: relative;
            overflow: hidden;
        }
        .guide-card:hover {
            border-color: var(--sl-copper);
            background: var(--sl-bg-hover);
            transform: translateY(-2px);
        }
        .guide-card.selected {
            border-color: var(--sl-copper);
            background: rgba(184, 115, 51, 0.1);
        }
        .guide-card.selected::after {
            content: '\\2713';
            position: absolute;
            top: var(--sl-space-2);
            right: var(--sl-space-2);
            background: var(--sl-copper);
            color: white;
            width: 20px;
            height: 20px;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 0.7rem;
        }
        .card-icon {
            font-size: 1.5rem;
            margin-bottom: var(--sl-space-2);
            opacity: 0.8;
        }
        .card-label {
            font-weight: 600;
            font-size: 0.85rem;
            color: var(--sl-text-primary);
            margin-bottom: var(--sl-space-1);
        }
        .card-desc {
            font-size: 0.7rem;
            color: var(--sl-text-secondary);
            line-height: 1.4;
        }
        .card-meta {
            margin-top: var(--sl-space-2);
            font-size: 0.65rem;
            color: var(--sl-text-disabled);
            display: flex;
            gap: var(--sl-space-2);
        }
        .card-meta .ai-badge {
            background: linear-gradient(135deg, #7c3aed, #4f46e5);
            color: white;
            padding: 1px 6px;
            border-radius: var(--sl-radius-xs);
            font-weight: 500;
        }

        /* Job Summary */
        .job-summary {
            background: var(--sl-bg-inset);
            border: 1px solid var(--sl-border);
            border-radius: var(--sl-radius-md);
            padding: var(--sl-space-4);
        }
        .summary-row {
            display: flex;
            justify-content: space-between;
            padding: var(--sl-space-2) 0;
            border-bottom: 1px solid var(--sl-border-subtle);
            font-size: 0.8rem;
        }
        .summary-row:last-child {
            border-bottom: none;
        }
        .summary-label {
            color: var(--sl-text-secondary);
        }
        .summary-value {
            color: var(--sl-text-primary);
            font-weight: 500;
        }

        /* Pipeline Visualization */
        .pipeline-viz {
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: var(--sl-space-4);
            background: var(--sl-bg-inset);
            border-radius: var(--sl-radius-md);
            margin-top: var(--sl-space-4);
        }
        .pipeline-stage {
            display: flex;
            flex-direction: column;
            align-items: center;
            gap: var(--sl-space-2);
            flex: 1;
        }
        .stage-icon {
            width: 48px;
            height: 48px;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 1.2rem;
            background: var(--sl-bg-surface);
            border: 2px solid var(--sl-border);
            transition: all 0.3s;
        }
        .stage-icon.pending { border-color: var(--sl-text-disabled); opacity: 0.5; }
        .stage-icon.active { border-color: var(--sl-copper); animation: pulse-border 1.5s infinite; }
        .stage-icon.complete { border-color: var(--sl-success); background: rgba(74, 124, 89, 0.2); }
        @keyframes pulse-border {
            0%, 100% { box-shadow: 0 0 0 0 rgba(184, 115, 51, 0.4); }
            50% { box-shadow: 0 0 0 8px rgba(184, 115, 51, 0); }
        }
        .stage-label {
            font-size: 0.7rem;
            color: var(--sl-text-secondary);
            text-align: center;
        }
        .pipeline-connector {
            flex: 0.5;
            height: 2px;
            background: var(--sl-border);
            position: relative;
        }
        .pipeline-connector.active::after {
            content: '';
            position: absolute;
            left: 0;
            top: 0;
            height: 100%;
            background: var(--sl-copper);
            animation: flow 1s linear infinite;
            width: 50%;
        }
        @keyframes flow {
            0% { transform: translateX(-100%); }
            100% { transform: translateX(200%); }
        }

        /* Narration Box */
        .narration-box {
            background: linear-gradient(135deg, rgba(184, 115, 51, 0.08) 0%, rgba(184, 115, 51, 0.02) 100%);
            border: 1px solid rgba(184, 115, 51, 0.2);
            border-radius: var(--sl-radius-md);
            padding: var(--sl-space-4);
            margin-top: var(--sl-space-4);
            display: flex;
            gap: var(--sl-space-3);
            align-items: flex-start;
        }
        .narration-icon {
            width: 32px;
            height: 32px;
            background: var(--sl-copper);
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 0.9rem;
            flex-shrink: 0;
        }
        .narration-text {
            font-size: 0.8rem;
            color: var(--sl-text-secondary);
            line-height: 1.6;
        }

        /* Guide Footer */
        .guide-footer {
            padding: var(--sl-space-4) var(--sl-space-5);
            border-top: 1px solid var(--sl-border);
            display: flex;
            justify-content: space-between;
            align-items: center;
            background: var(--sl-bg-inset);
        }
        .guide-btn {
            padding: var(--sl-space-2) var(--sl-space-4);
            border-radius: var(--sl-radius-sm);
            font-size: 0.8rem;
            font-weight: 500;
            cursor: pointer;
            transition: all 0.2s;
            border: 1px solid transparent;
        }
        .guide-btn-secondary {
            background: transparent;
            border-color: var(--sl-border);
            color: var(--sl-text-secondary);
        }
        .guide-btn-secondary:hover {
            background: var(--sl-bg-hover);
            color: var(--sl-text-primary);
        }
        .guide-btn-primary {
            background: var(--sl-copper);
            color: white;
            border-color: var(--sl-copper);
        }
        .guide-btn-primary:hover {
            background: var(--sl-copper-dark);
        }
        .guide-btn:disabled {
            opacity: 0.5;
            cursor: not-allowed;
        }

        /* Quick Submit Button (for main dashboard) */
        .quick-submit-btn {
            position: fixed;
            bottom: var(--sl-space-5);
            right: var(--sl-space-5);
            width: 56px;
            height: 56px;
            border-radius: 50%;
            background: linear-gradient(135deg, var(--sl-copper), var(--sl-copper-dark));
            border: none;
            cursor: pointer;
            box-shadow: 0 4px 15px rgba(184, 115, 51, 0.4);
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 1.5rem;
            color: white;
            transition: all 0.3s;
            z-index: 100;
        }
        .quick-submit-btn:hover {
            transform: scale(1.1);
            box-shadow: 0 6px 20px rgba(184, 115, 51, 0.5);
        }
        .quick-submit-btn::after {
            content: 'Submit Job';
            position: absolute;
            right: 70px;
            background: var(--sl-bg-surface);
            color: var(--sl-text-primary);
            padding: var(--sl-space-2) var(--sl-space-3);
            border-radius: var(--sl-radius-sm);
            font-size: 0.75rem;
            white-space: nowrap;
            opacity: 0;
            pointer-events: none;
            transition: opacity 0.2s;
            border: 1px solid var(--sl-border);
        }
        .quick-submit-btn:hover::after {
            opacity: 1;
        }
'''


def get_guided_workflow_html() -> str:
    """Return HTML for the guided workflow component."""
    return '''
        <!-- Guided Workflow Modal -->
        <div class="workflow-guide-overlay" id="workflow-guide-overlay">
            <div class="workflow-guide" id="workflow-guide">
                <div class="guide-header">
                    <h2>Workflow Submission Guide</h2>
                    <button class="guide-close" onclick="closeWorkflowGuide()">&times;</button>
                </div>

                <div class="guide-progress">
                    <div class="progress-track">
                        <div class="progress-fill" id="guide-progress-fill" style="width: 0%"></div>
                    </div>
                    <span class="progress-label" id="guide-progress-label">Step 1/8</span>
                </div>

                <div class="guide-content" id="guide-content">
                    <!-- Dynamic content inserted by JavaScript -->
                </div>

                <div class="guide-footer">
                    <button class="guide-btn guide-btn-secondary" id="guide-back" onclick="guideBack()" disabled>Back</button>
                    <button class="guide-btn guide-btn-primary" id="guide-next" onclick="guideNext()">Get Started</button>
                </div>
            </div>
        </div>

        <!-- Quick Submit FAB -->
        <button class="quick-submit-btn" onclick="openWorkflowGuide()" title="Submit a job to the workflow">
            +
        </button>
'''


def get_guided_workflow_js() -> str:
    """Return JavaScript for the guided workflow component."""
    return '''
        // ═══════════════════════════════════════════════════════════════
        // Guided Workflow Submission System
        // ═══════════════════════════════════════════════════════════════

        const workflowGuide = {
            active: false,
            currentStep: 0,
            totalSteps: 8,
            selectedCategory: null,
            selectedTemplate: null,
            jobConfig: {},
            jobId: null,
            templates: []
        };

        const categoryIcons = {
            testing: '&#128248;',      // test tube
            ai_analysis: '&#129504;',  // brain
            maintenance: '&#128295;',   // wrench
            deployment: '&#128640;',    // rocket
            custom: '&#9998;'           // pencil
        };

        const stageIcons = {
            task_queue: 'T',
            runner: 'R',
            workflow: 'W',
            validation: '&#10003;',
            completion: '&#9733;'
        };

        function openWorkflowGuide() {
            document.getElementById('workflow-guide-overlay').classList.add('active');
            workflowGuide.active = true;
            startWorkflowGuide();
        }

        function closeWorkflowGuide() {
            document.getElementById('workflow-guide-overlay').classList.remove('active');
            workflowGuide.active = false;
            resetWorkflowGuide();
        }

        function resetWorkflowGuide() {
            workflowGuide.currentStep = 0;
            workflowGuide.selectedCategory = null;
            workflowGuide.selectedTemplate = null;
            workflowGuide.jobConfig = {};
            workflowGuide.jobId = null;
            fetch('/api/workflow/guide/reset', { method: 'POST' }).catch(() => {});
        }

        async function startWorkflowGuide() {
            try {
                const res = await fetch('/api/workflow/guide/start', { method: 'POST' });
                const data = await res.json();
                if (data.success) {
                    workflowGuide.templates = data.templates || [];
                    renderGuideStep(data.step);
                }
            } catch (e) {
                console.error('Failed to start workflow guide:', e);
            }
        }

        function updateProgress() {
            const pct = ((workflowGuide.currentStep + 1) / workflowGuide.totalSteps) * 100;
            document.getElementById('guide-progress-fill').style.width = pct + '%';
            document.getElementById('guide-progress-label').textContent =
                'Step ' + (workflowGuide.currentStep + 1) + '/' + workflowGuide.totalSteps;
        }

        function renderGuideStep(step) {
            const content = document.getElementById('guide-content');
            const backBtn = document.getElementById('guide-back');
            const nextBtn = document.getElementById('guide-next');

            updateProgress();

            // Enable/disable back button
            backBtn.disabled = workflowGuide.currentStep === 0;

            // Render based on step type
            switch (step.id) {
                case 'welcome':
                    renderWelcomeStep(content, step);
                    nextBtn.textContent = 'Get Started';
                    break;
                case 'select_category':
                    renderCategoryStep(content, step);
                    nextBtn.textContent = 'Continue';
                    nextBtn.disabled = !workflowGuide.selectedCategory;
                    break;
                case 'select_template':
                    renderTemplateStep(content, step);
                    nextBtn.textContent = 'Continue';
                    nextBtn.disabled = !workflowGuide.selectedTemplate;
                    break;
                case 'configure_job':
                    renderConfigureStep(content, step);
                    nextBtn.textContent = 'Review';
                    break;
                case 'review_job':
                    renderReviewStep(content, step);
                    nextBtn.textContent = 'Submit Job';
                    break;
                case 'submit_job':
                    renderSubmittingStep(content, step);
                    nextBtn.disabled = true;
                    break;
                case 'observe_pipeline':
                    renderPipelineStep(content, step);
                    nextBtn.textContent = 'Finish';
                    nextBtn.disabled = false;
                    break;
                case 'complete':
                    renderCompleteStep(content, step);
                    nextBtn.textContent = 'Close';
                    break;
                default:
                    content.innerHTML = '<p>Unknown step</p>';
            }
        }

        function renderWelcomeStep(container, step) {
            container.innerHTML = `
                <h3>${step.title}</h3>
                <p>${step.instruction}</p>
                <div class="pipeline-viz">
                    <div class="pipeline-stage">
                        <div class="stage-icon">${stageIcons.task_queue}</div>
                        <span class="stage-label">Task Queue</span>
                    </div>
                    <div class="pipeline-connector"></div>
                    <div class="pipeline-stage">
                        <div class="stage-icon">${stageIcons.runner}</div>
                        <span class="stage-label">Runner</span>
                    </div>
                    <div class="pipeline-connector"></div>
                    <div class="pipeline-stage">
                        <div class="stage-icon">${stageIcons.workflow}</div>
                        <span class="stage-label">Workflow</span>
                    </div>
                    <div class="pipeline-connector"></div>
                    <div class="pipeline-stage">
                        <div class="stage-icon">${stageIcons.completion}</div>
                        <span class="stage-label">Complete</span>
                    </div>
                </div>
                <div class="narration-box">
                    <div class="narration-icon">&#128161;</div>
                    <div class="narration-text">
                        Jobs you submit flow through this pipeline automatically.
                        The runner picks up tasks, triggers GitHub workflows, and reports results back to the dashboard.
                    </div>
                </div>
            `;
        }

        function renderCategoryStep(container, step) {
            const categories = [
                { id: 'testing', label: 'Testing', icon: categoryIcons.testing, desc: 'Run tests and validations' },
                { id: 'ai_analysis', label: 'AI Analysis', icon: categoryIcons.ai_analysis, desc: 'Local AI code review' },
                { id: 'maintenance', label: 'Maintenance', icon: categoryIcons.maintenance, desc: 'Cleanup and checks' },
                { id: 'deployment', label: 'Deployment', icon: categoryIcons.deployment, desc: 'Build and deploy' },
                { id: 'custom', label: 'Custom Task', icon: categoryIcons.custom, desc: 'Create custom job' }
            ];

            container.innerHTML = `
                <h3>${step.title}</h3>
                <p>${step.instruction}</p>
                <div class="guide-cards">
                    ${categories.map(c => `
                        <div class="guide-card ${workflowGuide.selectedCategory === c.id ? 'selected' : ''}"
                             onclick="selectCategory('${c.id}')">
                            <div class="card-icon">${c.icon}</div>
                            <div class="card-label">${c.label}</div>
                            <div class="card-desc">${c.desc}</div>
                        </div>
                    `).join('')}
                </div>
            `;
        }

        async function selectCategory(category) {
            workflowGuide.selectedCategory = category;
            try {
                const res = await fetch('/api/workflow/guide/category/' + category, { method: 'POST' });
                const data = await res.json();
                if (data.success) {
                    workflowGuide.templates = data.templates || [];
                }
            } catch (e) {}
            // Re-render to show selection
            renderCategoryStep(document.getElementById('guide-content'), {
                id: 'select_category',
                title: 'Select Job Category',
                instruction: 'Choose the category that best matches your task:'
            });
            document.getElementById('guide-next').disabled = false;
        }

        function renderTemplateStep(container, step) {
            const templates = workflowGuide.templates.filter(t =>
                t.category === workflowGuide.selectedCategory ||
                t.id === 'custom_task' ||
                workflowGuide.selectedCategory === 'custom'
            );

            container.innerHTML = `
                <h3>${step.title}</h3>
                <p>Available templates for ${workflowGuide.selectedCategory}:</p>
                <div class="guide-cards">
                    ${templates.map(t => `
                        <div class="guide-card ${workflowGuide.selectedTemplate?.id === t.id ? 'selected' : ''}"
                             onclick="selectTemplate('${t.id}')">
                            <div class="card-label">${t.name}</div>
                            <div class="card-desc">${t.description}</div>
                            <div class="card-meta">
                                <span>${t.estimated_duration}</span>
                                ${t.ai_capable ? '<span class="ai-badge">AI</span>' : ''}
                            </div>
                        </div>
                    `).join('')}
                </div>
            `;
        }

        async function selectTemplate(templateId) {
            const template = workflowGuide.templates.find(t => t.id === templateId);
            workflowGuide.selectedTemplate = template;
            try {
                await fetch('/api/workflow/guide/template/' + templateId, { method: 'POST' });
            } catch (e) {}
            renderTemplateStep(document.getElementById('guide-content'), {
                id: 'select_template',
                title: 'Select Job Template'
            });
            document.getElementById('guide-next').disabled = false;
        }

        function renderConfigureStep(container, step) {
            const t = workflowGuide.selectedTemplate;
            if (!t) return;

            container.innerHTML = `
                <h3>Configure: ${t.name}</h3>
                <p>Adjust parameters or accept defaults:</p>
                <div class="job-summary">
                    <div class="summary-row">
                        <span class="summary-label">Template</span>
                        <span class="summary-value">${t.name}</span>
                    </div>
                    <div class="summary-row">
                        <span class="summary-label">Workflow</span>
                        <span class="summary-value">${t.workflow}</span>
                    </div>
                    <div class="summary-row">
                        <span class="summary-label">Est. Duration</span>
                        <span class="summary-value">${t.estimated_duration}</span>
                    </div>
                </div>
                <div class="narration-box">
                    <div class="narration-icon">&#9881;</div>
                    <div class="narration-text">
                        This template is pre-configured for optimal results.
                        For most cases, the default settings work well.
                    </div>
                </div>
            `;
        }

        function renderReviewStep(container, step) {
            const t = workflowGuide.selectedTemplate;
            if (!t) return;

            container.innerHTML = `
                <h3>Review Job Details</h3>
                <p>Confirm your job configuration before submission:</p>
                <div class="job-summary">
                    <div class="summary-row">
                        <span class="summary-label">Job Name</span>
                        <span class="summary-value">${t.name}</span>
                    </div>
                    <div class="summary-row">
                        <span class="summary-label">Category</span>
                        <span class="summary-value">${workflowGuide.selectedCategory}</span>
                    </div>
                    <div class="summary-row">
                        <span class="summary-label">Workflow</span>
                        <span class="summary-value">${t.workflow}</span>
                    </div>
                    <div class="summary-row">
                        <span class="summary-label">AI-Powered</span>
                        <span class="summary-value">${t.ai_capable ? 'Yes' : 'No'}</span>
                    </div>
                    <div class="summary-row">
                        <span class="summary-label">Priority</span>
                        <span class="summary-value">${t.priority}/10</span>
                    </div>
                    <div class="summary-row">
                        <span class="summary-label">Est. Duration</span>
                        <span class="summary-value">${t.estimated_duration}</span>
                    </div>
                </div>
            `;
        }

        function renderSubmittingStep(container, step) {
            container.innerHTML = `
                <h3>Submitting Job...</h3>
                <p>Your job is being added to the workflow pipeline.</p>
                <div style="text-align: center; padding: 40px;">
                    <div style="font-size: 2rem; animation: pulse-copper 1s infinite;">&#128336;</div>
                    <p style="margin-top: 16px; color: var(--sl-text-secondary);">Processing...</p>
                </div>
            `;
        }

        function renderPipelineStep(container, step) {
            container.innerHTML = `
                <h3>Job Submitted!</h3>
                <p>Your job (ID: ${workflowGuide.jobId || 'pending'}) is now in the pipeline.</p>
                <div class="pipeline-viz">
                    <div class="pipeline-stage">
                        <div class="stage-icon complete">${stageIcons.task_queue}</div>
                        <span class="stage-label">Queued</span>
                    </div>
                    <div class="pipeline-connector active"></div>
                    <div class="pipeline-stage">
                        <div class="stage-icon active">${stageIcons.runner}</div>
                        <span class="stage-label">Runner</span>
                    </div>
                    <div class="pipeline-connector"></div>
                    <div class="pipeline-stage">
                        <div class="stage-icon pending">${stageIcons.workflow}</div>
                        <span class="stage-label">Workflow</span>
                    </div>
                    <div class="pipeline-connector"></div>
                    <div class="pipeline-stage">
                        <div class="stage-icon pending">${stageIcons.completion}</div>
                        <span class="stage-label">Complete</span>
                    </div>
                </div>
                <div class="narration-box">
                    <div class="narration-icon">&#128161;</div>
                    <div class="narration-text">
                        Track progress in the Workflow Pipeline panel on the Overview page,
                        or check the Workflows page for detailed status.
                    </div>
                </div>
            `;
        }

        function renderCompleteStep(container, step) {
            container.innerHTML = `
                <h3>All Done!</h3>
                <p>Your job has been submitted to the SLATE workflow pipeline.</p>
                <div class="job-summary">
                    <div class="summary-row">
                        <span class="summary-label">Job ID</span>
                        <span class="summary-value">${workflowGuide.jobId || 'N/A'}</span>
                    </div>
                    <div class="summary-row">
                        <span class="summary-label">Status</span>
                        <span class="summary-value" style="color: var(--sl-success);">Submitted</span>
                    </div>
                </div>
                <div class="narration-box">
                    <div class="narration-icon">&#127881;</div>
                    <div class="narration-text">
                        You can submit another job anytime using the + button in the corner,
                        or use the Quick Actions on the dashboard for common operations.
                    </div>
                </div>
            `;
        }

        async function guideNext() {
            const stepIds = ['welcome', 'select_category', 'select_template', 'configure_job',
                            'review_job', 'submit_job', 'observe_pipeline', 'complete'];

            if (workflowGuide.currentStep >= stepIds.length - 1) {
                closeWorkflowGuide();
                return;
            }

            workflowGuide.currentStep++;
            const nextStepId = stepIds[workflowGuide.currentStep];

            // Handle special steps
            if (nextStepId === 'submit_job') {
                renderGuideStep({ id: 'submit_job', title: 'Submitting...' });
                try {
                    const res = await fetch('/api/workflow/guide/submit', { method: 'POST' });
                    const data = await res.json();
                    if (data.success) {
                        workflowGuide.jobId = data.job_id;
                        workflowGuide.currentStep++;
                        renderGuideStep({ id: 'observe_pipeline', title: 'Pipeline Status' });
                        showToast('Job submitted: ' + data.job_id);
                        // Refresh tasks in background
                        setTimeout(refreshTasks, 1000);
                    } else {
                        showToast('Submission failed: ' + (data.error || 'Unknown error'), 'error');
                    }
                } catch (e) {
                    showToast('Submission failed', 'error');
                }
                return;
            }

            if (nextStepId === 'configure_job') {
                try {
                    await fetch('/api/workflow/guide/configure', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ parameters: {} })
                    });
                } catch (e) {}
            }

            renderGuideStep({ id: nextStepId, title: '' });
        }

        function guideBack() {
            if (workflowGuide.currentStep > 0) {
                workflowGuide.currentStep--;
                const stepIds = ['welcome', 'select_category', 'select_template', 'configure_job',
                                'review_job', 'submit_job', 'observe_pipeline', 'complete'];
                renderGuideStep({ id: stepIds[workflowGuide.currentStep], title: '' });
            }
        }

        // Toast notification helper
        function showToast(message, type = 'info') {
            const toast = document.createElement('div');
            toast.style.cssText = `
                position: fixed;
                bottom: 80px;
                right: 20px;
                background: ${type === 'error' ? 'var(--sl-error)' : 'var(--sl-bg-surface)'};
                color: var(--sl-text-primary);
                padding: 12px 20px;
                border-radius: 8px;
                box-shadow: 0 4px 12px rgba(0,0,0,0.3);
                z-index: 1001;
                font-size: 0.85rem;
                border: 1px solid var(--sl-border);
                animation: slideIn 0.3s ease;
            `;
            toast.textContent = message;
            document.body.appendChild(toast);
            setTimeout(() => toast.remove(), 4000);
        }
'''


def get_complete_guided_workflow_component() -> str:
    """Return the complete guided workflow component (CSS + HTML + JS)."""
    return f'''
        <!-- Guided Workflow Styles -->
        <style>
{get_guided_workflow_css()}
        </style>

        {get_guided_workflow_html()}

        <script>
{get_guided_workflow_js()}
        </script>
'''
