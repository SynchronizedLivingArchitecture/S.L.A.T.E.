# Contributing to SLATE
# Modified: 2026-02-08T06:00:00Z | Author: COPILOT | Change: Add agent development guide, kernel-style contribution workflow

Thank you for your interest in contributing to S.L.A.T.E. (Synchronized Living Architecture for Transformation and Evolution)!

## Quick Start

1. **Fork** the repository: https://github.com/SynchronizedLivingArchitecture/S.L.A.T.E.
2. **Clone** your fork locally
3. **Initialize** your SLATE workspace:
   ```bash
   python slate/slate_fork_manager.py --init --name "Your Name" --email "you@example.com"
   ```
4. **Validate** your changes before submitting:
   ```bash
   python slate/slate_fork_manager.py --validate
   ```

## Contribution Workflow

```
Your Fork → Feature Branch → Validate → PR → Review → Merge
```

### 1. Create a Feature Branch

```bash
git checkout -b feature/your-feature-name
```

### 2. Make Changes

- Follow the existing code style
- Add tests for new features
- Update documentation if needed

### 3. Validate

```bash
# Run tests
python -m pytest tests/ -v

# Validate SLATE prerequisites
python slate/slate_fork_manager.py --validate
```

### 4. Submit PR

Push your branch and create a Pull Request against the `main` branch.

## Requirements

All contributions must:

- [ ] Pass all tests (Arrange-Act-Assert format)
- [ ] Pass validation checks
- [ ] Not modify protected files (see below)
- [ ] Bind only to `127.0.0.1` (never `0.0.0.0`)
- [ ] Keep ActionGuard intact

## Protected Files

These files cannot be modified by external contributors:

- `.github/workflows/*` - CI/CD automation
- `.github/CODEOWNERS` - Access control
- `slate/action_guard.py` - Security enforcement
- `slate/sdk_source_guard.py` - Package validation

## Code Style

- **Python 3.11+** required
- **Type hints** for all functions
- **Google-style docstrings**
- **Ruff** for linting and formatting

## AAA Engineering Standards (Required)

SLATE follows AAA standards across testing, accessibility, security, and performance.

### 1) Test Rigor (Arrange-Act-Assert)
- Tests must use explicit Arrange, Act, Assert sections
- Coverage should focus on `slate/` and `slate_core/`
- Use `pytest` and `pytest-asyncio` for async tests

### 2) Accessibility (WCAG AAA for UI)
- All UI must be keyboard accessible (tab order, focus states)
- Provide text alternatives for non-text content
- Maintain strong contrast and readable typography
- Avoid motion that cannot be disabled

### 3) Security/Compliance
- No external network calls without explicit user consent
- ActionGuard must remain enforced
- Avoid dynamic execution (no `eval`, `exec`)
- No secrets or tokens in code or logs

### 4) Performance/Reliability
- Validate performance using `slate/slate_benchmark.py`
- Avoid blocking calls in request handlers
- Add timeouts and retries to IO operations

### SLATE System Validation
Use SLATE workflows and tools for validation before PRs:

```bash
python slate/slate_status.py --quick
python slate/slate_runtime.py --check-all
python slate/slate_workflow_manager.py --status
```

```bash
# Lint
ruff check slate/ agents/

# Format
ruff format slate/ agents/
```

## Security

SLATE is a **local-only** system. All contributions must:

1. Bind servers to `127.0.0.1` only
2. Avoid `eval()`, `exec()` with dynamic content
3. Never include credentials or API keys
4. Not make external network calls without explicit user consent

## Getting Help

- Check the [wiki](https://github.com/SynchronizedLivingArchitecture/S.L.A.T.E/wiki)
- Open an [issue](https://github.com/SynchronizedLivingArchitecture/S.L.A.T.E/issues)
- Read `CLAUDE.md` for project guidelines
- See `docs/specs/agents-capacity.md` for system capacity planning

## Creating a New Agent (Kernel-Style Plugins)

SLATE uses a kernel-style modular agent system. Each agent is a Python file in
`slate_core/plugins/agents/` that subclasses `AgentBase`.

### 1. Create the Agent File

```python
# slate_core/plugins/agents/your_agent.py
# Modified: YYYY-MM-DDTHH:MM:SSZ | Author: YOUR_NAME | Change: description

from slate_core.plugins.agent_registry import AgentBase, AgentCapability

class YourAgent(AgentBase):
    AGENT_ID = "YOUR_AGENT"
    AGENT_NAME = "Your Agent Name"
    AGENT_VERSION = "1.0.0"
    AGENT_DESCRIPTION = "What your agent does"
    REQUIRES_GPU = False
    DEPENDENCIES = []  # Other agent IDs required

    def capabilities(self):
        return [
            AgentCapability(
                name="your_capability",
                patterns=["keyword1", "keyword2"],
                requires_gpu=False,
                priority=50,
                description="What tasks this handles",
            ),
        ]

    def execute(self, task: dict) -> dict:
        # Process the task
        return {"success": True, "result": "done"}

    def health_check(self) -> dict:
        base = super().health_check()
        base["healthy"] = True
        return base
```

### 2. Test Your Agent

```bash
# Discover & load
python slate_core/plugins/agent_registry.py --discover
python slate_core/plugins/agent_registry.py --load YOUR_AGENT

# Health check
python slate_core/plugins/agent_registry.py --health
```

### 3. Add Tests (Required)

Create `tests/test_your_agent.py` following Arrange-Act-Assert pattern.

### Agent Registry CLI (Kernel Commands)

| Command | Linux Kernel Equivalent | Description |
|---------|------------------------|-------------|
| `--discover` | `modprobe --list` | Find available agents |
| `--load AGENT` | `insmod` | Load agent into memory |
| `--unload AGENT` | `rmmod` | Remove agent from memory |
| `--reload AGENT` | `rmmod + insmod` | Hot-reload agent |
| `--load-all` | — | Load all discovered agents |
| `--status` | `lsmod` | Show loaded agents |
| `--health` | — | Run health checks |

### Current Agent Roster

| Agent | Role | Routing Patterns |
|-------|------|-----------------|
| ALPHA | Coding | implement, code, build, fix, create, add, refactor |
| BETA | Testing | test, validate, verify, coverage, check, lint |
| GAMMA | Planning | analyze, plan, research, document, review, design |
| DELTA | Integration | claude, mcp, sdk, integration, api, plugin |
| EPSILON | Spec-Weaver | spec, architecture, blueprint, schema, rfc, capacity |
| ZETA | Benchmark Oracle | benchmark, performance, profile, throughput, optimize |
| COPILOT | Orchestration | complex, multi-step, orchestrate, deploy, release |

## License

By contributing, you agree that your contributions will be licensed under the
S.L.A.T.E. Experimental Open Source License (EOSL-1.0).

---

*Thank you for helping make SLATE better!*
