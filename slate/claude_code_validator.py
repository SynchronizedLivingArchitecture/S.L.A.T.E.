#!/usr/bin/env python3
# Modified: 2026-02-07T10:00:00Z | Author: COPILOT | Change: Initial creation of Claude Code validator
"""
Claude Code Validator - Comprehensive settings validation and management for SLATE.

Validates and manages:
- Claude Code settings (project and user-level)
- MCP server configuration
- Hook system integration with ActionGuard
- Permission management
- Claude Agent SDK compatibility
- Session and context management

Based on Claude Agent SDK documentation:
https://platform.claude.com/docs/en/agent-sdk/overview
"""

import json
import logging
import os
import re
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

# Add workspace root to path
WORKSPACE_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(WORKSPACE_ROOT))

from slate.action_guard import ActionGuard, get_guard

logger = logging.getLogger("slate.claude_code_validator")


# ── Configuration Schema ─────────────────────────────────────────────────

# Claude Code permission modes
PERMISSION_MODES = ["default", "acceptEdits", "bypassPermissions", "plan"]

# Required MCP server fields
MCP_REQUIRED_FIELDS = ["command", "args"]

# Claude models and their capabilities
CLAUDE_MODELS = {
    "claude-opus-4-6": {"tier": "premium", "tool_search": True, "max_tokens": 200000},
    "claude-opus-4-5-20251101": {"tier": "premium", "tool_search": True, "max_tokens": 200000},
    "claude-sonnet-4-5-20250929": {"tier": "standard", "tool_search": True, "max_tokens": 200000},
    "claude-haiku-4-5-20251001": {"tier": "fast", "tool_search": False, "max_tokens": 200000},
}

# Built-in tools in Claude Code
BUILTIN_TOOLS = [
    "Read", "Write", "Edit", "Bash", "Glob", "Grep",
    "WebSearch", "WebFetch", "Task", "TodoWrite",
    "AskUserQuestion", "NotebookEdit", "Skill",
]

# Hook event types
HOOK_EVENTS = [
    "PreToolUse", "PostToolUse", "PostToolUseFailure",
    "UserPromptSubmit", "Stop", "SubagentStart", "SubagentStop",
    "PreCompact", "SessionStart", "SessionEnd", "Notification",
]

# Default SLATE hooks for security
DEFAULT_SLATE_HOOKS = {
    "PreToolUse": [
        {
            "matcher": "Bash",
            "description": "Validate bash commands through ActionGuard",
            "action": "validate_command",
        },
        {
            "matcher": "Write|Edit",
            "description": "Validate file paths for safety",
            "action": "validate_file_path",
        },
    ],
    "PostToolUse": [
        {
            "matcher": ".*",
            "description": "Audit log all tool executions",
            "action": "audit_log",
        },
    ],
}


# ── Data Classes ─────────────────────────────────────────────────────────

@dataclass
class ValidationResult:
    """Result of a validation check."""
    valid: bool
    component: str
    message: str
    suggestions: list[str] = field(default_factory=list)

    def __str__(self) -> str:
        status = "PASS" if self.valid else "FAIL"
        return f"[{status}] {self.component}: {self.message}"


@dataclass
class ClaudeCodeConfig:
    """Parsed Claude Code configuration."""
    settings_path: Optional[Path] = None
    settings: dict = field(default_factory=dict)
    local_settings_path: Optional[Path] = None
    local_settings: dict = field(default_factory=dict)
    mcp_servers: dict = field(default_factory=dict)
    permissions: dict = field(default_factory=dict)
    plugins: list = field(default_factory=list)
    hooks: dict = field(default_factory=dict)


# ── ClaudeCodeValidator Class ────────────────────────────────────────────

