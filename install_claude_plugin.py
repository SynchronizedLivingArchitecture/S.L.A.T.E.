#!/usr/bin/env python3
"""
SLATE Claude Code Plugin Installer

This script registers the SLATE plugin with Claude Code, enabling:
- /slate commands for orchestration
- /slate-status for system status
- /slate-workflow for task management
- /slate-runner for GitHub Actions runner management
- MCP server integration for tool access

Usage:
    python install_claude_plugin.py [--uninstall]
"""

import argparse
import json
import os
import shutil
import sys
from pathlib import Path


def get_claude_dir() -> Path:
    """Get the Claude Code configuration directory."""
    if sys.platform == "win32":
        claude_dir = Path(os.environ.get("USERPROFILE", "")) / ".claude"
    else:
        claude_dir = Path.home() / ".claude"
    return claude_dir


def get_workspace_root() -> Path:
    """Get the SLATE workspace root."""
    return Path(__file__).parent.resolve()


def validate_plugin_structure(workspace: Path) -> bool:
    """Validate that the plugin structure is correct."""
    required_files = [
        workspace / ".claude-plugin" / "plugin.json",
    ]

    for f in required_files:
        if not f.exists():
            print(f"ERROR: Missing required file: {f}")
            return False

    # Validate plugin.json
    try:
        with open(workspace / ".claude-plugin" / "plugin.json") as f:
            plugin_data = json.load(f)
            if "name" not in plugin_data:
                print("ERROR: plugin.json missing 'name' field")
                return False
    except json.JSONDecodeError as e:
        print(f"ERROR: Invalid JSON in plugin.json: {e}")
        return False

    return True


def install_plugin(workspace: Path, claude_dir: Path) -> bool:
    """Install the SLATE plugin to Claude Code."""
    plugins_dir = claude_dir / "plugins" / "installed"
    plugins_dir.mkdir(parents=True, exist_ok=True)

    # Read plugin name
    with open(workspace / ".claude-plugin" / "plugin.json") as f:
        plugin_data = json.load(f)
        plugin_name = plugin_data.get("name", "slate-sdk")

    # Create symlink or copy plugin directory
    target_dir = plugins_dir / plugin_name

    if target_dir.exists():
        print(f"Plugin '{plugin_name}' already installed. Removing old version...")
        if target_dir.is_symlink():
            target_dir.unlink()
        else:
            shutil.rmtree(target_dir)

    # Create symlink (preferred) or copy
    try:
        target_dir.symlink_to(workspace, target_is_directory=True)
        print(f"Created symlink: {target_dir} -> {workspace}")
    except OSError:
        # Symlink failed (Windows without dev mode), copy instead
        print("Symlink failed, copying plugin files...")
        shutil.copytree(workspace, target_dir, dirs_exist_ok=True)
        print(f"Copied plugin to: {target_dir}")

    # Update Claude settings to include plugin
    settings_file = claude_dir / "settings.json"
    settings = {}

    if settings_file.exists():
        try:
            with open(settings_file) as f:
                settings = json.load(f)
        except json.JSONDecodeError:
            pass

    # Add plugin to enabled plugins
    if "plugins" not in settings:
        settings["plugins"] = {}
    if "enabled" not in settings["plugins"]:
        settings["plugins"]["enabled"] = []

    if plugin_name not in settings["plugins"]["enabled"]:
        settings["plugins"]["enabled"].append(plugin_name)

    # Write updated settings
    with open(settings_file, "w") as f:
        json.dump(settings, f, indent=2)

    print(f"\nPlugin '{plugin_name}' installed successfully!")
    print("\nAvailable commands:")
    print("  /slate [start|stop|status]  - Manage SLATE orchestrator")
    print("  /slate-status               - Check system status")
    print("  /slate-workflow             - Manage task queue")
    print("  /slate-runner               - Manage GitHub runner")
    print("  /slate-help                 - Show all commands")

    return True


def uninstall_plugin(workspace: Path, claude_dir: Path) -> bool:
    """Uninstall the SLATE plugin from Claude Code."""
    # Read plugin name
    with open(workspace / ".claude-plugin" / "plugin.json") as f:
        plugin_data = json.load(f)
        plugin_name = plugin_data.get("name", "slate-sdk")

    plugins_dir = claude_dir / "plugins" / "installed"
    target_dir = plugins_dir / plugin_name

    if target_dir.exists():
        if target_dir.is_symlink():
            target_dir.unlink()
        else:
            shutil.rmtree(target_dir)
        print(f"Removed plugin directory: {target_dir}")

    # Update settings
    settings_file = claude_dir / "settings.json"
    if settings_file.exists():
        try:
            with open(settings_file) as f:
                settings = json.load(f)

            if "plugins" in settings and "enabled" in settings["plugins"]:
                if plugin_name in settings["plugins"]["enabled"]:
                    settings["plugins"]["enabled"].remove(plugin_name)

                    with open(settings_file, "w") as f:
                        json.dump(settings, f, indent=2)
        except json.JSONDecodeError:
            pass

    print(f"Plugin '{plugin_name}' uninstalled successfully!")
    return True


def main():
    parser = argparse.ArgumentParser(
        description="Install SLATE plugin for Claude Code"
    )
    parser.add_argument(
        "--uninstall",
        action="store_true",
        help="Uninstall the plugin instead of installing"
    )
    parser.add_argument(
        "--validate",
        action="store_true",
        help="Only validate the plugin structure"
    )
    args = parser.parse_args()

    workspace = get_workspace_root()
    claude_dir = get_claude_dir()

    print(f"SLATE Workspace: {workspace}")
    print(f"Claude Config: {claude_dir}")
    print()

    # Validate plugin structure
    if not validate_plugin_structure(workspace):
        print("\nPlugin validation failed!")
        sys.exit(1)

    print("Plugin structure validated successfully!")

    if args.validate:
        sys.exit(0)

    if args.uninstall:
        if not uninstall_plugin(workspace, claude_dir):
            sys.exit(1)
    else:
        if not install_plugin(workspace, claude_dir):
            sys.exit(1)

    print("\nRestart Claude Code for changes to take effect.")


if __name__ == "__main__":
    main()
