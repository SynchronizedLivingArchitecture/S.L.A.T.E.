#!/usr/bin/env python3
"""
SLATE Interactive Experience UI
================================

Game-like frontend interface for the choose-your-own-adventure
development experience. Features:

- Narrative dialogue area with typewriter effect
- Expandable option cards with previews
- AI companion with personality
- Visual navigation breadcrumb
- Risk/reversibility indicators
- "Learn more" expandable details
- Consequence previews before actions
"""


def get_interactive_experience_css() -> str:
    """Return CSS for the interactive experience UI."""
    return '''
        /* ═══════════════════════════════════════════════════════════════
           Interactive Experience Styles
           Game-like UI for development adventure
           ═══════════════════════════════════════════════════════════════ */

        /* Main Experience Container */
        .experience-overlay {
            position: fixed;
            inset: 0;
            background: rgba(0, 0, 0, 0.95);
            z-index: 2000;
            display: none;
            opacity: 0;
            transition: opacity 0.4s ease;
        }
        .experience-overlay.active {
            display: flex;
            opacity: 1;
        }

        .experience-container {
            width: 100%;
            height: 100%;
            display: grid;
            grid-template-columns: 280px 1fr 300px;
            grid-template-rows: auto 1fr auto;
            gap: 0;
            background: linear-gradient(135deg, #0a0908 0%, #1a1614 50%, #0a0908 100%);
        }

        /* ─── Header Bar ──────────────────────────────────────────────── */
        .exp-header {
            grid-column: 1 / -1;
            padding: 16px 24px;
            background: linear-gradient(180deg, rgba(184, 115, 51, 0.1) 0%, transparent 100%);
            border-bottom: 1px solid rgba(184, 115, 51, 0.2);
            display: flex;
            justify-content: space-between;
            align-items: center;
        }

        .exp-title {
            display: flex;
            align-items: center;
            gap: 12px;
        }
        .exp-title h1 {
            font-size: 1.3rem;
            font-weight: 600;
            color: var(--sl-text-primary);
            letter-spacing: 0.05em;
        }
        .exp-title .subtitle {
            font-size: 0.75rem;
            color: var(--sl-copper);
            text-transform: uppercase;
            letter-spacing: 0.1em;
        }

        .exp-close {
            background: transparent;
            border: 1px solid var(--sl-border);
            color: var(--sl-text-secondary);
            padding: 8px 16px;
            border-radius: 4px;
            cursor: pointer;
            font-size: 0.8rem;
            transition: all 0.2s;
        }
        .exp-close:hover {
            background: var(--sl-bg-hover);
            color: var(--sl-text-primary);
            border-color: var(--sl-copper);
        }

        /* ─── Navigation Sidebar ──────────────────────────────────────── */
        .exp-sidebar {
            background: rgba(0, 0, 0, 0.3);
            border-right: 1px solid var(--sl-border);
            padding: 20px 16px;
            overflow-y: auto;
        }

        .exp-breadcrumb {
            margin-bottom: 24px;
        }
        .breadcrumb-title {
            font-size: 0.65rem;
            color: var(--sl-text-disabled);
            text-transform: uppercase;
            letter-spacing: 0.1em;
            margin-bottom: 8px;
        }
        .breadcrumb-trail {
            display: flex;
            flex-direction: column;
            gap: 4px;
        }
        .breadcrumb-item {
            display: flex;
            align-items: center;
            gap: 8px;
            padding: 6px 10px;
            background: transparent;
            border: none;
            color: var(--sl-text-secondary);
            font-size: 0.75rem;
            cursor: pointer;
            border-radius: 4px;
            transition: all 0.2s;
            text-align: left;
        }
        .breadcrumb-item:hover {
            background: var(--sl-bg-hover);
            color: var(--sl-text-primary);
        }
        .breadcrumb-item.current {
            background: rgba(184, 115, 51, 0.15);
            color: var(--sl-copper);
        }
        .breadcrumb-item::before {
            content: '';
            width: 6px;
            height: 6px;
            background: var(--sl-border);
            border-radius: 50%;
        }
        .breadcrumb-item.current::before {
            background: var(--sl-copper);
        }

        .exp-zones {
            margin-top: 24px;
        }
        .zones-title {
            font-size: 0.65rem;
            color: var(--sl-text-disabled);
            text-transform: uppercase;
            letter-spacing: 0.1em;
            margin-bottom: 12px;
        }
        .zone-item {
            display: flex;
            align-items: center;
            gap: 10px;
            padding: 10px 12px;
            margin-bottom: 4px;
            background: transparent;
            border: 1px solid transparent;
            border-radius: 6px;
            cursor: pointer;
            transition: all 0.2s;
        }
        .zone-item:hover {
            background: var(--sl-bg-hover);
            border-color: var(--sl-border);
        }
        .zone-item.active {
            background: rgba(184, 115, 51, 0.1);
            border-color: var(--sl-copper);
        }
        .zone-icon {
            width: 32px;
            height: 32px;
            border-radius: 8px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 1rem;
        }
        .zone-info {
            flex: 1;
        }
        .zone-name {
            font-size: 0.8rem;
            color: var(--sl-text-primary);
            font-weight: 500;
        }
        .zone-status {
            font-size: 0.65rem;
            color: var(--sl-text-disabled);
        }

        /* ─── Main Content Area ───────────────────────────────────────── */
        .exp-main {
            padding: 32px 40px;
            overflow-y: auto;
            display: flex;
            flex-direction: column;
        }

        /* Narrative Section */
        .exp-narrative {
            margin-bottom: 32px;
        }
        .narrative-title {
            font-size: 1.5rem;
            font-weight: 600;
            color: var(--sl-text-primary);
            margin-bottom: 16px;
            display: flex;
            align-items: center;
            gap: 12px;
        }
        .narrative-title::before {
            content: '';
            width: 4px;
            height: 28px;
            background: var(--sl-copper);
            border-radius: 2px;
        }
        .narrative-text {
            font-size: 1rem;
            color: var(--sl-text-secondary);
            line-height: 1.8;
            max-width: 700px;
            font-style: italic;
        }
        .narrative-text.typing::after {
            content: '|';
            animation: blink 0.7s infinite;
        }
        @keyframes blink {
            0%, 100% { opacity: 1; }
            50% { opacity: 0; }
        }

        /* Options Grid */
        .exp-options {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
            gap: 16px;
            margin-top: auto;
        }

        .option-card {
            background: var(--sl-bg-surface);
            border: 1px solid var(--sl-border);
            border-radius: 12px;
            padding: 20px;
            cursor: pointer;
            transition: all 0.3s ease;
            position: relative;
            overflow: hidden;
        }
        .option-card::before {
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            width: 100%;
            height: 3px;
            background: var(--sl-border);
            transition: background 0.3s;
        }
        .option-card:hover {
            border-color: var(--sl-copper);
            transform: translateY(-4px);
            box-shadow: 0 12px 24px rgba(0, 0, 0, 0.3);
        }
        .option-card:hover::before {
            background: var(--sl-copper);
        }

        .option-card.risk-1::before { background: var(--sl-warning); }
        .option-card.risk-2::before { background: var(--sl-warning); }
        .option-card.risk-3::before { background: var(--sl-error); }

        .option-header {
            display: flex;
            align-items: flex-start;
            gap: 12px;
            margin-bottom: 12px;
        }
        .option-icon {
            width: 40px;
            height: 40px;
            background: var(--sl-bg-inset);
            border-radius: 10px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 1.2rem;
            flex-shrink: 0;
        }
        .option-title-area {
            flex: 1;
        }
        .option-label {
            font-size: 0.95rem;
            font-weight: 600;
            color: var(--sl-text-primary);
            margin-bottom: 4px;
        }
        .option-desc {
            font-size: 0.8rem;
            color: var(--sl-text-secondary);
            line-height: 1.4;
        }

        .option-meta {
            display: flex;
            align-items: center;
            gap: 8px;
            margin-top: 12px;
            flex-wrap: wrap;
        }
        .option-badge {
            font-size: 0.65rem;
            padding: 3px 8px;
            border-radius: 4px;
            background: var(--sl-bg-inset);
            color: var(--sl-text-disabled);
        }
        .option-badge.time {
            background: rgba(8, 145, 178, 0.15);
            color: #0891b2;
        }
        .option-badge.risk {
            background: rgba(245, 158, 11, 0.15);
            color: #f59e0b;
        }
        .option-badge.safe {
            background: rgba(74, 124, 89, 0.15);
            color: #4a7c59;
        }
        .option-badge.ai {
            background: linear-gradient(135deg, rgba(124, 58, 237, 0.2), rgba(79, 70, 229, 0.2));
            color: #a78bfa;
        }

        .option-preview {
            margin-top: 12px;
            padding-top: 12px;
            border-top: 1px solid var(--sl-border);
            font-size: 0.75rem;
            color: var(--sl-text-disabled);
            display: none;
        }
        .option-card:hover .option-preview {
            display: block;
        }

        .option-expand {
            position: absolute;
            bottom: 8px;
            right: 8px;
            background: transparent;
            border: none;
            color: var(--sl-text-disabled);
            padding: 4px 8px;
            font-size: 0.7rem;
            cursor: pointer;
            border-radius: 4px;
            transition: all 0.2s;
        }
        .option-expand:hover {
            background: var(--sl-bg-hover);
            color: var(--sl-copper);
        }

        /* ─── Companion Panel ─────────────────────────────────────────── */
        .exp-companion {
            background: rgba(0, 0, 0, 0.3);
            border-left: 1px solid var(--sl-border);
            padding: 20px 16px;
            display: flex;
            flex-direction: column;
        }

        .companion-header {
            text-align: center;
            margin-bottom: 20px;
        }
        .companion-avatar {
            width: 80px;
            height: 80px;
            margin: 0 auto 12px;
            background: linear-gradient(135deg, var(--sl-copper), #8B5A2B);
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 2rem;
            box-shadow: 0 0 30px rgba(184, 115, 51, 0.3);
            animation: companion-pulse 3s ease-in-out infinite;
        }
        @keyframes companion-pulse {
            0%, 100% { box-shadow: 0 0 30px rgba(184, 115, 51, 0.3); }
            50% { box-shadow: 0 0 50px rgba(184, 115, 51, 0.5); }
        }
        .companion-name {
            font-size: 0.9rem;
            font-weight: 600;
            color: var(--sl-text-primary);
        }
        .companion-title {
            font-size: 0.7rem;
            color: var(--sl-copper);
        }

        .companion-dialogue {
            flex: 1;
            overflow-y: auto;
        }
        .dialogue-bubble {
            background: var(--sl-bg-surface);
            border: 1px solid var(--sl-border);
            border-radius: 12px;
            padding: 14px 16px;
            margin-bottom: 12px;
            position: relative;
        }
        .dialogue-bubble::before {
            content: '';
            position: absolute;
            top: -8px;
            left: 20px;
            width: 16px;
            height: 16px;
            background: var(--sl-bg-surface);
            border: 1px solid var(--sl-border);
            border-bottom: none;
            border-right: none;
            transform: rotate(45deg);
        }
        .dialogue-text {
            font-size: 0.85rem;
            color: var(--sl-text-secondary);
            line-height: 1.6;
        }
        .dialogue-text strong {
            color: var(--sl-copper);
        }

        .companion-input {
            margin-top: auto;
        }
        .companion-input input {
            width: 100%;
            background: var(--sl-bg-inset);
            border: 1px solid var(--sl-border);
            border-radius: 8px;
            padding: 12px 14px;
            color: var(--sl-text-primary);
            font-size: 0.85rem;
        }
        .companion-input input::placeholder {
            color: var(--sl-text-disabled);
        }
        .companion-input input:focus {
            outline: none;
            border-color: var(--sl-copper);
        }

        /* ─── Action Confirmation Modal ───────────────────────────────── */
        .action-confirm-modal {
            position: fixed;
            inset: 0;
            background: rgba(0, 0, 0, 0.8);
            display: none;
            justify-content: center;
            align-items: center;
            z-index: 3000;
        }
        .action-confirm-modal.active {
            display: flex;
        }
        .action-confirm-content {
            background: var(--sl-bg-surface);
            border: 1px solid var(--sl-border);
            border-radius: 16px;
            padding: 32px;
            max-width: 500px;
            width: 90%;
        }
        .action-confirm-header {
            display: flex;
            align-items: center;
            gap: 16px;
            margin-bottom: 20px;
        }
        .action-confirm-icon {
            width: 56px;
            height: 56px;
            background: linear-gradient(135deg, var(--sl-copper), #8B5A2B);
            border-radius: 12px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 1.5rem;
        }
        .action-confirm-title {
            font-size: 1.2rem;
            font-weight: 600;
            color: var(--sl-text-primary);
        }
        .action-confirm-subtitle {
            font-size: 0.8rem;
            color: var(--sl-text-secondary);
        }

        .action-confirm-body {
            margin-bottom: 24px;
        }
        .action-preview-box {
            background: var(--sl-bg-inset);
            border: 1px solid var(--sl-border);
            border-radius: 8px;
            padding: 16px;
            margin-bottom: 16px;
        }
        .action-preview-label {
            font-size: 0.7rem;
            color: var(--sl-text-disabled);
            text-transform: uppercase;
            letter-spacing: 0.05em;
            margin-bottom: 8px;
        }
        .action-preview-text {
            font-size: 0.85rem;
            color: var(--sl-text-secondary);
            line-height: 1.5;
        }

        .action-warnings {
            display: flex;
            gap: 8px;
            flex-wrap: wrap;
        }
        .action-warning-badge {
            font-size: 0.7rem;
            padding: 4px 10px;
            border-radius: 4px;
        }
        .action-warning-badge.safe {
            background: rgba(74, 124, 89, 0.15);
            color: #4a7c59;
        }
        .action-warning-badge.caution {
            background: rgba(245, 158, 11, 0.15);
            color: #f59e0b;
        }

        .action-confirm-buttons {
            display: flex;
            gap: 12px;
            justify-content: flex-end;
        }
        .action-btn {
            padding: 12px 24px;
            border-radius: 8px;
            font-size: 0.85rem;
            font-weight: 500;
            cursor: pointer;
            transition: all 0.2s;
        }
        .action-btn-cancel {
            background: transparent;
            border: 1px solid var(--sl-border);
            color: var(--sl-text-secondary);
        }
        .action-btn-cancel:hover {
            background: var(--sl-bg-hover);
            color: var(--sl-text-primary);
        }
        .action-btn-confirm {
            background: var(--sl-copper);
            border: 1px solid var(--sl-copper);
            color: white;
        }
        .action-btn-confirm:hover {
            background: var(--sl-copper-dark);
        }

        /* ─── Learn More Modal ────────────────────────────────────────── */
        .learn-more-panel {
            position: fixed;
            top: 0;
            right: -400px;
            width: 400px;
            height: 100%;
            background: var(--sl-bg-surface);
            border-left: 1px solid var(--sl-border);
            z-index: 2500;
            transition: right 0.3s ease;
            display: flex;
            flex-direction: column;
        }
        .learn-more-panel.active {
            right: 0;
        }
        .learn-more-header {
            padding: 20px 24px;
            border-bottom: 1px solid var(--sl-border);
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        .learn-more-title {
            font-size: 1rem;
            font-weight: 600;
            color: var(--sl-text-primary);
        }
        .learn-more-close {
            background: transparent;
            border: none;
            color: var(--sl-text-secondary);
            cursor: pointer;
            font-size: 1.2rem;
        }
        .learn-more-content {
            flex: 1;
            padding: 24px;
            overflow-y: auto;
        }
        .learn-more-section {
            margin-bottom: 24px;
        }
        .learn-more-section-title {
            font-size: 0.7rem;
            color: var(--sl-text-disabled);
            text-transform: uppercase;
            letter-spacing: 0.05em;
            margin-bottom: 8px;
        }
        .learn-more-section-text {
            font-size: 0.9rem;
            color: var(--sl-text-secondary);
            line-height: 1.7;
        }
        .learn-more-ai-hint {
            background: linear-gradient(135deg, rgba(124, 58, 237, 0.1), rgba(79, 70, 229, 0.1));
            border: 1px solid rgba(124, 58, 237, 0.2);
            border-radius: 8px;
            padding: 12px 16px;
            margin-top: 16px;
        }
        .learn-more-ai-hint-title {
            font-size: 0.75rem;
            color: #a78bfa;
            font-weight: 500;
            margin-bottom: 4px;
        }
        .learn-more-ai-hint-text {
            font-size: 0.8rem;
            color: var(--sl-text-secondary);
        }

        /* ─── Footer Status Bar ───────────────────────────────────────── */
        .exp-footer {
            grid-column: 1 / -1;
            padding: 12px 24px;
            background: var(--sl-bg-inset);
            border-top: 1px solid var(--sl-border);
            display: flex;
            justify-content: space-between;
            align-items: center;
            font-size: 0.75rem;
            color: var(--sl-text-disabled);
        }
        .exp-stats {
            display: flex;
            gap: 24px;
        }
        .exp-stat {
            display: flex;
            align-items: center;
            gap: 6px;
        }
        .exp-stat-value {
            color: var(--sl-text-secondary);
            font-weight: 500;
        }

        /* ─── Experience FAB ──────────────────────────────────────────── */
        .experience-fab {
            position: fixed;
            bottom: 24px;
            right: 24px;
            width: 64px;
            height: 64px;
            border-radius: 16px;
            background: linear-gradient(135deg, var(--sl-copper), #8B5A2B);
            border: none;
            cursor: pointer;
            box-shadow: 0 8px 24px rgba(184, 115, 51, 0.4);
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            gap: 2px;
            transition: all 0.3s;
            z-index: 100;
        }
        .experience-fab:hover {
            transform: scale(1.08);
            box-shadow: 0 12px 32px rgba(184, 115, 51, 0.5);
        }
        .experience-fab-icon {
            font-size: 1.5rem;
        }
        .experience-fab-text {
            font-size: 0.55rem;
            color: rgba(255,255,255,0.9);
            text-transform: uppercase;
            letter-spacing: 0.05em;
        }
'''