class ClaudeCodeValidator:
    """
    Validates and manages Claude Code configuration for SLATE.

    Usage:
        validator = ClaudeCodeValidator()
        results = validator.validate_all()
        for r in results:
            print(r)
    """

    def __init__(self, workspace: Optional[Path] = None):
        self.workspace = workspace or WORKSPACE_ROOT
        self.config = ClaudeCodeConfig()
        self.guard = get_guard()
        self._load_config()

    def _load_config(self) -> None:
        """Load all Claude Code configuration files."""
        # Project-level .claude directory
        claude_dir = self.workspace / ".claude"

        # Load settings.json
        settings_path = claude_dir / "settings.json"
        if settings_path.exists():
            self.config.settings_path = settings_path
            try:
                with open(settings_path) as f:
                    self.config.settings = json.load(f)
            except json.JSONDecodeError as e:
                logger.error(f"Invalid JSON in settings.json: {e}")

        # Load settings.local.json
        local_settings_path = claude_dir / "settings.local.json"
        if local_settings_path.exists():
            self.config.local_settings_path = local_settings_path
            try:
                with open(local_settings_path) as f:
                    self.config.local_settings = json.load(f)
            except json.JSONDecodeError as e:
                logger.error(f"Invalid JSON in settings.local.json: {e}")

        # Load plugin.json for MCP servers
        plugin_json = self.workspace / ".claude-plugin" / "plugin.json"
        if plugin_json.exists():
            try:
                with open(plugin_json) as f:
                    plugin_data = json.load(f)
                    self.config.mcp_servers = plugin_data.get("mcpServers", {})
                    self.config.plugins = plugin_data.get("commands", [])
            except json.JSONDecodeError as e:
                logger.error(f"Invalid JSON in plugin.json: {e}")

        # Extract permissions
        self.config.permissions = self.config.local_settings.get("permissions", {})

    def validate_all(self) -> list[ValidationResult]:
        """Run all validation checks."""
        results = []
        results.extend(self.validate_settings())
        results.extend(self.validate_mcp_servers())
        results.extend(self.validate_permissions())
        results.extend(self.validate_hooks())
        results.extend(self.validate_security_integration())
        results.extend(self.validate_sdk_compatibility())
        return results

    def validate_settings(self) -> list[ValidationResult]:
        """Validate Claude Code settings files."""
        results = []

        # Check settings.json exists
        if not self.config.settings_path or not self.config.settings_path.exists():
            results.append(ValidationResult(
                valid=False,
                component="settings.json",
                message="Settings file not found",
                suggestions=["Create .claude/settings.json with plugin configuration"],
            ))
        else:
            results.append(ValidationResult(
                valid=True,
                component="settings.json",
                message=f"Found at {self.config.settings_path}",
            ))

            # Validate plugin configuration
            if "enabledPlugins" in self.config.settings:
                results.append(ValidationResult(
                    valid=True,
                    component="plugins",
                    message=f"Plugins configured: {list(self.config.settings['enabledPlugins'].keys())}",
                ))
            elif "plugins" in self.config.settings:
                results.append(ValidationResult(
                    valid=True,
                    component="plugins",
                    message=f"Plugins enabled: {self.config.settings['plugins'].get('enabled', [])}",
                ))

        # Check local settings
        if self.config.local_settings_path and self.config.local_settings_path.exists():
            results.append(ValidationResult(
                valid=True,
                component="settings.local.json",
                message="Local settings found (user-specific)",
            ))

        return results

    def validate_mcp_servers(self) -> list[ValidationResult]:
        """Validate MCP server configuration."""
        results = []

        if not self.config.mcp_servers:
            results.append(ValidationResult(
                valid=False,
                component="mcp_servers",
                message="No MCP servers configured",
                suggestions=[
                    "Add mcpServers to .claude-plugin/plugin.json",
                    "Configure SLATE MCP server for tool integration",
                ],
            ))
            return results

        for server_name, server_config in self.config.mcp_servers.items():
            # Check required fields
            missing = [f for f in MCP_REQUIRED_FIELDS if f not in server_config]
            if missing:
                results.append(ValidationResult(
                    valid=False,
                    component=f"mcp:{server_name}",
                    message=f"Missing required fields: {missing}",
                    suggestions=[f"Add {f} to MCP server config" for f in missing],
                ))
                continue

            # Validate command path (expand variables)
            command = server_config.get("command", "")
            expanded_command = self._expand_variables(command)

            if not Path(expanded_command).exists():
                results.append(ValidationResult(
                    valid=False,
                    component=f"mcp:{server_name}",
                    message=f"Command not found: {expanded_command}",
                    suggestions=["Verify Python venv path", "Run pip install to create venv"],
                ))
            else:
                results.append(ValidationResult(
                    valid=True,
                    component=f"mcp:{server_name}",
                    message=f"Server configured: {command}",
                ))

            # Validate args reference valid script
            args = server_config.get("args", [])
            for arg in args:
                expanded_arg = self._expand_variables(arg)
                if expanded_arg.endswith(".py"):
                    if not Path(expanded_arg).exists():
                        results.append(ValidationResult(
                            valid=False,
                            component=f"mcp:{server_name}",
                            message=f"Script not found: {expanded_arg}",
                            suggestions=["Verify script path exists"],
                        ))

            # Validate environment variables
            env = server_config.get("env", {})
            if "PYTHONPATH" not in env:
                results.append(ValidationResult(
                    valid=False,
                    component=f"mcp:{server_name}:env",
                    message="PYTHONPATH not set in environment",
                    suggestions=["Add PYTHONPATH to env for proper imports"],
                ))

        return results

    def validate_permissions(self) -> list[ValidationResult]:
        """Validate permission configuration."""
        results = []

        permissions = self.config.permissions
        if not permissions:
            results.append(ValidationResult(
                valid=True,
                component="permissions",
                message="Using default permission mode",
            ))
            return results

        # Check allow list
        allow_list = permissions.get("allow", [])
        for rule in allow_list:
            # Validate rule format
            if not re.match(r"^\w+\([^)]*\)$", rule):
                results.append(ValidationResult(
                    valid=False,
                    component="permissions:allow",
                    message=f"Invalid rule format: {rule}",
                    suggestions=["Use format: Tool(pattern:*)"],
                ))
            else:
                # Check against ActionGuard
                if "Bash(" in rule:
                    # Extract command pattern
                    match = re.search(r"Bash\(([^:]+):", rule)
                    if match:
                        cmd_pattern = match.group(1)
                        guard_result = self.guard.validate_command(cmd_pattern)
                        if not guard_result.allowed:
                            results.append(ValidationResult(
                                valid=False,
                                component="permissions:allow",
                                message=f"Rule conflicts with ActionGuard: {rule}",
                                suggestions=[f"ActionGuard blocks: {guard_result.reason}"],
                            ))
                        else:
                            results.append(ValidationResult(
                                valid=True,
                                component="permissions:allow",
                                message=f"Rule OK: {rule}",
                            ))

        # Check deny list
        deny_list = permissions.get("deny", [])
        for rule in deny_list:
            results.append(ValidationResult(
                valid=True,
                component="permissions:deny",
                message=f"Deny rule configured: {rule}",
            ))

        return results

    def validate_hooks(self) -> list[ValidationResult]:
        """Validate hook configuration for SLATE integration."""
        results = []

        # Check if hooks are configured
        hooks = self.config.hooks
        if not hooks:
            results.append(ValidationResult(
                valid=True,
                component="hooks",
                message="No custom hooks configured (using defaults)",
                suggestions=[
                    "Consider adding PreToolUse hooks for ActionGuard integration",
                    "Add PostToolUse hooks for audit logging",
                ],
            ))
            return results

        for event_type, event_hooks in hooks.items():
            if event_type not in HOOK_EVENTS:
                results.append(ValidationResult(
                    valid=False,
                    component=f"hooks:{event_type}",
                    message=f"Unknown hook event type: {event_type}",
                    suggestions=[f"Valid events: {HOOK_EVENTS}"],
                ))
            else:
                results.append(ValidationResult(
                    valid=True,
                    component=f"hooks:{event_type}",
                    message=f"Hook configured for {event_type}",
                ))

        return results

    def validate_security_integration(self) -> list[ValidationResult]:
        """Validate SLATE security integration."""
        results = []

        # Check ActionGuard is available
        try:
            guard = get_guard()
            results.append(ValidationResult(
                valid=True,
                component="security:action_guard",
                message="ActionGuard initialized",
            ))

            # Test basic patterns
            test_result = guard.validate_command("python slate/slate_status.py")
            if test_result.allowed:
                results.append(ValidationResult(
                    valid=True,
                    component="security:action_guard:test",
                    message="ActionGuard accepting valid commands",
                ))

            # Test blocked pattern
            blocked_result = guard.validate_command("rm -rf /")
            if not blocked_result.allowed:
                results.append(ValidationResult(
                    valid=True,
                    component="security:action_guard:block",
                    message="ActionGuard blocking dangerous commands",
                ))
        except Exception as e:
            results.append(ValidationResult(
                valid=False,
                component="security:action_guard",
                message=f"ActionGuard error: {e}",
            ))

        # Check PII scanner
        pii_scanner_path = self.workspace / "slate" / "pii_scanner.py"
        if pii_scanner_path.exists():
            results.append(ValidationResult(
                valid=True,
                component="security:pii_scanner",
                message="PII Scanner available",
            ))
        else:
            results.append(ValidationResult(
                valid=False,
                component="security:pii_scanner",
                message="PII Scanner not found",
                suggestions=["Create slate/pii_scanner.py for credential scanning"],
            ))

        # Check SDK source guard
        sdk_guard_path = self.workspace / "slate" / "sdk_source_guard.py"
        if sdk_guard_path.exists():
            results.append(ValidationResult(
                valid=True,
                component="security:sdk_source_guard",
                message="SDK Source Guard available",
            ))

        return results

    def validate_sdk_compatibility(self) -> list[ValidationResult]:
        """Validate Claude Agent SDK compatibility."""
        results = []

        # Check for anthropic SDK
        try:
            import anthropic
            results.append(ValidationResult(
                valid=True,
                component="sdk:anthropic",
                message=f"Anthropic SDK available: {anthropic.__version__}",
            ))
        except ImportError:
            results.append(ValidationResult(
                valid=False,
                component="sdk:anthropic",
                message="Anthropic SDK not installed",
                suggestions=["pip install anthropic"],
            ))

        # Check for MCP package
        try:
            import mcp
            results.append(ValidationResult(
                valid=True,
                component="sdk:mcp",
                message="MCP package available",
            ))
        except ImportError:
            results.append(ValidationResult(
                valid=False,
                component="sdk:mcp",
                message="MCP package not installed",
                suggestions=["pip install mcp"],
            ))

        # Check CLAUDE.md exists
        claude_md = self.workspace / "CLAUDE.md"
        if claude_md.exists():
            results.append(ValidationResult(
                valid=True,
                component="sdk:claude_md",
                message="CLAUDE.md project instructions found",
            ))
        else:
            results.append(ValidationResult(
                valid=False,
                component="sdk:claude_md",
                message="CLAUDE.md not found",
                suggestions=["Create CLAUDE.md with project-specific instructions"],
            ))

        # Check commands directory
        commands_dir = self.workspace / ".claude" / "commands"
        if commands_dir.exists():
            command_files = list(commands_dir.glob("*.md"))
            results.append(ValidationResult(
                valid=True,
                component="sdk:commands",
                message=f"Found {len(command_files)} slash commands",
            ))
        else:
            results.append(ValidationResult(
                valid=False,
                component="sdk:commands",
                message="No slash commands directory",
                suggestions=["Create .claude/commands/ for custom commands"],
            ))

        return results

    def _expand_variables(self, value: str) -> str:
        """Expand environment variables and special tokens."""
        # Expand ${CLAUDE_PLUGIN_ROOT}
        value = value.replace("${CLAUDE_PLUGIN_ROOT}", str(self.workspace))
        # Expand environment variables
        value = os.path.expandvars(value)
        return value

    def get_recommended_config(self) -> dict:
        """Generate recommended Claude Code configuration for SLATE."""
        return {
            "settings.json": {
                "extraKnownMarketplaces": {
                    "slate-marketplace": {"source": "."}
                },
                "enabledPlugins": {
                    "slate-sdk@slate-marketplace": True
                },
            },
            "settings.local.json": {
                "permissions": {
                    "allow": [
                        "Bash(python:*)",
                        "Bash(pytest:*)",
                        "Bash(git:*)",
                        "Bash(ruff:*)",
                        "Bash(pip:*)",
                    ],
                    "deny": [
                        "Bash(rm -rf:*)",
                        "Bash(eval:*)",
                        "Bash(curl:* | bash)",
                    ],
                },
            },
            "plugin.json": {
                "name": "slate-sdk",
                "version": "1.1.0",
                "mcpServers": {
                    "slate": {
                        "command": "${CLAUDE_PLUGIN_ROOT}/.venv/Scripts/python.exe",
                        "args": ["${CLAUDE_PLUGIN_ROOT}/slate/mcp_server.py"],
                        "env": {
                            "SLATE_WORKSPACE": "${CLAUDE_PLUGIN_ROOT}",
                            "PYTHONPATH": "${CLAUDE_PLUGIN_ROOT}",
                            "PYTHONIOENCODING": "utf-8",
                        },
                    },
                },
            },
            "hooks": DEFAULT_SLATE_HOOKS,
        }

    def generate_report(self) -> str:
        """Generate a validation report."""
        results = self.validate_all()

        lines = [
            "=" * 60,
            "  SLATE Claude Code Validation Report",
            "=" * 60,
            "",
        ]

        passed = sum(1 for r in results if r.valid)
        failed = sum(1 for r in results if not r.valid)

        # Group by component category
        categories = {}
        for r in results:
            cat = r.component.split(":")[0]
            if cat not in categories:
                categories[cat] = []
            categories[cat].append(r)

        for cat, cat_results in categories.items():
            lines.append(f"\n  {cat.upper()}")
            lines.append("  " + "-" * 40)
            for r in cat_results:
                status = "PASS" if r.valid else "FAIL"
                lines.append(f"    [{status}] {r.component}: {r.message}")
                if r.suggestions and not r.valid:
                    for s in r.suggestions:
                        lines.append(f"           -> {s}")

        lines.extend([
            "",
            "=" * 60,
            f"  Summary: {passed} passed, {failed} failed",
            "=" * 60,
        ])

        return "\n".join(lines)


