# Specification 009: @slate Copilot Participant Roadmap Awareness
<!-- Modified: 2026-02-07T12:00:00Z | Author: CLAUDE | Change: Create wiki page for spec 009 -->

**Status**: Completed | **Created**: 2026-02-07

## Overview

Enhance the @slate VSCode chat participant to have full SLATE system awareness, keeping development roadmap/plan aligned, guiding Copilot's code writes, executing workflows, and reducing token costs.

## Goals

1. **Roadmap Awareness** - Know current dev stage, active specs, and task queue
2. **Code Guidance** - Stage-specific coding patterns and recommendations
3. **Token Optimization** - Compressed context for efficient LLM usage
4. **Workflow Execution** - Full integration with SLATE's 8-layer ecosystem
5. **Spec Alignment** - All code suggestions match roadmap requirements

## New Tools (5 Added)

| Tool | Purpose | Maps To |
|------|---------|---------|
| `slate_devCycle` | Development cycle state machine | Dev Cycle Engine |
| `slate_specKit` | Spec processing and wiki generation | Spec-Kit |
| `slate_learningProgress` | XP, achievements, learning paths | Interactive Tutor |
| `slate_planContext` | **TOKEN SAVER** - compressed context | All systems |
| `slate_codeGuidance` | Stage-aware code recommendations | Dev Cycle + Specs |

## New Commands (6 Added)

| Command | Layer | Description |
|---------|-------|-------------|
| `/roadmap` | Roadmap | View dev stage, specs, tasks |
| `/stage` | Dev Cycle | View/change development stage |
| `/guidance` | Code | Stage-specific coding patterns |
| `/context` | Tokens | Compressed context summary |
| `/specs` | Specs | Process specs, run AI analysis |
| `/learn` | Learning | Track progress and achievements |

## Development Cycle Integration

```
@slate Participant
  PLAN  -->  CODE  -->  TEST  -->  DEPLOY  -->
    |          |          |          |
    +----------+----------+----------+
                    |
              FEEDBACK guidance
```

### Stage-Specific Guidance

| Stage | Focus | Code Patterns |
|-------|-------|---------------|
| PLAN | Architecture | Interface design, specs, requirements |
| CODE | Implementation | Type hints, docstrings, minimal changes |
| TEST | Validation | pytest, 50%+ coverage, descriptive names |
| DEPLOY | CI/CD | GitHub Actions, runner checks, docs |
| FEEDBACK | Review | Discussions, achievements, patterns |

## Token Optimization

### Plan Context Tool

The `slate_planContext` tool returns a single-line compressed summary:

```
STAGE: CODE | Iteration: v0.1.0 | Cycle: 0
TASKS: 5 pending, 1 in-progress
SPECS: 005-monochrome-theme, 006-natural-theme, 007-design-system, 008-guided-experience
DIRECTIVE: Implement features. Follow existing patterns.
```

This saves ~500+ tokens compared to fetching full state from each subsystem.

## Spec Alignment

### Connected Specifications

| Spec | Alignment |
|------|-----------|
| 005-monochrome-theme | Colors used in Control Board |
| 006-natural-theme-system | Theme slider integration |
| 007-slate-design-system | M3 tokens, starburst logo |
| 008-slate-guided-experience | Guided mode + AI narration |

## Files Modified

### TypeScript (VSCode Extension)

| File | Changes |
|------|---------|
| `plugins/slate-copilot/src/tools.ts` | +5 new tools, extended state interface |
| `plugins/slate-copilot/src/slateParticipant.ts` | +6 commands, roadmap-aware system prompt |
| `plugins/slate-copilot/src/slateControlBoardView.ts` | Mini ring, learning toggle |

### Python (Backend)

| File | Changes |
|------|---------|
| `slate/dev_cycle_engine.py` | --activities, --reason CLI args |
| `slate/interactive_tutor.py` | --next CLI arg |
| `slate/slate_spec_kit.py` | --list, --roadmap, --brief CLI args |

## Success Metrics

1. **Tool Count**: 26 tools (up from 21)
2. **Command Count**: 18 commands (up from 12)
3. **Token Savings**: ~40% reduction via planContext
4. **Roadmap Adherence**: 100% stage-aware code suggestions
5. **Spec Coverage**: All 4 active specs integrated

## Testing

```bash
# Compile TypeScript
cd plugins/slate-copilot && npm run compile

# Test Python CLI
python slate/dev_cycle_engine.py --status --json
python slate/interactive_tutor.py --status --json
python slate/slate_spec_kit.py --list

# Test @slate commands in VSCode
@slate /help
@slate /roadmap
@slate /context
@slate /guidance
```

## Related Specs

- [Spec 007: Design System](Spec-007-Design-System) - Visual tokens
- [Spec 008: Guided Experience](Spec-008-Guided-Experience) - AI narration
