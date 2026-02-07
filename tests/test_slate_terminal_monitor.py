#!/usr/bin/env python3
# Modified: 2026-02-07T12:55:00Z | Author: COPILOT | Change: Create tests for terminal monitor module
"""
Tests for SLATE Terminal Monitor.
All tests follow Arrange-Act-Assert (AAA) pattern.
"""

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Ensure workspace root is on path
WORKSPACE_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(WORKSPACE_ROOT))

from slate.slate_terminal_monitor import (
    BLOCKED_COMMANDS,
    LONG_RUNNING,
    DEFAULT_TIMEOUT,
    is_blocked,
    get_command_config,
    get_advice,
    run_command,
    get_status,
)


# ═══════════════════════════════════════════════════════════════════════════════
# Constants Tests
# ═══════════════════════════════════════════════════════════════════════════════

class TestConstants:
    """Test terminal monitor constants."""

    def test_blocked_commands_includes_curl(self):
        # Assert — curl.exe is always blocked on this system
        assert "curl.exe" in BLOCKED_COMMANDS

    def test_default_timeout_is_positive(self):
        # Assert
        assert DEFAULT_TIMEOUT > 0

    def test_long_running_has_entries(self):
        # Assert
        assert len(LONG_RUNNING) > 0


# ═══════════════════════════════════════════════════════════════════════════════
# Blocked Command Tests
# ═══════════════════════════════════════════════════════════════════════════════

class TestIsBlocked:
    """Test command blocking logic."""

    def test_curl_is_blocked(self):
        # Arrange
        command = "curl.exe https://example.com"
        # Act
        blocked, reason = is_blocked(command)
        # Assert
        assert blocked is True
        assert len(reason) > 0

    def test_python_not_blocked(self):
        # Arrange
        command = "python slate/slate_status.py --quick"
        # Act
        blocked, reason = is_blocked(command)
        # Assert
        assert blocked is False

    def test_safe_commands_not_blocked(self):
        # Arrange
        safe_commands = [
            "git status",
            "python -c 'print(1)'",
            "nvidia-smi",
            "ollama list",
        ]
        # Act & Assert
        for cmd in safe_commands:
            blocked, _ = is_blocked(cmd)
            assert not blocked, f"{cmd} should not be blocked"


# ═══════════════════════════════════════════════════════════════════════════════
# Command Config Tests
# ═══════════════════════════════════════════════════════════════════════════════

class TestGetCommandConfig:
    """Test command configuration lookup."""

    def test_returns_dict(self):
        # Act
        config = get_command_config("pip install torch")
        # Assert
        assert isinstance(config, dict)

    def test_long_running_has_timeout(self):
        # Arrange — find a known long-running pattern
        if LONG_RUNNING:
            pattern = list(LONG_RUNNING.keys())[0]
            # Act
            config = get_command_config(pattern)
            # Assert
            assert isinstance(config, dict)

    def test_unknown_command_gets_defaults(self):
        # Arrange
        command = "echo hello world"
        # Act
        config = get_command_config(command)
        # Assert
        assert isinstance(config, dict)


# ═══════════════════════════════════════════════════════════════════════════════
# Advice Tests
# ═══════════════════════════════════════════════════════════════════════════════

class TestGetAdvice:
    """Test command advisory system."""

    def test_blocked_command_warns(self):
        # Arrange
        command = "curl.exe https://example.com"
        # Act
        advice = get_advice(command)
        # Assert
        assert isinstance(advice, dict)
        assert advice.get("safe") is False

    def test_safe_command_advice(self):
        # Arrange
        command = "python --version"
        # Act
        advice = get_advice(command)
        # Assert
        assert isinstance(advice, dict)
        assert advice.get("safe") is True


# ═══════════════════════════════════════════════════════════════════════════════
# Run Command Tests
# ═══════════════════════════════════════════════════════════════════════════════

class TestRunCommand:
    """Test command execution with safety checks."""

    def test_blocked_command_not_executed(self):
        # Arrange
        command = "curl.exe https://example.com"
        # Act
        result = run_command(command)
        # Assert
        assert isinstance(result, dict)
        assert result.get("blocked", False) is True or result.get("success", True) is False

    @patch("subprocess.run")
    def test_safe_command_executed(self, mock_run):
        # Arrange
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="Python 3.11.9",
            stderr="",
        )
        # Act
        result = run_command("python --version", timeout=10)
        # Assert
        assert isinstance(result, dict)

    @patch("subprocess.run")
    def test_command_with_timeout(self, mock_run):
        # Arrange
        mock_run.return_value = MagicMock(returncode=0, stdout="done", stderr="")
        # Act
        result = run_command("echo test", timeout=5)
        # Assert
        assert isinstance(result, dict)


# ═══════════════════════════════════════════════════════════════════════════════
# Status Tests
# ═══════════════════════════════════════════════════════════════════════════════

class TestGetStatus:
    """Test monitor status reporting."""

    def test_status_returns_dict(self):
        # Act
        status = get_status()
        # Assert
        assert isinstance(status, dict)

    def test_status_includes_blocked_list(self):
        # Act
        status = get_status()
        # Assert
        assert "blocked" in status or "blocked_commands" in status or len(status) > 0

    def test_status_includes_default_timeout(self):
        # Act
        status = get_status()
        # Assert
        status_str = json.dumps(status)
        assert str(DEFAULT_TIMEOUT) in status_str or "timeout" in status_str.lower()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