# ── Hook Handler Functions ───────────────────────────────────────────────

def create_pretool_hook() -> dict:
    """Create a PreToolUse hook for ActionGuard validation."""
    return {
        "hook_event_name": "PreToolUse",
        "validate": lambda tool_name, tool_input: _validate_tool_use(tool_name, tool_input),
    }


def _validate_tool_use(tool_name: str, tool_input: dict) -> dict:
    """Validate tool use through ActionGuard."""
    guard = get_guard()

    if tool_name == "Bash":
        command = tool_input.get("command", "")
        result = guard.validate_command(command)
        if not result.allowed:
            return {
                "permissionDecision": "deny",
                "reason": result.reason,
            }

    elif tool_name in ["Write", "Edit"]:
        file_path = tool_input.get("file_path", "")
        result = guard.validate_file_path(file_path)
        if not result.allowed:
            return {
                "permissionDecision": "deny",
                "reason": result.reason,
            }

    return {"permissionDecision": "allow"}


# ── MCP Server Enhancement ───────────────────────────────────────────────

def create_claude_code_mcp_tool() -> dict:
    """Create an MCP tool definition for Claude Code validation."""
    return {
        "name": "slate_claude_code",
        "description": "Validate and manage Claude Code configuration for SLATE",
        "inputSchema": {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["validate", "report", "recommend", "fix"],
                    "description": "Action to perform",
                    "default": "validate",
                },
            },
        },
    }


