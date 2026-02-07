# Modified: 2026-02-07T13:30:00Z | Author: COPILOT | Change: Add test coverage for action_guard module
"""
Tests for slate/action_guard.py — ActionGuard security enforcement,
blocked patterns, rate limiting, K8s manifest validation, container images.
"""

import pytest

from slate.action_guard import (
    ActionGuard,
    ActionResult,
    RateTracker,
    BLOCKED_PATTERNS,
    BLOCKED_DOMAINS,
    ALLOWED_HOSTS,
    K8S_BLOCKED_PATTERNS,
    TRUSTED_REGISTRIES,
    RATE_LIMITS,
    get_guard,
    validate_action,
    validate_command,
    is_safe,
)


# ── ActionResult & RateTracker ──────────────────────────────────────────


class TestActionResult:
    """Tests for ActionResult dataclass."""

    def test_allowed_result_str(self):
        r = ActionResult(allowed=True, action="test", reason="OK")
        assert "[ALLOWED]" in str(r)

    def test_blocked_result_str(self):
        r = ActionResult(allowed=False, action="test", reason="Bad")
        assert "[BLOCKED]" in str(r)


class TestRateTracker:
    """Tests for RateTracker class."""

    def test_empty_tracker(self):
        tracker = RateTracker()
        assert tracker.count_recent() == 0

    def test_add_and_count(self):
        tracker = RateTracker()
        tracker.add()
        tracker.add()
        assert tracker.count_recent() == 2


# ── ActionGuard Core ────────────────────────────────────────────────────


class TestActionGuardValidation:
    """Tests for ActionGuard.validate_action and related methods."""

    @pytest.fixture
    def guard(self):
        return ActionGuard()

    def test_safe_command_allowed(self, guard):
        result = guard.validate_action("command_exec", "python slate/slate_status.py --quick")
        assert result.allowed is True

    def test_eval_blocked(self, guard):
        result = guard.validate_action("command_exec", 'eval("dangerous")')
        assert result.allowed is False
        assert "Blocked pattern" in result.reason

    def test_rm_rf_blocked(self, guard):
        result = guard.validate_action("command_exec", "rm -rf /")
        assert result.allowed is False

    def test_exec_os_blocked(self, guard):
        result = guard.validate_action("command_exec", 'exec(os.system("whoami"))')
        assert result.allowed is False

    def test_base64_decode_blocked(self, guard):
        result = guard.validate_action("command_exec", "base64.b64decode(payload)")
        assert result.allowed is False

    def test_zero_bind_blocked(self, guard):
        result = guard.validate_action("network_request", "http://0.0.0.0:8080")
        assert result.allowed is False
        assert "Blocked" in result.reason

    def test_localhost_allowed(self, guard):
        result = guard.validate_action("network_request", "http://127.0.0.1:8080/api")
        assert result.allowed is True

    def test_external_domain_blocked(self, guard):
        result = guard.validate_action("network_request", "https://api.openai.com/v1/chat")
        assert result.allowed is False
        assert "Blocked external domain" in result.reason

    def test_github_api_allowed(self, guard):
        result = guard.validate_action("network_request", "https://api.github.com/repos")
        assert result.allowed is True


# ── Host Validation ─────────────────────────────────────────────────────


class TestHostValidation:
    """Tests for ActionGuard.validate_host."""

    @pytest.fixture
    def guard(self):
        return ActionGuard()

    def test_localhost_allowed(self, guard):
        result = guard.validate_host("127.0.0.1")
        assert result.allowed is True

    def test_localhost_name_allowed(self, guard):
        result = guard.validate_host("localhost")
        assert result.allowed is True

    def test_github_domain_allowed(self, guard):
        result = guard.validate_host("api.github.com")
        assert result.allowed is True

    def test_random_host_blocked(self, guard):
        result = guard.validate_host("evil-server.example.com")
        assert result.allowed is False


# ── File Path Validation ────────────────────────────────────────────────


