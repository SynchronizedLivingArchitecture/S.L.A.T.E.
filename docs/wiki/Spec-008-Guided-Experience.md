# Specification 008: SLATE Guided Experience
<!-- Modified: 2026-02-07T12:00:00Z | Author: CLAUDE | Change: Create wiki page for spec 008 -->

**Status**: Implementing | **Created**: 2026-02-07

## Overview

Transform the SLATE Dashboard into a **product brochure experience** with an **AI-driven guided mode** that actively executes setup steps for users, forcing them down an optimal configuration path.

## Design Philosophy

### Brochure Site Principles
1. **Hero-First Design** - Large, impactful hero sections that sell SLATE's value
2. **Feature Showcases** - Visual demonstrations of capabilities before interaction
3. **Social Proof Elements** - System health, uptime, and capability metrics
4. **Progressive Disclosure** - Reveal complexity only when needed
5. **Call-to-Action Focus** - Every section drives toward the next action

### Guided Mode Principles
1. **AI-Driven Execution** - System performs actions, not just suggests them
2. **Forced Design Path** - Users follow the optimal setup sequence
3. **Zero-Decision Onboarding** - Smart defaults eliminate choice paralysis
4. **Real-Time Feedback** - AI narrates what it's doing and why
5. **Escape Hatches** - Advanced users can exit guided mode

## Guided Flow Sequence

```
1. WELCOME     - Hero with value proposition, auto-advance 3s
2. SYSTEM_SCAN - Auto-detect Python, GPU, Ollama, Docker, Claude Code
3. CORE_SERVICES - Configure dashboard, orchestrator, GPU scheduler
4. AI_BACKENDS - Setup Ollama, verify models, test inference
5. INTEGRATIONS - GitHub auth, Docker, MCP server
6. VALIDATION  - Health checks, workflow dispatch, GPU access
7. COMPLETE    - System summary, next steps
```

## Theme Specification (LOCKED)

### Color System

```css
/* Primary Brand */
--slate-primary: #B85A3C;         /* Anthropic-inspired warm rust */

/* Blueprint Engineering */
--blueprint-bg: #0D1B2A;          /* Deep technical blue */
--blueprint-grid: #1B3A4B;        /* Subtle grid lines */
--blueprint-accent: #98C1D9;      /* Highlight color */

/* Status Semantics */
--status-active: #22C55E;         /* Green - connected/running */
--status-pending: #F59E0B;        /* Amber - in progress */
--status-error: #EF4444;          /* Red - failed/error */
```

### Typography

```css
--font-display: 'Styrene A', 'Inter Tight', system-ui, sans-serif;
--font-body: 'Tiempos Text', 'Georgia', serif;
--font-mono: 'Cascadia Code', 'JetBrains Mono', 'Consolas', monospace;
```

## AI Narration System

The AI guides users through setup with contextual narration:

```python
class AIGuidanceNarrator:
    """AI voice that guides users through setup."""

    def narrate(self, action: str, status: str) -> str
    def explain_action(self, action: str) -> str
    def report_result(self, action: str, success: bool) -> str
    def suggest_next(self) -> str
```

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/guided/start` | POST | Start guided mode |
| `/api/guided/status` | GET | Get current guided state |
| `/api/guided/step` | GET | Get current step details |
| `/api/guided/advance` | POST | Force advance to next step |
| `/api/guided/pause` | POST | Pause guided execution |
| `/api/guided/resume` | POST | Resume guided execution |
| `/api/guided/exit` | POST | Exit guided mode |
| `/api/guided/narrate` | GET | Get AI narration for current state |

## Success Metrics

1. **Zero-Click Setup**: User can complete setup without manual configuration
2. **Sub-5-Minute Onboarding**: Full system ready in under 5 minutes
3. **100% Detection Rate**: All installed services auto-detected
4. **Graceful Degradation**: Missing services don't block progress
5. **Exit Accessibility**: Advanced users can exit at any point

## Brochure UI Sections

### Hero Section

```
┌─────────────────────────────────────────────────────────────────┐
│                                                                 │
│     ████  S.L.A.T.E.  ████                                     │
│     Synchronized Living Architecture                            │
│     for Transformation and Evolution                            │
│                                                                 │
│     [  Start Guided Setup  ]    [  Advanced Mode  ]            │
│                                                                 │
│     ▼ Scroll to Explore                                        │
└─────────────────────────────────────────────────────────────────┘
```

### Feature Showcase Cards

```
┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐
│   🧠 AI     │  │   ⚡ GPU    │  │   🤖 Agent  │  │   📦 Git   │
│   Local     │  │   Dual      │  │   Agentic   │  │   Actions  │
│   Inference │  │   Compute   │  │   Workflows │  │   Runner   │
│             │  │             │  │             │  │             │
│  Ollama +   │  │  RTX 5070   │  │  Claude +   │  │  Self-     │
│  Foundry    │  │  Ti x2      │  │  Copilot    │  │  Hosted    │
└─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘
```

## Guided Mode Overlay

```html
<div class="guided-overlay active">
    <div class="guided-header">
        <div class="guided-progress">Step 3 of 7</div>
        <button class="guided-exit">Exit Guided Mode</button>
    </div>

    <div class="guided-content">
        <div class="guided-narrator">
            <div class="narrator-avatar">🤖</div>
            <div class="narrator-text">
                "I'm now configuring your GPU scheduler..."
            </div>
        </div>

        <div class="guided-action">
            <div class="action-status">
                <span class="status-dot active"></span>
                Configuring GPU Scheduler...
            </div>
        </div>
    </div>

    <div class="guided-footer">
        <div class="step-indicators">
            <span class="step complete">1</span>
            <span class="step complete">2</span>
            <span class="step active">3</span>
            <span class="step pending">4</span>
            <span class="step pending">5</span>
            <span class="step pending">6</span>
            <span class="step pending">7</span>
        </div>
    </div>
</div>
```

## Implementation Progress

### Phase 1: Theme Spec
- [x] Define immutable color system
- [x] Define typography scale
- [x] Define spacing scale
- [x] Create design-tokens.py

### Phase 2: Brochure Elements
- [~] Hero section with animated background
- [~] Feature showcase cards
- [ ] Stats/metrics display
- [ ] CTA buttons

### Phase 3: Guided Mode Core
- [~] GuidedModeState management
- [~] Step execution engine
- [ ] AI narrator integration
- [ ] Auto-advance logic

### Phase 4: Guided Mode UI
- [ ] Full-screen overlay
- [ ] Step progress indicators
- [ ] Narrator bubble
- [ ] Action visualizations

### Phase 5: AI Integration
- [ ] Ollama narration prompts
- [ ] Error diagnosis
- [ ] Recovery suggestions
- [ ] Contextual help

## Implementation Files

| File | Description |
|------|-------------|
| `slate/guided_mode.py` | Guided mode state machine |
| `slate/guided_workflow.py` | Step execution engine |
| `slate_web/guided_workflow_ui.py` | UI components |
| `plugins/slate-copilot/src/slateGuidedInstallView.ts` | VSCode webview |

## CLI Commands

```bash
# Start guided mode
python slate/guided_mode.py --start

# Check current step
python slate/guided_mode.py --status

# Skip to step
python slate/guided_mode.py --skip-to 4

# Exit guided mode
python slate/guided_mode.py --exit
```

## Related Specs

- [Spec 007: Design System](Spec-007-Design-System) - Visual foundation
- [Spec 009: Copilot Roadmap Awareness](Spec-009-Copilot-Roadmap-Awareness) - Integration
