# SLATE Guided Experience & Brochure UI Specification

**Spec ID**: 008-slate-guided-experience
**Status**: implementing
**Created**: 2026-02-07
**Author**: Claude Opus 4.5

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

## Theme Specification (LOCKED)

### Core Identity
```
Name: SLATE Engineering Blueprint Theme
Version: 3.0.0 (LOCKED)
Philosophy: Technical precision meets product elegance
```

### Color System (Immutable)
```css
/* Primary Brand */
--slate-primary: #B85A3C;         /* Anthropic-inspired warm rust */
--slate-primary-light: #D4785A;
--slate-primary-dark: #8B4530;

/* Blueprint Engineering */
--blueprint-bg: #0D1B2A;          /* Deep technical blue */
--blueprint-grid: #1B3A4B;        /* Subtle grid lines */
--blueprint-accent: #98C1D9;      /* Highlight color */
--blueprint-node: #E0FBFC;        /* Node backgrounds */

/* Status Semantics */
--status-active: #22C55E;         /* Green - connected/running */
--status-pending: #F59E0B;        /* Amber - in progress */
--status-error: #EF4444;          /* Red - failed/error */
--status-inactive: #6B7280;       /* Gray - stopped/offline */

/* Wizard Flow */
--step-active: #3B82F6;           /* Current step highlight */
--step-complete: #22C55E;         /* Completed checkmark */
--step-pending: #9CA3AF;          /* Future step muted */
```

### Typography (Immutable)
```css
--font-display: 'Styrene A', 'Inter Tight', system-ui, sans-serif;
--font-body: 'Tiempos Text', 'Georgia', serif;
--font-mono: 'Cascadia Code', 'JetBrains Mono', 'Consolas', monospace;
```

### Spacing Scale (Immutable)
```css
--space-xs: 4px;
--space-sm: 8px;
--space-md: 16px;
--space-lg: 24px;
--space-xl: 32px;
--space-2xl: 48px;
--space-3xl: 64px;
```

## Brochure UI Sections

### 1. Hero Section
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

### 2. Feature Showcase Cards
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

### 3. System Architecture (Blueprint)
```
┌─────────────────────────────────────────────────────────────────┐
│  ╔═══════════════════════════════════════════════════════════╗  │
│  ║  S.L.A.T.E. ARCHITECTURE BLUEPRINT                        ║  │
│  ╠═══════════════════════════════════════════════════════════╣  │
│  ║                                                           ║  │
│  ║     [Dashboard]──────[SLATE Core]──────[Ollama]          ║  │
│  ║          │                │                │              ║  │
│  ║          └────────┬───────┴────────┬──────┘              ║  │
│  ║                   │                │                      ║  │
│  ║          [GitHub Runner]    [Claude Code]                 ║  │
│  ║                   │                │                      ║  │
│  ║              [Docker]────────[GPU Cluster]               ║  │
│  ║                                                           ║  │
│  ╚═══════════════════════════════════════════════════════════╝  │
└─────────────────────────────────────────────────────────────────┘
```

## Guided Mode Specification

### Mode States
```python
class GuidedModeState:
    INACTIVE = "inactive"      # Standard dashboard mode
    INITIALIZING = "init"      # Scanning system
    EXECUTING = "executing"    # AI performing action
    WAITING = "waiting"        # Waiting for external process
    PAUSED = "paused"          # User intervention required
    COMPLETE = "complete"      # All steps finished
```

### Guided Flow Sequence
```
1. WELCOME
   - Display hero with value proposition
   - AI: "Let me set up your SLATE environment..."
   - Auto-advance after 3 seconds

2. SYSTEM_SCAN
   - AI: "Scanning your system for installed services..."
   - Auto-detect: Python, GPU, Ollama, Docker, Claude Code
   - Display results with status badges
   - Auto-advance when scan complete

3. CORE_SERVICES
   - AI: "Configuring core SLATE services..."
   - Execute: Start dashboard server
   - Execute: Initialize orchestrator
   - Execute: Configure GPU scheduler
   - Auto-advance when all pass

4. AI_BACKENDS
   - AI: "Setting up local AI inference..."
   - Execute: Check Ollama connection
   - Execute: Verify models (mistral-nemo)
   - Execute: Test inference endpoint
   - Auto-advance when ready

5. INTEGRATIONS
   - AI: "Connecting external services..."
   - Execute: Verify GitHub authentication
   - Execute: Check Docker daemon
   - Execute: Validate MCP server
   - Auto-advance when connected

6. VALIDATION
   - AI: "Running comprehensive validation..."
   - Execute: Health check all services
   - Execute: Test workflow dispatch
   - Execute: Verify GPU access
   - Auto-advance when validated

7. COMPLETE
   - AI: "Your SLATE system is fully operational!"
   - Display system summary
   - Offer: "Continue to Dashboard" or "Run AI Task"
```

