#!/usr/bin/env python3
"""
SLATE Control Panel UI
=======================

Practical, button-driven interface. Real buttons, real commands,
clear feedback, step-by-step guidance.
"""


def get_control_panel_css() -> str:
    """CSS for the control panel."""
    return '''
        /* ═══════════════════════════════════════════════════════════════
           SLATE Control Panel - Practical Button-Driven UI
           ═══════════════════════════════════════════════════════════════ */

        .control-panel-overlay {
            position: fixed;
            inset: 0;
            background: rgba(0, 0, 0, 0.92);
            z-index: 2000;
            display: none;
            overflow-y: auto;
        }
        .control-panel-overlay.active {
            display: block;
        }

        .control-panel {
            max-width: 1200px;
            margin: 0 auto;
            padding: 24px;
        }

        /* Header */
        .cp-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 24px;
            padding-bottom: 16px;
            border-bottom: 1px solid var(--sl-border);
        }
        .cp-title {
            font-size: 1.4rem;
            font-weight: 600;
            color: var(--sl-text-primary);
        }
        .cp-close {
            background: var(--sl-bg-surface);
            border: 1px solid var(--sl-border);
            color: var(--sl-text-secondary);
            padding: 8px 20px;
            border-radius: 6px;
            cursor: pointer;
            font-size: 0.85rem;
        }
        .cp-close:hover {
            background: var(--sl-bg-hover);
            color: var(--sl-text-primary);
        }

        /* System Status Bar */
        .cp-status-bar {
            display: flex;
            gap: 24px;
            padding: 16px 20px;
            background: var(--sl-bg-surface);
            border: 1px solid var(--sl-border);
            border-radius: 8px;
            margin-bottom: 24px;
        }
        .cp-status-item {
            display: flex;
            align-items: center;
            gap: 8px;
            font-size: 0.8rem;
        }
        .cp-status-dot {
            width: 8px;
            height: 8px;
            border-radius: 50%;
        }
        .cp-status-dot.online { background: #4ade80; }
        .cp-status-dot.offline { background: #ef4444; }
        .cp-status-dot.unknown { background: #6b7280; }
        .cp-status-label {
            color: var(--sl-text-secondary);
        }
        .cp-status-value {
            color: var(--sl-text-primary);
            font-weight: 500;
        }

        /* Guided Sequences Section */
        .cp-sequences {
            margin-bottom: 32px;
        }
        .cp-section-title {
            font-size: 0.75rem;
            color: var(--sl-text-disabled);
            text-transform: uppercase;
            letter-spacing: 0.1em;
            margin-bottom: 12px;
        }
        .cp-sequence-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
            gap: 12px;
        }
        .cp-sequence-card {
            background: var(--sl-bg-surface);
            border: 1px solid var(--sl-border);
            border-radius: 10px;
            padding: 16px 20px;
            cursor: pointer;
            transition: all 0.2s;
        }
        .cp-sequence-card:hover {
            border-color: var(--sl-copper);
            transform: translateY(-2px);
        }
        .cp-sequence-name {
            font-size: 0.95rem;
            font-weight: 600;
            color: var(--sl-text-primary);
            margin-bottom: 4px;
        }
        .cp-sequence-desc {
            font-size: 0.75rem;
            color: var(--sl-text-secondary);
            margin-bottom: 8px;
        }
        .cp-sequence-meta {
            font-size: 0.7rem;
            color: var(--sl-copper);
        }

        /* Active Sequence Display */
        .cp-active-sequence {
            background: linear-gradient(135deg, rgba(184, 115, 51, 0.1) 0%, rgba(184, 115, 51, 0.02) 100%);
            border: 1px solid var(--sl-copper);
            border-radius: 12px;
            padding: 24px;
            margin-bottom: 32px;
            display: none;
        }
        .cp-active-sequence.active {
            display: block;
        }
        .cp-seq-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 16px;
        }
        .cp-seq-title {
            font-size: 1.1rem;
            font-weight: 600;
            color: var(--sl-copper);
        }
        .cp-seq-cancel {
            background: transparent;
            border: 1px solid var(--sl-border);
            color: var(--sl-text-secondary);
            padding: 6px 14px;
            border-radius: 4px;
            cursor: pointer;
            font-size: 0.75rem;
        }
        .cp-seq-progress {
            display: flex;
            align-items: center;
            gap: 8px;
            margin-bottom: 16px;
        }
        .cp-seq-progress-bar {
            flex: 1;
            height: 6px;
            background: var(--sl-bg-inset);
            border-radius: 3px;
            overflow: hidden;
        }
        .cp-seq-progress-fill {
            height: 100%;
            background: var(--sl-copper);
            border-radius: 3px;
            transition: width 0.3s;
        }
        .cp-seq-progress-text {
            font-size: 0.75rem;
            color: var(--sl-text-secondary);
            min-width: 60px;
        }
        .cp-seq-instruction {
            font-size: 0.9rem;
            color: var(--sl-text-primary);
            padding: 12px 16px;
            background: var(--sl-bg-surface);
            border-radius: 6px;
            margin-bottom: 16px;
        }
        .cp-seq-buttons {
            display: flex;
            gap: 12px;
        }
        .cp-seq-run {
            background: var(--sl-copper);
            border: none;
            color: white;
            padding: 10px 24px;
            border-radius: 6px;
            cursor: pointer;
            font-size: 0.85rem;
            font-weight: 500;
        }
        .cp-seq-run:hover {
            background: #9a5f2a;
        }
        .cp-seq-run:disabled {
            opacity: 0.5;
            cursor: not-allowed;
        }
        .cp-seq-run.running {
            background: #6b7280;
        }
        .cp-seq-skip {
            background: transparent;
            border: 1px solid var(--sl-border);
            color: var(--sl-text-secondary);
            padding: 10px 20px;
            border-radius: 6px;
            cursor: pointer;
            font-size: 0.85rem;
        }

        /* Action Categories */
        .cp-categories {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
            gap: 20px;
        }
        .cp-category {
            background: var(--sl-bg-surface);
            border: 1px solid var(--sl-border);
            border-radius: 12px;
            overflow: hidden;
        }
        .cp-category-header {
            padding: 14px 18px;
            background: var(--sl-bg-inset);
            border-bottom: 1px solid var(--sl-border);
            font-size: 0.85rem;
            font-weight: 600;
            color: var(--sl-text-primary);
            text-transform: capitalize;
        }
        .cp-category-actions {
            padding: 8px;
        }

        /* Action Buttons */
        .cp-action {
            display: flex;
            align-items: center;
            gap: 12px;
            padding: 12px 14px;
            margin-bottom: 4px;
            background: transparent;
            border: 1px solid transparent;
            border-radius: 8px;
            cursor: pointer;
            width: 100%;
            text-align: left;
            transition: all 0.15s;
        }
        .cp-action:hover {
            background: var(--sl-bg-hover);
            border-color: var(--sl-border);
        }
        .cp-action:active {
            transform: scale(0.98);
        }
        .cp-action.running {
            background: rgba(184, 115, 51, 0.1);
            border-color: var(--sl-copper);
        }
        .cp-action.success {
            background: rgba(74, 173, 128, 0.1);
            border-color: #4ade80;
        }
        .cp-action.error {
            background: rgba(239, 68, 68, 0.1);
            border-color: #ef4444;
        }

        .cp-action-icon {
            width: 36px;
            height: 36px;
            background: var(--sl-bg-inset);
            border-radius: 8px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 1rem;
            flex-shrink: 0;
        }
        .cp-action.running .cp-action-icon {
            animation: pulse-icon 1s infinite;
        }
        @keyframes pulse-icon {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.5; }
        }

        .cp-action-info {
            flex: 1;
            min-width: 0;
        }
        .cp-action-label {
            font-size: 0.85rem;
            font-weight: 500;
            color: var(--sl-text-primary);
            margin-bottom: 2px;
        }
        .cp-action-desc {
            font-size: 0.7rem;
            color: var(--sl-text-secondary);
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }

        .cp-action-status {
            font-size: 0.7rem;
            color: var(--sl-text-disabled);
        }
        .cp-action.success .cp-action-status { color: #4ade80; }
        .cp-action.error .cp-action-status { color: #ef4444; }
        .cp-action.running .cp-action-status { color: var(--sl-copper); }

        /* Output Panel */
        .cp-output {
            position: fixed;
            bottom: 0;
            left: 0;
            right: 0;
            background: var(--sl-bg-surface);
            border-top: 1px solid var(--sl-border);
            transform: translateY(100%);
            transition: transform 0.3s;
            z-index: 2100;
        }
        .cp-output.active {
            transform: translateY(0);
        }
        .cp-output-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 12px 20px;
            background: var(--sl-bg-inset);
            border-bottom: 1px solid var(--sl-border);
        }
        .cp-output-title {
            font-size: 0.85rem;
            font-weight: 500;
            color: var(--sl-text-primary);
        }
        .cp-output-close {
            background: transparent;
            border: none;
            color: var(--sl-text-secondary);
            cursor: pointer;
            font-size: 1rem;
        }
        .cp-output-content {
            max-height: 300px;
            overflow-y: auto;
            padding: 16px 20px;
            font-family: var(--sl-font-mono);
            font-size: 0.75rem;
            color: var(--sl-text-secondary);
            white-space: pre-wrap;
            line-height: 1.5;
        }
        .cp-output-content .success { color: #4ade80; }
        .cp-output-content .error { color: #ef4444; }
        .cp-output-content .info { color: var(--sl-copper); }

        /* Control Panel FAB */
        .cp-fab {
            position: fixed;
            bottom: 24px;
            right: 24px;
            width: 56px;
            height: 56px;
            border-radius: 14px;
            background: linear-gradient(135deg, var(--sl-copper), #8B5A2B);
            border: none;
            cursor: pointer;
            box-shadow: 0 6px 20px rgba(184, 115, 51, 0.4);
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 1.4rem;
            color: white;
            transition: all 0.2s;
            z-index: 100;
        }
        .cp-fab:hover {
            transform: scale(1.08);
            box-shadow: 0 8px 28px rgba(184, 115, 51, 0.5);
        }
'''