class TestFilePathValidation:
    """Tests for ActionGuard.validate_file_path."""

    @pytest.fixture
    def guard(self):
        return ActionGuard()

    def test_safe_path_allowed(self, guard):
        result = guard.validate_file_path("slate/slate_status.py")
        assert result.allowed is True

    def test_etc_passwd_blocked(self, guard):
        result = guard.validate_file_path("/etc/passwd")
        assert result.allowed is False

    def test_system32_blocked(self, guard):
        result = guard.validate_file_path("C:\\Windows\\System32\\cmd.exe")
        assert result.allowed is False


# ── K8s Manifest Validation ─────────────────────────────────────────────


class TestK8sManifestValidation:
    """Tests for ActionGuard.validate_k8s_manifest."""

    @pytest.fixture
    def guard(self):
        return ActionGuard()

    def test_safe_manifest_allowed(self, guard):
        manifest = "allowPrivilegeEscalation: false\nrunAsNonRoot: true"
        result = guard.validate_k8s_manifest(manifest)
        assert result.allowed is True

    def test_privileged_blocked(self, guard):
        result = guard.validate_k8s_manifest("privileged: true")
        assert result.allowed is False

    def test_host_network_blocked(self, guard):
        result = guard.validate_k8s_manifest("hostNetwork: true")
        assert result.allowed is False

    def test_nodeport_blocked(self, guard):
        result = guard.validate_k8s_manifest("type: NodePort")
        assert result.allowed is False

    def test_clusterip_allowed(self, guard):
        result = guard.validate_k8s_manifest("type: ClusterIP")
        assert result.allowed is True

    def test_root_user_blocked(self, guard):
        result = guard.validate_k8s_manifest("runAsUser: 0")
        assert result.allowed is False

    def test_nonroot_user_allowed(self, guard):
        result = guard.validate_k8s_manifest("runAsUser: 1000\nrunAsNonRoot: true")
        assert result.allowed is True


# ── Container Image Validation ──────────────────────────────────────────


class TestContainerImageValidation:
    """Tests for ActionGuard.validate_container_image."""

    @pytest.fixture
    def guard(self):
        return ActionGuard()

    def test_ghcr_slate_allowed(self, guard):
        result = guard.validate_container_image("ghcr.io/synchronizedlivingarchitecture/slate:latest-gpu")
        assert result.allowed is True

    def test_ollama_allowed(self, guard):
        result = guard.validate_container_image("ollama/ollama:latest")
        assert result.allowed is True

    def test_nvidia_cuda_allowed(self, guard):
        result = guard.validate_container_image("nvidia/cuda:12.4.1-runtime-ubuntu22.04")
        assert result.allowed is True

    def test_untrusted_registry_blocked(self, guard):
        result = guard.validate_container_image("evil-registry.io/malware:latest")
        assert result.allowed is False


# ── Audit Log ───────────────────────────────────────────────────────────


class TestAuditLog:
    """Tests for audit log functionality."""

    def test_audit_log_records(self):
        guard = ActionGuard()
        guard.validate_action("command_exec", "python test.py")
        guard.validate_action("command_exec", 'eval("bad")')
        log = guard.get_audit_log()
        assert len(log) == 2
        assert log[0].allowed is True
        assert log[1].allowed is False

    def test_blocked_count(self):
        guard = ActionGuard()
        guard.validate_action("command_exec", "python test.py")
        guard.validate_action("command_exec", 'eval("bad")')
        assert guard.get_blocked_count() == 1


# ── Module-level functions ──────────────────────────────────────────────


class TestModuleFunctions:
    """Tests for module-level convenience functions."""

    def test_is_safe_returns_bool(self):
        assert is_safe("command_exec", "python test.py") is True
        assert is_safe("command_exec", 'eval("x")') is False

    def test_validate_command_shorthand(self):
        result = validate_command("python slate/slate_status.py")
        assert result.allowed is True

    def test_validate_action_function(self):
        result = validate_action("network_request", "http://127.0.0.1:8080")
        assert result.allowed is True