def get_interactive_experience_html() -> str:
    """Return HTML for the interactive experience UI."""
    return '''
        <!-- Interactive Experience Overlay -->
        <div class="experience-overlay" id="experience-overlay">
            <div class="experience-container">
                <!-- Header -->
                <div class="exp-header">
                    <div class="exp-title">
                        <h1>S.L.A.T.E.</h1>
                        <span class="subtitle">Interactive Command</span>
                    </div>
                    <button class="exp-close" onclick="closeExperience()">Exit Experience</button>
                </div>

                <!-- Navigation Sidebar -->
                <div class="exp-sidebar">
                    <div class="exp-breadcrumb">
                        <div class="breadcrumb-title">Navigation</div>
                        <div class="breadcrumb-trail" id="exp-breadcrumb">
                            <!-- Populated by JS -->
                        </div>
                    </div>

                    <div class="exp-zones">
                        <div class="zones-title">Development Zones</div>
                        <div id="exp-zones-list">
                            <!-- Populated by JS -->
                        </div>
                    </div>
                </div>

                <!-- Main Content -->
                <div class="exp-main">
                    <div class="exp-narrative">
                        <h2 class="narrative-title" id="exp-title">Loading...</h2>
                        <p class="narrative-text" id="exp-narrative">...</p>
                    </div>

                    <div class="exp-options" id="exp-options">
                        <!-- Option cards populated by JS -->
                    </div>
                </div>

                <!-- Companion Panel -->
                <div class="exp-companion">
                    <div class="companion-header">
                        <div class="companion-avatar">&#129302;</div>
                        <div class="companion-name">SLATE</div>
                        <div class="companion-title">AI Companion</div>
                    </div>

                    <div class="companion-dialogue" id="companion-dialogue">
                        <div class="dialogue-bubble">
                            <p class="dialogue-text" id="companion-text">
                                Welcome, developer. I'm here to guide you through your project.
                                What would you like to explore?
                            </p>
                        </div>
                    </div>

                    <div class="companion-input">
                        <input type="text" id="companion-question" placeholder="Ask me anything..."
                               onkeypress="if(event.key==='Enter')askCompanion()">
                    </div>
                </div>

                <!-- Footer -->
                <div class="exp-footer">
                    <div class="exp-stats">
                        <div class="exp-stat">
                            <span>Explored:</span>
                            <span class="exp-stat-value" id="exp-visited">0</span> / <span id="exp-total">0</span>
                        </div>
                        <div class="exp-stat">
                            <span>Actions:</span>
                            <span class="exp-stat-value" id="exp-actions">0</span>
                        </div>
                        <div class="exp-stat">
                            <span>Session:</span>
                            <span class="exp-stat-value" id="exp-duration">0:00</span>
                        </div>
                    </div>
                    <div>
                        Press <kbd>?</kbd> for help | <kbd>Esc</kbd> to close
                    </div>
                </div>
            </div>
        </div>

        <!-- Action Confirmation Modal -->
        <div class="action-confirm-modal" id="action-confirm-modal">
            <div class="action-confirm-content">
                <div class="action-confirm-header">
                    <div class="action-confirm-icon" id="action-confirm-icon">&#9889;</div>
                    <div>
                        <div class="action-confirm-title" id="action-confirm-title">Confirm Action</div>
                        <div class="action-confirm-subtitle" id="action-confirm-subtitle">This will execute the selected operation</div>
                    </div>
                </div>

                <div class="action-confirm-body">
                    <div class="action-preview-box">
                        <div class="action-preview-label">What will happen</div>
                        <div class="action-preview-text" id="action-confirm-preview">...</div>
                    </div>

                    <div class="action-warnings" id="action-confirm-warnings">
                        <!-- Populated by JS -->
                    </div>
                </div>

                <div class="action-confirm-buttons">
                    <button class="action-btn action-btn-cancel" onclick="cancelAction()">Go Back</button>
                    <button class="action-btn action-btn-confirm" id="action-confirm-btn" onclick="confirmAction()">Proceed</button>
                </div>
            </div>
        </div>

        <!-- Learn More Panel -->
        <div class="learn-more-panel" id="learn-more-panel">
            <div class="learn-more-header">
                <span class="learn-more-title" id="learn-more-title">Learn More</span>
                <button class="learn-more-close" onclick="closeLearnMore()">&times;</button>
            </div>
            <div class="learn-more-content" id="learn-more-content">
                <!-- Populated by JS -->
            </div>
        </div>

        <!-- Experience FAB -->
        <button class="experience-fab" onclick="openExperience()" title="Open Interactive Experience">
            <span class="experience-fab-icon">&#9733;</span>
            <span class="experience-fab-text">Explore</span>
        </button>
'''