### AI Narration System
```python
class AIGuidanceNarrator:
    """AI voice that guides users through setup."""

    def narrate(self, action: str, status: str) -> str:
        """Generate contextual guidance text."""

    def explain_action(self, action: str) -> str:
        """Explain what the system is about to do."""

    def report_result(self, action: str, success: bool) -> str:
        """Report the outcome of an action."""

    def suggest_next(self) -> str:
        """Suggest the next step in the flow."""
```

### Auto-Execution Engine
```python
class GuidedExecutor:
    """Executes setup steps automatically."""

    async def execute_step(self, step: GuidedStep) -> StepResult:
        """Execute a guided mode step."""
        # 1. Announce action via AI narrator
        # 2. Execute the actual command/check
        # 3. Report result
        # 4. Auto-advance or pause for error

    async def recover_from_error(self, error: Exception) -> bool:
        """Attempt automatic error recovery."""
        # Use Ollama to diagnose and suggest fixes
```

## API Endpoints for Guided Mode

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

## UI Components

### GuidedModeOverlay
Full-screen overlay that takes control during guided mode.

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
                "I'm now configuring your GPU scheduler for optimal
                dual-GPU load balancing..."
            </div>
        </div>

        <div class="guided-action">
            <div class="action-visual">
                <!-- Animated visualization of current action -->
            </div>
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

### BrochureHero
Marketing-style hero component.

```html
<section class="brochure-hero">
    <div class="hero-background">
        <!-- Animated blueprint grid -->
    </div>
    <div class="hero-content">
        <div class="hero-logo">
            <!-- Animated starburst logo -->
        </div>
        <h1 class="hero-title">S.L.A.T.E.</h1>
        <p class="hero-subtitle">
            Synchronized Living Architecture for<br>
            Transformation and Evolution
        </p>
        <div class="hero-stats">
            <div class="stat">
                <span class="stat-value">2x</span>
                <span class="stat-label">RTX 5070 Ti</span>
            </div>
            <div class="stat">
                <span class="stat-value">100%</span>
                <span class="stat-label">Local AI</span>
            </div>
            <div class="stat">
                <span class="stat-value">0</span>
                <span class="stat-label">Cloud Costs</span>
            </div>
        </div>
        <div class="hero-cta">
            <button class="cta-primary" onclick="startGuidedMode()">
                Start Guided Setup
            </button>
            <button class="cta-secondary" onclick="enterAdvancedMode()">
                Advanced Mode
            </button>
        </div>
    </div>
</section>
```

## Implementation Priority

### Phase 1: Lock Theme Spec
- [x] Define immutable color system
- [x] Define typography scale
- [x] Define spacing scale
- [x] Create design-tokens.py updates
- [ ] Generate locked CSS file

### Phase 2: Brochure Elements
- [ ] Hero section with animated background
- [ ] Feature showcase cards
- [ ] Stats/metrics display
- [ ] CTA buttons

### Phase 3: Guided Mode Core
- [ ] GuidedModeState management
- [ ] Step execution engine
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

## Success Metrics

1. **Zero-Click Setup**: User can complete setup without manual configuration
2. **Sub-5-Minute Onboarding**: Full system ready in under 5 minutes
3. **100% Detection Rate**: All installed services auto-detected
4. **Graceful Degradation**: Missing services don't block progress
5. **Exit Accessibility**: Advanced users can exit at any point

## Theme Lock Declaration

```
╔═══════════════════════════════════════════════════════════════╗
║                    THEME SPECIFICATION LOCK                    ║
╠═══════════════════════════════════════════════════════════════╣
║                                                               ║
║  Version: 3.0.0                                               ║
║  Status: LOCKED                                               ║
║  Date: 2026-02-07                                             ║
║                                                               ║
║  The following are immutable:                                 ║
║  - Primary color palette                                      ║
║  - Blueprint engineering colors                               ║
║  - Status semantic colors                                     ║
║  - Typography families                                        ║
║  - Spacing scale values                                       ║
║                                                               ║
║  Improvements must be additive, not breaking.                 ║
║                                                               ║
╚═══════════════════════════════════════════════════════════════╝
```