def get_control_panel_html() -> str:
    """HTML for the control panel."""
    return '''
        <!-- Control Panel Overlay -->
        <div class="control-panel-overlay" id="control-panel-overlay">
            <div class="control-panel">
                <!-- Header -->
                <div class="cp-header">
                    <div class="cp-title">SLATE Control Panel</div>
                    <button class="cp-close" onclick="closeControlPanel()">Close Panel</button>
                </div>

                <!-- System Status -->
                <div class="cp-status-bar" id="cp-status-bar">
                    <div class="cp-status-item">
                        <div class="cp-status-dot" id="cp-status-dashboard"></div>
                        <span class="cp-status-label">Dashboard</span>
                    </div>
                    <div class="cp-status-item">
                        <div class="cp-status-dot" id="cp-status-runner"></div>
                        <span class="cp-status-label">Runner</span>
                    </div>
                    <div class="cp-status-item">
                        <div class="cp-status-dot" id="cp-status-ollama"></div>
                        <span class="cp-status-label">Ollama AI</span>
                    </div>
                    <div class="cp-status-item">
                        <span class="cp-status-label">Tasks:</span>
                        <span class="cp-status-value" id="cp-status-tasks">0</span>
                    </div>
                    <div class="cp-status-item">
                        <span class="cp-status-label">GPU:</span>
                        <span class="cp-status-value" id="cp-status-gpu">checking...</span>
                    </div>
                </div>

                <!-- Guided Sequences -->
                <div class="cp-sequences">
                    <div class="cp-section-title">Guided Workflows (Step-by-Step)</div>
                    <div class="cp-sequence-grid" id="cp-sequences">
                        <!-- Populated by JS -->
                    </div>
                </div>

                <!-- Active Sequence -->
                <div class="cp-active-sequence" id="cp-active-sequence">
                    <div class="cp-seq-header">
                        <div class="cp-seq-title" id="cp-seq-title">Running Sequence...</div>
                        <button class="cp-seq-cancel" onclick="cancelSequence()">Cancel</button>
                    </div>
                    <div class="cp-seq-progress">
                        <div class="cp-seq-progress-bar">
                            <div class="cp-seq-progress-fill" id="cp-seq-progress-fill" style="width: 0%"></div>
                        </div>
                        <span class="cp-seq-progress-text" id="cp-seq-progress-text">Step 0/0</span>
                    </div>
                    <div class="cp-seq-instruction" id="cp-seq-instruction">Preparing...</div>
                    <div class="cp-seq-buttons">
                        <button class="cp-seq-run" id="cp-seq-run" onclick="runSequenceStep()">Run This Step</button>
                        <button class="cp-seq-skip" onclick="skipSequenceStep()">Skip Step</button>
                    </div>
                </div>

                <!-- Action Categories -->
                <div class="cp-section-title">All Actions (Click to Run)</div>
                <div class="cp-categories" id="cp-categories">
                    <!-- Populated by JS -->
                </div>
            </div>
        </div>

        <!-- Output Panel -->
        <div class="cp-output" id="cp-output">
            <div class="cp-output-header">
                <span class="cp-output-title" id="cp-output-title">Output</span>
                <button class="cp-output-close" onclick="closeOutput()">&times;</button>
            </div>
            <div class="cp-output-content" id="cp-output-content">
                Waiting for output...
            </div>
        </div>

        <!-- Control Panel FAB -->
        <button class="cp-fab" onclick="openControlPanel()" title="Open Control Panel">
            &#9881;
        </button>
'''


