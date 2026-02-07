# Tasks: SLATE Guided Experience & Brochure UI

**Spec ID**: 008-slate-guided-experience
**Status**: implementing
**Started**: 2026-02-07
**Updated**: 2026-02-07

## Implementation Checklist

### Phase 1: Lock Theme Spec
- [x] Define immutable color system
- [x] Define typography scale
- [x] Define spacing scale
- [x] Create design-tokens.py updates
- [x] Add blueprint engineering tokens
- [ ] Generate locked CSS file (.slate_identity/theme-locked.css)

### Phase 2: Brochure UI Elements
- [x] Hero section with animated blueprint background
- [x] Feature showcase cards (4-column grid)
- [x] System stats/metrics display (GPU, Local AI, Cloud Costs)
- [x] Primary/Secondary CTA buttons
- [ ] Scroll-to-explore indicator

### Phase 3: Guided Mode Core
- [x] Create slate/guided_mode.py module
- [x] GuidedModeState enum
- [x] GuidedStep dataclass
- [x] GuidedExecutor class
- [x] AIGuidanceNarrator class
- [x] Add API endpoints to dashboard

### Phase 4: Guided Mode UI
- [x] Full-screen guided overlay
- [x] Step progress indicators (numbered circles)
- [x] AI narrator bubble with avatar
- [x] Action status visualization
- [x] Auto-advance timer display

### Phase 5: AI Integration
- [x] Ollama narration prompt templates
- [x] Error diagnosis system
- [x] Recovery suggestion generator
- [ ] Contextual help tooltips

### Phase 6: Installer Integration
- [ ] Add guided mode to slate_installer.py
- [ ] Auto-launch guided mode on first run
- [ ] Save guided mode completion state
- [ ] Skip guided mode if already completed

## Files Created/Modified

### New Files
- `slate/guided_mode.py` - Core guided mode engine (complete)
- `specs/008-slate-guided-experience/spec.md` - Full specification

### Modified Files
- `agents/slate_dashboard_server.py` - Brochure UI + guided mode endpoints + overlay
- `docs/specs/design-inspiration.json` - Engineering patterns added
- `slate/design_tokens.py` - Blueprint engineering tokens

## API Endpoints Added

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/guided/status` | GET | Get current guided mode status |
| `/api/guided/start` | POST | Start guided mode |
| `/api/guided/execute` | POST | Execute current step |
| `/api/guided/advance` | POST | Advance to next step |
| `/api/guided/reset` | POST | Reset guided mode |
| `/api/guided/step` | GET | Get current step info |

## Guided Mode Flow

1. Welcome - Introduction to SLATE (3s auto-advance)
2. System Scan - Detect Python, GPU, Ollama, Docker
3. Python Check - Verify 3.11+
4. GPU Detect - Find NVIDIA GPUs
5. Ollama Setup - Connect to local LLM
6. Dashboard Start - Verify port 8080
7. GitHub Connect - Check gh CLI auth
8. Docker Check - Verify daemon (optional)
9. Claude Code - Check MCP config (optional)
10. Validation - Run health checks
11. Complete - Show success

## Current Status

Dashboard running at **http://127.0.0.1:8080** with:
- Brochure-style hero section
- Feature showcase grid
- "Start Guided Setup" CTA
- Full guided mode overlay
- AI narrator with avatar
- Step-by-step auto-execution
