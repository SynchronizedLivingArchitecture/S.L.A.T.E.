# /slate-claude

Manage and validate Claude Code integration with SLATE.

## Usage

```
/slate-claude [action]
```

## Actions

| Action | Description |
|--------|-------------|
| `status` | Show Claude Code integration status (default) |
| `validate` | Run all validation checks |
| `report` | Generate full validation report |
| `agent-options` | Show recommended Agent SDK configuration |

## Examples

```bash
# Check integration status
/slate-claude status

# Run validation checks
/slate-claude validate

# Generate detailed report
/slate-claude report

# Show Agent SDK options for SLATE
/slate-claude agent-options
```

## What Gets Validated

1. **Settings** - `.claude/settings.json` and local settings
2. **MCP Servers** - Configuration and connectivity
3. **Permissions** - Allow/deny rules with ActionGuard check
4. **Hooks** - PreToolUse/PostToolUse configuration
5. **Security** - ActionGuard, PII Scanner, SDK Source Guard
6. **SDK Compatibility** - Anthropic SDK, MCP package, commands

## Integration with SLATE Security

The Claude Code validator integrates with SLATE's security systems:

- **ActionGuard**: Validates Bash commands and file operations
- **PII Scanner**: Scans for credentials before operations
- **SDK Source Guard**: Ensures trusted package sources

## Agent SDK Configuration

SLATE provides recommended Claude Agent SDK options:

```python
{
    "allowed_tools": ["Read", "Write", "Edit", "Bash", ...],
    "permission_mode": "acceptEdits",
    "system_prompt": "(loaded from CLAUDE.md)",
    "model": "claude-sonnet-4-5-20250929",
    "mcp_servers": {"slate": {...}},
    "hooks": {
        "PreToolUse": [...],
        "PostToolUse": [...]
    }
}
```

## Related Commands

- `/slate-status` - Overall SLATE system status
- `/slate-help` - All available commands