# ── CLI ──────────────────────────────────────────────────────────────────

def main():
    """CLI entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        description="SLATE Claude Code Validator"
    )
    parser.add_argument(
        "--validate", "-v",
        action="store_true",
        help="Run all validation checks",
    )
    parser.add_argument(
        "--report", "-r",
        action="store_true",
        help="Generate full validation report",
    )
    parser.add_argument(
        "--recommend",
        action="store_true",
        help="Show recommended configuration",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output in JSON format",
    )
    parser.add_argument(
        "--workspace",
        type=Path,
        default=WORKSPACE_ROOT,
        help="Workspace root directory",
    )
    args = parser.parse_args()

    validator = ClaudeCodeValidator(args.workspace)

    if args.recommend:
        config = validator.get_recommended_config()
        if args.json:
            print(json.dumps(config, indent=2))
        else:
            print("Recommended Claude Code Configuration:")
            print("-" * 40)
            for file_name, file_config in config.items():
                print(f"\n{file_name}:")
                print(json.dumps(file_config, indent=2))
        return

    if args.report or not any([args.validate, args.recommend]):
        print(validator.generate_report())
        return

    if args.validate:
        results = validator.validate_all()
        if args.json:
            output = [
                {
                    "valid": r.valid,
                    "component": r.component,
                    "message": r.message,
                    "suggestions": r.suggestions,
                }
                for r in results
            ]
            print(json.dumps(output, indent=2))
        else:
            for r in results:
                print(r)

            passed = sum(1 for r in results if r.valid)
            failed = sum(1 for r in results if not r.valid)
            print(f"\nResults: {passed} passed, {failed} failed")

            if failed > 0:
                sys.exit(1)


if __name__ == "__main__":
    main()
