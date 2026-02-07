# S.L.A.T.E. Wiki
<!-- Modified: 2026-02-07T12:00:00Z | Author: CLAUDE | Change: Add Claude Code integration and v2.5 features -->

Welcome to **S.L.A.T.E.** (Synchronized Living Architecture for Transformation and Evolution) - turn your local hardware into an AI operations center for GitHub.

## Why SLATE?

GitHub Actions is powerful. But if you want AI in your pipeline, you're paying per-token to cloud providers. Your code gets sent to external servers. You're rate-limited.

**SLATE changes that.** Your local machine becomes the brain behind your GitHub operations.

## What You Get

| Feature | Description |
|---------|-------------|
| **Local AI Engine** | Ollama + Foundry running on your GPU. No API bills. |
| **Persistent Memory** | ChromaDB stores codebase context across sessions. |
| **Live Dashboard** | Monitor services, tasks, and GPU in real-time. |
| **GitHub Bridge** | Self-hosted runner syncs with Issues, PRs, and Projects. |
| **Claude Code Integration** | MCP server + slash commands for Claude Code. |
| **Guided Experience** | AI-driven setup wizard for zero-config onboarding. |

## Quick Navigation

| Section | Description |
|---------|-------------|
| [Getting Started](Getting-Started) | Installation and first steps |
| [Architecture](Architecture) | System design and components |
| [CLI Reference](CLI-Reference) | Command-line tools and options |
| [Configuration](Configuration) | Settings and customization |
| [Development](Development) | Contributing and extending SLATE |
| [Troubleshooting](Troubleshooting) | Common issues and solutions |

## GitHub Integration

SLATE creates a bridge between your local hardware and GitHub:

```
GitHub Issues → SLATE pulls to local queue → Local AI processes → Results pushed as commits/PR comments
```

**Built-in workflows:**
- CI Pipeline (Push/PR) - Linting, tests, AI code review
- AI Maintenance (Every 4h) - Codebase analysis, auto-docs
- Nightly Jobs (Daily 4am) - Full test suite, dependency audit
- Project Automation (Every 30min) - Sync Issues/PRs to boards

## Built-In Safeguards

| Guard | What It Does |
|-------|--------------|
| **ActionGuard** | Blocks `rm -rf`, `0.0.0.0` bindings, `eval()`, external API calls |
| **SDK Source Guard** | Only trusted publishers (Microsoft, NVIDIA, Meta, Google) |
| **PII Scanner** | Catches API keys and credentials before GitHub sync |
| **Resource Limits** | Max tasks, stale detection, GPU memory monitoring |

## Getting Help

- [GitHub Issues](https://github.com/SynchronizedLivingArchitecture/S.L.A.T.E/issues) - Bug reports and feature requests
- [Discussions](https://github.com/SynchronizedLivingArchitecture/S.L.A.T.E/discussions) - Questions and community support

## Version

Current version: **2.5.0**

---

**The Philosophy:** Cloud for collaboration. Local for compute. Full control.
