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

## Implementation Priority

### Phase 1: Lock Theme Spec
- Define immutable color system
- Define typography scale
- Define spacing scale

### Phase 2: Brochure Elements
- Hero section with animated background
- Feature showcase cards
- Stats/metrics display

### Phase 3: Guided Mode Core
- GuidedModeState management
- Step execution engine
- AI narrator integration

### Phase 4-5: UI and AI Integration
- Full-screen overlay
- Ollama narration prompts
- Error diagnosis and recovery

## Related Specs

- [Spec 007: Design System](Spec-007-Design-System) - Visual foundation
- [Spec 009: Copilot Roadmap Awareness](Spec-009-Copilot-Roadmap-Awareness) - Integration
