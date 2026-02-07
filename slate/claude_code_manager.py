#!/usr/bin/env python3
# Modified: 2026-02-07T10:30:00Z | Author: COPILOT | Change: Initial creation of Claude Code manager
"""
Claude Code Manager - Configuration and integration management for SLATE.

Provides:
- Settings management (read/write/update)
- Hook system with ActionGuard integration
- Claude Agent SDK integration patterns
- Session management
- MCP server lifecycle management
- Permission system configuration

Based on Claude Agent SDK documentation:
https://platform.claude.com/docs/en/agent-sdk/overview
"""

import asyncio
import json
import logging
import os
import shutil
import subprocess
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Optional

# Add workspace root to path
WORKSPACE_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(WORKSPACE_ROOT))

from slate.action_guard import ActionGuard, ActionResult, get_guard
from slate.claude_code_validator import ClaudeCodeValidator, ValidationResult

logger = logging.getLogger("slate.claude_code_manager")


# ── Configuration Paths ──────────────────────────────────────────────────

def get_user_claude_dir() -> Path:
    """Get user-level Claude Code config directory."""
    if sys.platform == "win32":
        return Path(os.environ.get("USERPROFILE", "")) / ".claude"
    return Path.home() / ".claude"


def get_project_claude_dir(workspace: Path) -> Path:
    """Get project-level Claude Code config directory."""
    return workspace / ".claude"


# ── Hook Types ───────────────────────────────────────────────────────────

@dataclass
class HookResult:
    """Result from a hook execution."""
    permission_decision: str  # "allow", "deny", "ask"
    reason: str = ""
    updated_input: Optional[dict] = None
    system_message: Optional[str] = None
    continue_execution: bool = True


@dataclass
class HookContext:
    """Context passed to hook callbacks."""
    tool_name: str
    tool_input: dict
    tool_use_id: str
    session_id: Optional[str] = None
    workspace: Optional[Path] = None


HookCallback = Callable[[HookContext], HookResult]


# ── Hook Registry ────────────────────────────────────────────────────────

class HookRegistry:
    """
    Registry for Claude Code hooks with ActionGuard integration.

    Provides security-first hook management for SLATE.
    """

    def __init__(self, guard: Optional[ActionGuard] = None):
        self.guard = guard or get_guard()
        self._hooks: dict[str, list[tuple[str, HookCallback]]] = {
            "PreToolUse": [],
            "PostToolUse": [],
            "PostToolUseFailure": [],
            "UserPromptSubmit": [],
            "Stop": [],
            "SubagentStart": [],
            "SubagentStop": [],
            "PreCompact": [],
        }
        self._register_default_hooks()

    def _register_default_hooks(self) -> None:
        """Register SLATE's default security hooks."""
        # PreToolUse: Validate Bash commands
        self.register("PreToolUse", "Bash", self._validate_bash_hook)

        # PreToolUse: Validate file operations
        self.register("PreToolUse", "Write|Edit", self._validate_file_hook)

        # PostToolUse: Audit logging
        self.register("PostToolUse", ".*", self._audit_hook)

    def register(
        self,
        event: str,
        matcher: str,
        callback: HookCallback,
    ) -> None:
        """Register a hook for an event."""
        if event not in self._hooks:
            raise ValueError(f"Unknown hook event: {event}")
        self._hooks[event].append((matcher, callback))
        logger.debug(f"Registered hook for {event} with matcher: {matcher}")

    def unregister(self, event: str, matcher: str) -> bool:
        """Unregister a hook."""
        if event not in self._hooks:
            return False
        original_len = len(self._hooks[event])
        self._hooks[event] = [
            (m, c) for m, c in self._hooks[event] if m != matcher
        ]
        return len(self._hooks[event]) < original_len

    def execute_hooks(
        self,
        event: str,
        context: HookContext,
    ) -> HookResult:
        """Execute all matching hooks for an event."""
        import re

        results = []
        for matcher, callback in self._hooks.get(event, []):
            if re.match(matcher, context.tool_name):
                try:
                    result = callback(context)
                    results.append(result)

                    # Stop on deny
                    if result.permission_decision == "deny":
                        return result
                except Exception as e:
                    logger.error(f"Hook error for {event}/{matcher}: {e}")
                    return HookResult(
                        permission_decision="deny",
                        reason=f"Hook error: {e}",
                    )

        # All hooks passed
        return HookResult(permission_decision="allow")

    def _validate_bash_hook(self, context: HookContext) -> HookResult:
        """Validate Bash commands through ActionGuard."""
        command = context.tool_input.get("command", "")
        result = self.guard.validate_command(command)

        if not result.allowed:
            return HookResult(
                permission_decision="deny",
                reason=f"ActionGuard: {result.reason}",
            )

        return HookResult(permission_decision="allow")

    def _validate_file_hook(self, context: HookContext) -> HookResult:
        """Validate file operations through ActionGuard."""
        file_path = context.tool_input.get("file_path", "")
        result = self.guard.validate_file_path(file_path)

        if not result.allowed:
            return HookResult(
                permission_decision="deny",
                reason=f"ActionGuard: {result.reason}",
            )

        return HookResult(permission_decision="allow")

    def _audit_hook(self, context: HookContext) -> HookResult:
        """Audit log all tool executions."""
        timestamp = datetime.now().isoformat()
        logger.info(
            f"AUDIT: [{timestamp}] {context.tool_name} "
            f"session={context.session_id} "
            f"tool_use_id={context.tool_use_id}"
        )
        return HookResult(permission_decision="allow")


