# /slate-help

Show all available SLATE commands.

## Instructions

Display this help information:

---

## SLATE Commands

| Command | Description |
|---------|-------------|
| `/slate [start\|stop\|status]` | Manage SLATE orchestrator |
| `/slate-status` | Check system and service status |
| `/slate-workflow` | Manage task workflow queue |
| `/slate-runner` | Manage GitHub Actions runner |
| `/slate-multirunner` | Manage multi-runner system |
| `/slate-discussions` | Manage GitHub Discussions |
| `/slate-gpu` | Manage dual-GPU load balancing |
| `/slate-claude` | Validate Claude Code integration |
| `/slate-help` | Show this help |

## Quick Examples

```
/slate start          # Start all SLATE services
/slate stop           # Stop all services
/slate-status         # Check GPU, services, environment
/slate-workflow       # View task queue health
/slate-runner         # Check GitHub runner status
/slate-claude validate  # Validate Claude Code integration
```

## MCP Tools

The SLATE MCP server also provides these tools for direct use:
- `slate_status` - Check all services and GPU status
- `slate_workflow` - Manage task queue
- `slate_orchestrator` - Start/stop services
- `slate_runner` - Manage GitHub runner
- `slate_ai` - Execute AI tasks via local LLMs
- `slate_runtime` - Check runtime integrations
- `slate_hardware` - Detect and optimize GPU hardware
- `slate_gpu` - Manage dual-GPU load balancing
- `slate_claude_code` - Validate Claude Code configuration

---