def get_interactive_experience_js() -> str:
    """Return JavaScript for the interactive experience."""
    return '''
        // ═══════════════════════════════════════════════════════════════
        // SLATE Interactive Experience Engine
        // ═══════════════════════════════════════════════════════════════

        const experience = {
            active: false,
            currentNode: null,
            pendingAction: null,
            sessionStart: null,
            durationInterval: null
        };

        const zoneIcons = {
            control_center: '&#9881;',
            code_forge: '&#128296;',
            ai_nexus: '&#129504;',
            deployment_dock: '&#128640;',
            knowledge_archive: '&#128218;',
            collaboration_hub: '&#129309;'
        };

        const optionIcons = {
            radar: '&#128225;',
            anvil: '&#128296;',
            brain: '&#129504;',
            rocket: '&#128640;',
            book: '&#128218;',
            people: '&#129309;',
            lightning: '&#9889;',
            home: '&#127968;',
            flame: '&#128293;',
            sparkle: '&#10024;',
            shield: '&#128737;',
            magnify: '&#128269;',
            eye: '&#128065;',
            document: '&#128196;',
            chat: '&#128172;',
            cpu: '&#128187;',
            container: '&#128230;',
            gear: '&#9881;',
            tree: '&#127794;',
            search: '&#128270;',
            merge: '&#128256;',
            bug: '&#128027;',
            workflow: '&#127380;',
            sync: '&#128260;',
            heart: '&#128151;',
            play: '&#9654;',
            check: '&#10004;',
            map: '&#128506;',
            server: '&#128187;',
            gauge: '&#128200;',
            list: '&#128203;',
            scan: '&#128302;'
        };

        function openExperience() {
            document.getElementById('experience-overlay').classList.add('active');
            experience.active = true;
            experience.sessionStart = Date.now();
            startDurationTimer();
            loadExperienceStatus();
        }

        function closeExperience() {
            document.getElementById('experience-overlay').classList.remove('active');
            experience.active = false;
            stopDurationTimer();
        }

        function startDurationTimer() {
            experience.durationInterval = setInterval(() => {
                const elapsed = Math.floor((Date.now() - experience.sessionStart) / 1000);
                const mins = Math.floor(elapsed / 60);
                const secs = elapsed % 60;
                document.getElementById('exp-duration').textContent =
                    mins + ':' + secs.toString().padStart(2, '0');
            }, 1000);
        }

        function stopDurationTimer() {
            if (experience.durationInterval) {
                clearInterval(experience.durationInterval);
            }
        }

        async function loadExperienceStatus() {
            try {
                const res = await fetch('/api/experience/status');
                const data = await res.json();

                experience.currentNode = data.current_node;
                renderExperience(data);
            } catch (e) {
                console.error('Failed to load experience:', e);
            }
        }

        function renderExperience(data) {
            const node = data.current_node;

            // Update title and narrative
            document.getElementById('exp-title').textContent = node.title;
            typeWriter(document.getElementById('exp-narrative'), node.narrative);

            // Update breadcrumb
            renderBreadcrumb(data.breadcrumb);

            // Update zones
            renderZones(data.zones);

            // Update options
            renderOptions(node.options);

            // Update stats
            document.getElementById('exp-visited').textContent = data.visited_count;
            document.getElementById('exp-total').textContent = data.total_nodes;
            document.getElementById('exp-actions').textContent = data.action_count;
        }

        function typeWriter(element, text, speed = 20) {
            element.textContent = '';
            element.classList.add('typing');
            let i = 0;

            function type() {
                if (i < text.length) {
                    element.textContent += text.charAt(i);
                    i++;
                    setTimeout(type, speed);
                } else {
                    element.classList.remove('typing');
                }
            }
            type();
        }

        function renderBreadcrumb(breadcrumb) {
            const container = document.getElementById('exp-breadcrumb');
            container.innerHTML = breadcrumb.map((item, idx) => {
                const isCurrent = idx === breadcrumb.length - 1;
                return `<button class="breadcrumb-item ${isCurrent ? 'current' : ''}"
                                onclick="navigateTo('${item.id}')">${item.title}</button>`;
            }).join('');
        }

        function renderZones(zones) {
            const container = document.getElementById('exp-zones-list');
            container.innerHTML = Object.entries(zones).map(([id, zone]) => {
                const icon = zoneIcons[id] || '&#9673;';
                return `<div class="zone-item" onclick="navigateToZone('${id}')">
                    <div class="zone-icon" style="background: ${zone.color}20; color: ${zone.color}">${icon}</div>
                    <div class="zone-info">
                        <div class="zone-name">${zone.name}</div>
                        <div class="zone-status">${zone.health || 'Ready'}</div>
                    </div>
                </div>`;
            }).join('');
        }

        function renderOptions(options) {
            const container = document.getElementById('exp-options');
            container.innerHTML = options.map(opt => {
                const icon = optionIcons[opt.icon] || '&#9654;';
                const riskClass = opt.risk_level > 0 ? `risk-${opt.risk_level}` : '';

                let badges = '';
                if (opt.estimated_time) {
                    badges += `<span class="option-badge time">${opt.estimated_time}</span>`;
                }
                if (opt.risk_level === 0) {
                    badges += `<span class="option-badge safe">Safe</span>`;
                } else if (opt.risk_level > 0) {
                    badges += `<span class="option-badge risk">Caution</span>`;
                }
                if (opt.has_action && opt.label.toLowerCase().includes('ai')) {
                    badges += `<span class="option-badge ai">AI</span>`;
                }

                return `<div class="option-card ${riskClass}" onclick="selectOption('${opt.id}')">
                    <div class="option-header">
                        <div class="option-icon">${icon}</div>
                        <div class="option-title-area">
                            <div class="option-label">${opt.label}</div>
                            <div class="option-desc">${opt.description}</div>
                        </div>
                    </div>
                    <div class="option-meta">${badges}</div>
                    ${opt.preview ? `<div class="option-preview">${opt.preview}</div>` : ''}
                    ${opt.has_learn_more ? `<button class="option-expand" onclick="event.stopPropagation(); showLearnMore('${opt.id}')">Learn more</button>` : ''}
                </div>`;
            }).join('');
        }

        async function selectOption(optionId) {
            try {
                const res = await fetch('/api/experience/select/' + optionId, { method: 'POST' });
                const data = await res.json();

                if (data.type === 'action_confirmation') {
                    showActionConfirm(data);
                } else if (data.success) {
                    if (data.companion_dialogue) {
                        updateCompanion(data.companion_dialogue);
                    }
                    loadExperienceStatus();
                }
            } catch (e) {
                console.error('Failed to select option:', e);
            }
        }

        async function navigateTo(nodeId) {
            try {
                const res = await fetch('/api/experience/navigate/' + nodeId, { method: 'POST' });
                const data = await res.json();

                if (data.success) {
                    if (data.companion_dialogue) {
                        updateCompanion(data.companion_dialogue);
                    }
                    loadExperienceStatus();
                }
            } catch (e) {
                console.error('Failed to navigate:', e);
            }
        }

        function navigateToZone(zoneId) {
            const zoneNodeMap = {
                control_center: 'main_hub',
                code_forge: 'code_forge_hub',
                ai_nexus: 'ai_nexus_hub',
                deployment_dock: 'deployment_hub',
                knowledge_archive: 'archive_hub',
                collaboration_hub: 'collaboration_hub'
            };
            const nodeId = zoneNodeMap[zoneId] || 'main_hub';
            navigateTo(nodeId);
        }

        function showActionConfirm(data) {
            experience.pendingAction = data.action;

            document.getElementById('action-confirm-title').textContent = data.action.label;
            document.getElementById('action-confirm-subtitle').textContent = data.action.description;
            document.getElementById('action-confirm-preview').textContent = data.action.preview || 'Execute the selected action';

            // Build warnings
            const warnings = document.getElementById('action-confirm-warnings');
            let warningsHtml = '';
            if (data.action.reversible) {
                warningsHtml += '<span class="action-warning-badge safe">Reversible</span>';
            }
            if (data.action.risk_level === 0) {
                warningsHtml += '<span class="action-warning-badge safe">No Risk</span>';
            } else {
                warningsHtml += '<span class="action-warning-badge caution">May affect system</span>';
            }
            if (data.action.estimated_time) {
                warningsHtml += `<span class="action-warning-badge safe">${data.action.estimated_time}</span>`;
            }
            warnings.innerHTML = warningsHtml;

            document.getElementById('action-confirm-modal').classList.add('active');

            if (data.companion_dialogue) {
                updateCompanion(data.companion_dialogue);
            }
        }

        function cancelAction() {
            experience.pendingAction = null;
            document.getElementById('action-confirm-modal').classList.remove('active');
        }

        async function confirmAction() {
            if (!experience.pendingAction) return;

            const actionId = experience.pendingAction.id;
            document.getElementById('action-confirm-modal').classList.remove('active');

            // Show loading state
            updateCompanion('Executing action... Please wait.');

            try {
                const res = await fetch('/api/experience/execute/' + actionId, { method: 'POST' });
                const data = await res.json();

                if (data.companion_dialogue) {
                    updateCompanion(data.companion_dialogue);
                }

                if (data.success) {
                    addDialogueBubble('Action completed successfully!', 'success');
                    if (data.output) {
                        addDialogueBubble(data.output.substring(0, 300), 'output');
                    }
                } else {
                    addDialogueBubble('Something went wrong: ' + (data.error || 'Unknown error'), 'error');
                }

                loadExperienceStatus();
            } catch (e) {
                addDialogueBubble('Failed to execute action: ' + e.message, 'error');
            }

            experience.pendingAction = null;
        }

        async function showLearnMore(optionId) {
            try {
                const res = await fetch('/api/experience/learn-more/' + optionId);
                const data = await res.json();

                if (data.success) {
                    document.getElementById('learn-more-title').textContent = data.label;

                    let content = `
                        <div class="learn-more-section">
                            <div class="learn-more-section-title">Description</div>
                            <div class="learn-more-section-text">${data.description}</div>
                        </div>
                    `;

                    if (data.learn_more) {
                        content += `
                            <div class="learn-more-section">
                                <div class="learn-more-section-title">Details</div>
                                <div class="learn-more-section-text">${data.learn_more}</div>
                            </div>
                        `;
                    }

                    if (data.preview) {
                        content += `
                            <div class="learn-more-section">
                                <div class="learn-more-section-title">What Happens</div>
                                <div class="learn-more-section-text">${data.preview}</div>
                            </div>
                        `;
                    }

                    if (data.ai_hint) {
                        content += `
                            <div class="learn-more-ai-hint">
                                <div class="learn-more-ai-hint-title">&#129504; AI Recommendation</div>
                                <div class="learn-more-ai-hint-text">${data.ai_hint}</div>
                            </div>
                        `;
                    }

                    document.getElementById('learn-more-content').innerHTML = content;
                    document.getElementById('learn-more-panel').classList.add('active');

                    if (data.companion_dialogue) {
                        updateCompanion(data.companion_dialogue);
                    }
                }
            } catch (e) {
                console.error('Failed to load learn more:', e);
            }
        }

        function closeLearnMore() {
            document.getElementById('learn-more-panel').classList.remove('active');
        }

        function updateCompanion(text) {
            document.getElementById('companion-text').innerHTML = text;
        }

        function addDialogueBubble(text, type = 'normal') {
            const container = document.getElementById('companion-dialogue');
            const bubble = document.createElement('div');
            bubble.className = 'dialogue-bubble';
            bubble.innerHTML = `<p class="dialogue-text">${text}</p>`;
            container.appendChild(bubble);
            container.scrollTop = container.scrollHeight;
        }

        async function askCompanion() {
            const input = document.getElementById('companion-question');
            const question = input.value.trim();
            if (!question) return;

            input.value = '';
            addDialogueBubble('You: ' + question, 'user');

            try {
                const res = await fetch('/api/experience/ask', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ question })
                });
                const data = await res.json();

                if (data.response) {
                    addDialogueBubble(data.response);
                }
                if (data.recommendation) {
                    addDialogueBubble('<strong>Recommendation:</strong> ' + data.recommendation);
                }
            } catch (e) {
                addDialogueBubble("I couldn't process that question. Try again?");
            }
        }

        // Keyboard shortcuts
        document.addEventListener('keydown', (e) => {
            if (!experience.active) return;

            if (e.key === 'Escape') {
                if (document.getElementById('action-confirm-modal').classList.contains('active')) {
                    cancelAction();
                } else if (document.getElementById('learn-more-panel').classList.contains('active')) {
                    closeLearnMore();
                } else {
                    closeExperience();
                }
            }
        });
'''


def get_complete_interactive_experience() -> str:
    """Return the complete interactive experience component."""
    return f'''
        <!-- Interactive Experience Styles -->
        <style>
{get_interactive_experience_css()}
        </style>

        {get_interactive_experience_html()}

        <script>
{get_interactive_experience_js()}
        </script>
'''