# ── Claude Code Manager ──────────────────────────────────────────────────

class ClaudeCodeManager:
    """
    Manages Claude Code configuration and integration for SLATE.

    Provides:
    - Settings management
    - Hook lifecycle
    - MCP server management
    - Permission configuration
    - Session tracking
    """

    def __init__(self, workspace: Optional[Path] = None):
        self.workspace = workspace or WORKSPACE_ROOT
        self.user_dir = get_user_claude_dir()
        self.project_dir = get_project_claude_dir(self.workspace)
        self.hook_registry = HookRegistry()
        self.validator = ClaudeCodeValidator(self.workspace)
        self._sessions: dict[str, dict] = {}

    # ── Settings Management ──────────────────────────────────────────────

    def get_settings(self, level: str = "project") -> dict:
        """Get settings at specified level (project or user)."""
        if level == "project":
            settings_path = self.project_dir / "settings.json"
        else:
            settings_path = self.user_dir / "settings.json"

        if settings_path.exists():
            try:
                with open(settings_path) as f:
                    return json.load(f)
            except json.JSONDecodeError:
                return {}
        return {}

    def update_settings(
        self,
        updates: dict,
        level: str = "project",
        merge: bool = True,
    ) -> bool:
        """Update settings at specified level."""
        if level == "project":
            settings_path = self.project_dir / "settings.json"
            settings_path.parent.mkdir(parents=True, exist_ok=True)
        else:
            settings_path = self.user_dir / "settings.json"
            settings_path.parent.mkdir(parents=True, exist_ok=True)

        current = self.get_settings(level) if merge else {}
        current = self._deep_merge(current, updates)

        try:
            with open(settings_path, "w") as f:
                json.dump(current, f, indent=2)
            logger.info(f"Updated settings at {settings_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to update settings: {e}")
            return False

    def _deep_merge(self, base: dict, updates: dict) -> dict:
        """Deep merge two dictionaries."""
        result = base.copy()
        for key, value in updates.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._deep_merge(result[key], value)
            else:
                result[key] = value
        return result

    # ── Permission Management ────────────────────────────────────────────

    def get_permissions(self) -> dict:
        """Get current permission configuration."""
        local_settings_path = self.project_dir / "settings.local.json"
        if local_settings_path.exists():
            try:
                with open(local_settings_path) as f:
                    data = json.load(f)
                    return data.get("permissions", {})
            except json.JSONDecodeError:
                return {}
        return {}

    def add_permission_rule(
        self,
        rule: str,
        rule_type: str = "allow",
    ) -> bool:
        """Add a permission rule."""
        local_settings_path = self.project_dir / "settings.local.json"
        local_settings_path.parent.mkdir(parents=True, exist_ok=True)

        current = {}
        if local_settings_path.exists():
            try:
                with open(local_settings_path) as f:
                    current = json.load(f)
            except json.JSONDecodeError:
                pass

        if "permissions" not in current:
            current["permissions"] = {}
        if rule_type not in current["permissions"]:
            current["permissions"][rule_type] = []

        if rule not in current["permissions"][rule_type]:
            current["permissions"][rule_type].append(rule)

            try:
                with open(local_settings_path, "w") as f:
                    json.dump(current, f, indent=2)
                logger.info(f"Added permission rule: {rule_type} {rule}")
                return True
            except Exception as e:
                logger.error(f"Failed to add permission rule: {e}")
                return False
        return True

    def remove_permission_rule(
        self,
        rule: str,
        rule_type: str = "allow",
    ) -> bool:
        """Remove a permission rule."""
        local_settings_path = self.project_dir / "settings.local.json"
        if not local_settings_path.exists():
            return False

        try:
            with open(local_settings_path) as f:
                current = json.load(f)
        except json.JSONDecodeError:
            return False

        if "permissions" in current and rule_type in current["permissions"]:
            if rule in current["permissions"][rule_type]:
                current["permissions"][rule_type].remove(rule)

                with open(local_settings_path, "w") as f:
                    json.dump(current, f, indent=2)
                logger.info(f"Removed permission rule: {rule_type} {rule}")
                return True
        return False

    # ── MCP Server Management ────────────────────────────────────────────

    def get_mcp_servers(self) -> dict:
        """Get configured MCP servers."""
        plugin_json = self.workspace / ".claude-plugin" / "plugin.json"
        if plugin_json.exists():
            try:
                with open(plugin_json) as f:
                    data = json.load(f)
                    return data.get("mcpServers", {})
            except json.JSONDecodeError:
                return {}
        return {}

    def add_mcp_server(
        self,
        name: str,
        command: str,
        args: list[str],
        env: Optional[dict] = None,
    ) -> bool:
        """Add an MCP server configuration."""
        plugin_json = self.workspace / ".claude-plugin" / "plugin.json"
        plugin_json.parent.mkdir(parents=True, exist_ok=True)

        current = {}
        if plugin_json.exists():
            try:
                with open(plugin_json) as f:
                    current = json.load(f)
            except json.JSONDecodeError:
                pass

        if "mcpServers" not in current:
            current["mcpServers"] = {}

        current["mcpServers"][name] = {
            "command": command,
            "args": args,
        }
        if env:
            current["mcpServers"][name]["env"] = env

        try:
            with open(plugin_json, "w") as f:
                json.dump(current, f, indent=2)
            logger.info(f"Added MCP server: {name}")
            return True
        except Exception as e:
            logger.error(f"Failed to add MCP server: {e}")
            return False

    def test_mcp_server(self, name: str) -> dict:
        """Test an MCP server connection."""
        servers = self.get_mcp_servers()
        if name not in servers:
            return {"success": False, "error": f"Server not found: {name}"}

        config = servers[name]
        command = config.get("command", "")
        args = config.get("args", [])

        # Expand variables
        command = command.replace("${CLAUDE_PLUGIN_ROOT}", str(self.workspace))
        args = [a.replace("${CLAUDE_PLUGIN_ROOT}", str(self.workspace)) for a in args]

        # Test command exists
        if not Path(command).exists():
            return {"success": False, "error": f"Command not found: {command}"}

        # Test script exists
        for arg in args:
            if arg.endswith(".py") and not Path(arg).exists():
                return {"success": False, "error": f"Script not found: {arg}"}

        return {"success": True, "command": command, "args": args}

    # ── Hook Management ──────────────────────────────────────────────────

    def register_hook(
        self,
        event: str,
        matcher: str,
        callback: HookCallback,
    ) -> None:
        """Register a hook with the hook registry."""
        self.hook_registry.register(event, matcher, callback)

    def execute_hooks(
        self,
        event: str,
        tool_name: str,
        tool_input: dict,
        tool_use_id: str = "",
        session_id: Optional[str] = None,
    ) -> HookResult:
        """Execute hooks for a tool use."""
        context = HookContext(
            tool_name=tool_name,
            tool_input=tool_input,
            tool_use_id=tool_use_id,
            session_id=session_id,
            workspace=self.workspace,
        )
        return self.hook_registry.execute_hooks(event, context)

    # ── Session Management ───────────────────────────────────────────────

    def create_session(self, session_id: Optional[str] = None) -> str:
        """Create a new session."""
        import uuid
        session_id = session_id or str(uuid.uuid4())
        self._sessions[session_id] = {
            "id": session_id,
            "created_at": datetime.now().isoformat(),
            "tool_uses": [],
            "context": {},
        }
        logger.info(f"Created session: {session_id}")
        return session_id

    def get_session(self, session_id: str) -> Optional[dict]:
        """Get session data."""
        return self._sessions.get(session_id)

    def update_session(self, session_id: str, updates: dict) -> bool:
        """Update session data."""
        if session_id not in self._sessions:
            return False
        self._sessions[session_id].update(updates)
        return True

    def record_tool_use(
        self,
        session_id: str,
        tool_name: str,
        tool_input: dict,
        tool_output: str,
    ) -> None:
        """Record a tool use in the session."""
        if session_id in self._sessions:
            self._sessions[session_id]["tool_uses"].append({
                "tool": tool_name,
                "input": tool_input,
                "output": tool_output,
                "timestamp": datetime.now().isoformat(),
            })

    # ── Validation ───────────────────────────────────────────────────────

    def validate(self) -> list[ValidationResult]:
        """Run validation checks."""
        return self.validator.validate_all()

    def generate_report(self) -> str:
        """Generate validation report."""
        return self.validator.generate_report()

    # ── Claude Agent SDK Patterns ────────────────────────────────────────

    def get_agent_options(
        self,
        allowed_tools: Optional[list[str]] = None,
        permission_mode: str = "acceptEdits",
        system_prompt: Optional[str] = None,
        model: str = "claude-sonnet-4-5-20250929",
    ) -> dict:
        """
        Generate Claude Agent SDK options for SLATE integration.

        Returns a configuration dict compatible with ClaudeAgentOptions.
        """
        # Default allowed tools for SLATE
        default_tools = [
            "Read", "Write", "Edit", "Bash", "Glob", "Grep",
            "Task", "TodoWrite", "AskUserQuestion",
        ]

        # Add SLATE MCP tools
        mcp_tools = [
            "mcp__slate__slate_status",
            "mcp__slate__slate_workflow",
            "mcp__slate__slate_orchestrator",
            "mcp__slate__slate_runner",
            "mcp__slate__slate_ai",
            "mcp__slate__slate_runtime",
            "mcp__slate__slate_hardware",
            "mcp__slate__slate_benchmark",
            "mcp__slate__slate_gpu",
        ]

        tools = (allowed_tools or default_tools) + mcp_tools

        # Load CLAUDE.md for system prompt
        claude_md = self.workspace / "CLAUDE.md"
        if system_prompt is None and claude_md.exists():
            with open(claude_md) as f:
                system_prompt = f.read()

        return {
            "allowed_tools": tools,
            "permission_mode": permission_mode,
            "system_prompt": system_prompt,
            "model": model,
            "mcp_servers": self.get_mcp_servers(),
            "setting_sources": ["project"],
            "hooks": {
                "PreToolUse": self._create_pretool_hook_config(),
                "PostToolUse": self._create_posttool_hook_config(),
            },
        }

    def _create_pretool_hook_config(self) -> list[dict]:
        """Create PreToolUse hook configuration."""
        return [
            {
                "matcher": "Bash",
                "description": "Validate commands through ActionGuard",
            },
            {
                "matcher": "Write|Edit",
                "description": "Validate file paths for safety",
            },
        ]

    def _create_posttool_hook_config(self) -> list[dict]:
        """Create PostToolUse hook configuration."""
        return [
            {
                "matcher": ".*",
                "description": "Audit log all tool executions",
            },
        ]

    # ── Status ───────────────────────────────────────────────────────────

    def get_status(self) -> dict:
        """Get comprehensive status."""
        validation_results = self.validate()

        return {
            "workspace": str(self.workspace),
            "user_dir": str(self.user_dir),
            "project_dir": str(self.project_dir),
            "settings": {
                "project": self.get_settings("project"),
                "user": self.get_settings("user"),
            },
            "permissions": self.get_permissions(),
            "mcp_servers": self.get_mcp_servers(),
            "validation": {
                "passed": sum(1 for r in validation_results if r.valid),
                "failed": sum(1 for r in validation_results if not r.valid),
                "results": [
                    {
                        "valid": r.valid,
                        "component": r.component,
                        "message": r.message,
                    }
                    for r in validation_results
                ],
            },
            "active_sessions": len(self._sessions),
            "hooks_registered": sum(
                len(hooks) for hooks in self.hook_registry._hooks.values()
            ),
        }