def get_control_panel_js() -> str:
    """JavaScript for the control panel."""
    return '''
        // ═══════════════════════════════════════════════════════════════
        // SLATE Control Panel - Button-Driven UI
        // ═══════════════════════════════════════════════════════════════

        const controlPanel = {
            state: null,
            activeSequence: null,
            sequenceStep: 0,
            totalSteps: 0
        };

        const actionIcons = {
            pulse: '&#128147;',
            scan: '&#128302;',
            check: '&#10004;',
            flask: '&#128248;',
            sparkle: '&#10024;',
            shield: '&#128737;',
            brain: '&#129504;',
            document: '&#128196;',
            cpu: '&#128187;',
            list: '&#128203;',
            trash: '&#128465;',
            rocket: '&#128640;',
            play: '&#9654;',
            stop: '&#9632;',
            refresh: '&#128260;',
            merge: '&#128256;',
            bug: '&#128027;',
            workflow: '&#127380;',
            sync: '&#128260;'
        };

        function openControlPanel() {
            document.getElementById('control-panel-overlay').classList.add('active');
            loadPanelState();
        }

        function closeControlPanel() {
            document.getElementById('control-panel-overlay').classList.remove('active');
            closeOutput();
        }

        async function loadPanelState() {
            try {
                const res = await fetch('/api/control-panel/state');
                const data = await res.json();
                controlPanel.state = data;
                renderPanel(data);
            } catch (e) {
                console.error('Failed to load panel state:', e);
            }
        }

        function renderPanel(data) {
            // Update status bar
            updateStatusDot('cp-status-dashboard', data.system_status.dashboard);
            updateStatusDot('cp-status-runner', data.system_status.runner);
            updateStatusDot('cp-status-ollama', data.system_status.ollama);
            document.getElementById('cp-status-tasks').textContent = data.system_status.tasks_pending;
            document.getElementById('cp-status-gpu').textContent = data.system_status.gpu_available ? 'Available' : 'None';

            // Render sequences
            renderSequences(data.sequences);

            // Render categories
            renderCategories(data.categories);
        }

        function updateStatusDot(elementId, status) {
            const dot = document.getElementById(elementId);
            dot.className = 'cp-status-dot ' + (status === 'online' ? 'online' : status === 'offline' ? 'offline' : 'unknown');
        }

        function renderSequences(sequences) {
            const container = document.getElementById('cp-sequences');
            container.innerHTML = Object.values(sequences).map(seq => `
                <div class="cp-sequence-card" onclick="startSequence('${seq.id}')">
                    <div class="cp-sequence-name">${seq.name}</div>
                    <div class="cp-sequence-desc">${seq.description}</div>
                    <div class="cp-sequence-meta">${seq.step_count} steps - Click to start</div>
                </div>
            `).join('');
        }

        function renderCategories(categories) {
            const container = document.getElementById('cp-categories');
            container.innerHTML = Object.entries(categories).map(([cat, actions]) => `
                <div class="cp-category">
                    <div class="cp-category-header">${cat}</div>
                    <div class="cp-category-actions">
                        ${actions.map(action => `
                            <button class="cp-action" id="action-${action.id}" onclick="runAction('${action.id}')">
                                <div class="cp-action-icon">${actionIcons[action.icon] || '&#9654;'}</div>
                                <div class="cp-action-info">
                                    <div class="cp-action-label">${action.label}</div>
                                    <div class="cp-action-desc">${action.description}</div>
                                </div>
                                <div class="cp-action-status" id="status-${action.id}">Ready</div>
                            </button>
                        `).join('')}
                    </div>
                </div>
            `).join('');
        }

        async function runAction(actionId) {
            const btn = document.getElementById('action-' + actionId);
            const status = document.getElementById('status-' + actionId);

            // Update UI
            btn.className = 'cp-action running';
            status.textContent = 'Running...';
            showOutput('Running: ' + actionId, '');

            try {
                const res = await fetch('/api/control-panel/execute/' + actionId, { method: 'POST' });
                const data = await res.json();

                if (data.success) {
                    btn.className = 'cp-action success';
                    status.textContent = 'Done';
                    showOutput(data.label + ' - Success', '<span class="success">SUCCESS</span>\\n\\n' + (data.output || 'Completed'));
                } else {
                    btn.className = 'cp-action error';
                    status.textContent = 'Failed';
                    showOutput(data.label + ' - Error', '<span class="error">ERROR</span>\\n\\n' + (data.error || 'Failed'));
                }

                // Reset after 3 seconds
                setTimeout(() => {
                    btn.className = 'cp-action';
                    status.textContent = 'Ready';
                }, 3000);

            } catch (e) {
                btn.className = 'cp-action error';
                status.textContent = 'Error';
                showOutput('Error', '<span class="error">' + e.message + '</span>');
            }
        }

        async function startSequence(sequenceId) {
            try {
                const res = await fetch('/api/control-panel/sequence/start/' + sequenceId, { method: 'POST' });
                const data = await res.json();

                if (data.success) {
                    controlPanel.activeSequence = sequenceId;
                    controlPanel.sequenceStep = 0;
                    controlPanel.totalSteps = data.total_steps;

                    document.getElementById('cp-active-sequence').classList.add('active');
                    document.getElementById('cp-seq-title').textContent = data.sequence_name;
                    updateSequenceUI(data);
                }
            } catch (e) {
                console.error('Failed to start sequence:', e);
            }
        }

        function updateSequenceUI(data) {
            const progress = ((data.current_step) / controlPanel.totalSteps) * 100;
            document.getElementById('cp-seq-progress-fill').style.width = progress + '%';
            document.getElementById('cp-seq-progress-text').textContent =
                'Step ' + (data.current_step + 1) + '/' + controlPanel.totalSteps;
            document.getElementById('cp-seq-instruction').textContent = data.instruction;
            document.getElementById('cp-seq-run').disabled = false;
            document.getElementById('cp-seq-run').textContent = 'Run: ' + data.action.label;
        }

        async function runSequenceStep() {
            const btn = document.getElementById('cp-seq-run');
            btn.disabled = true;
            btn.textContent = 'Running...';
            btn.className = 'cp-seq-run running';

            try {
                const res = await fetch('/api/control-panel/sequence/execute', { method: 'POST' });
                const data = await res.json();

                // Show output
                if (data.step_result) {
                    const result = data.step_result;
                    if (result.success) {
                        showOutput(result.label + ' - Success', '<span class="success">SUCCESS</span>\\n\\n' + (result.output || ''));
                    } else {
                        showOutput(result.label + ' - Error', '<span class="error">ERROR</span>\\n\\n' + (result.error || ''));
                    }
                }

                // Advance to next step
                const advRes = await fetch('/api/control-panel/sequence/advance', { method: 'POST' });
                const advData = await advRes.json();

                if (advData.complete) {
                    document.getElementById('cp-active-sequence').classList.remove('active');
                    controlPanel.activeSequence = null;
                    showOutput('Sequence Complete', '<span class="success">' + advData.message + '</span>');
                } else {
                    updateSequenceUI(advData);
                }

                btn.className = 'cp-seq-run';

            } catch (e) {
                btn.disabled = false;
                btn.textContent = 'Retry Step';
                btn.className = 'cp-seq-run';
                showOutput('Error', '<span class="error">' + e.message + '</span>');
            }
        }

        async function skipSequenceStep() {
            try {
                const res = await fetch('/api/control-panel/sequence/advance', { method: 'POST' });
                const data = await res.json();

                if (data.complete) {
                    document.getElementById('cp-active-sequence').classList.remove('active');
                    controlPanel.activeSequence = null;
                } else {
                    updateSequenceUI(data);
                }
            } catch (e) {
                console.error('Failed to skip step:', e);
            }
        }

        async function cancelSequence() {
            try {
                await fetch('/api/control-panel/sequence/cancel', { method: 'POST' });
                document.getElementById('cp-active-sequence').classList.remove('active');
                controlPanel.activeSequence = null;
            } catch (e) {
                console.error('Failed to cancel sequence:', e);
            }
        }

        function showOutput(title, content) {
            document.getElementById('cp-output-title').textContent = title;
            document.getElementById('cp-output-content').innerHTML = content;
            document.getElementById('cp-output').classList.add('active');
        }

        function closeOutput() {
            document.getElementById('cp-output').classList.remove('active');
        }

        // Keyboard shortcuts
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') {
                if (document.getElementById('cp-output').classList.contains('active')) {
                    closeOutput();
                } else if (document.getElementById('control-panel-overlay').classList.contains('active')) {
                    closeControlPanel();
                }
            }
        });
'''


def get_complete_control_panel() -> str:
    """Return the complete control panel component."""
    return f'''
        <!-- Control Panel Styles -->
        <style>
{get_control_panel_css()}
        </style>

        {get_control_panel_html()}

        <script>
{get_control_panel_js()}
        </script>
'''