# ── Factory Functions ────────────────────────────────────────────────────

_manager_instance: Optional[ClaudeCodeManager] = None


def get_manager(workspace: Optional[Path] = None) -> ClaudeCodeManager:
    """Get or create the singleton manager instance."""
    global _manager_instance
    if _manager_instance is None:
        _manager_instance = ClaudeCodeManager(workspace)
    return _manager_instance


def reset_manager() -> None:
    """Reset the manager instance."""
    global _manager_instance
    _manager_instance = None


# ── CLI ──────────────────────────────────────────────────────────────────

def main():
    """CLI entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        description="SLATE Claude Code Manager"
    )
    parser.add_argument(
        "--status",
        action="store_true",
        help="Show Claude Code integration status",
    )
    parser.add_argument(
        "--validate",
        action="store_true",
        help="Validate configuration",
    )
    parser.add_argument(
        "--report",
        action="store_true",
        help="Generate validation report",
    )
    parser.add_argument(
        "--test-mcp",
        metavar="NAME",
        help="Test an MCP server",
    )
    parser.add_argument(
        "--add-permission",
        metavar="RULE",
        help="Add a permission rule",
    )
    parser.add_argument(
        "--permission-type",
        choices=["allow", "deny"],
        default="allow",
        help="Permission type (default: allow)",
    )
    parser.add_argument(
        "--agent-options",
        action="store_true",
        help="Show recommended Agent SDK options",
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

    manager = ClaudeCodeManager(args.workspace)

    if args.test_mcp:
        result = manager.test_mcp_server(args.test_mcp)
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            if result["success"]:
                print(f"MCP server '{args.test_mcp}' OK")
                print(f"  Command: {result['command']}")
                print(f"  Args: {result['args']}")
            else:
                print(f"MCP server '{args.test_mcp}' FAILED")
                print(f"  Error: {result['error']}")
        return

    if args.add_permission:
        success = manager.add_permission_rule(
            args.add_permission,
            args.permission_type,
        )
        if success:
            print(f"Added {args.permission_type} rule: {args.add_permission}")
        else:
            print(f"Failed to add rule")
            sys.exit(1)
        return

    if args.agent_options:
        options = manager.get_agent_options()
        # Remove system_prompt for display (too long)
        display_options = {k: v for k, v in options.items() if k != "system_prompt"}
        display_options["system_prompt"] = "(loaded from CLAUDE.md)"
        if args.json:
            print(json.dumps(display_options, indent=2))
        else:
            print("Recommended Claude Agent SDK Options:")
            print("-" * 40)
            print(json.dumps(display_options, indent=2))
        return

    if args.report:
        print(manager.generate_report())
        return

    if args.validate:
        results = manager.validate()
        if args.json:
            output = [
                {
                    "valid": r.valid,
                    "component": r.component,
                    "message": r.message,
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
        return

    # Default: status
    status = manager.get_status()
    if args.json:
        print(json.dumps(status, indent=2))
    else:
        print("=" * 60)
        print("  SLATE Claude Code Integration Status")
        print("=" * 60)
        print(f"\n  Workspace: {status['workspace']}")
        print(f"  User Dir:  {status['user_dir']}")
        print(f"  Project:   {status['project_dir']}")

        print("\n  MCP Servers:")
        for name in status["mcp_servers"]:
            print(f"    - {name}")

        print("\n  Permissions:")
        perms = status["permissions"]
        for rule in perms.get("allow", []):
            print(f"    [ALLOW] {rule}")
        for rule in perms.get("deny", []):
            print(f"    [DENY] {rule}")

        print("\n  Validation:")
        v = status["validation"]
        print(f"    Passed: {v['passed']}, Failed: {v['failed']}")

        print(f"\n  Active Sessions: {status['active_sessions']}")
        print(f"  Hooks Registered: {status['hooks_registered']}")
        print("=" * 60)


if __name__ == "__main__":
    main()
