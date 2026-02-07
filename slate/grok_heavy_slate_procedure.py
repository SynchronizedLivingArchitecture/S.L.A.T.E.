# Modified: 2026-02-07T09:00:00Z | Author: COPILOT | Change: Create Grok Heavy SLATE Procedure for security audits
"""
Grok Heavy SLATE Procedure
===========================
Automated security audit procedure using LLM analysis for vulnerability detection.

This procedure loads code from the repository, generates security-focused prompts,
sends them to a local LLM for analysis, parses responses, and reports findings.

Architecture:
    - **Primary backend**: Local Ollama (slate-coder 12B, slate-planner 7B)
    - **Fallback**: slate-fast 3B for classification/triage
    - **External APIs**: BLOCKED by ActionGuard (local-first enforcement)

    If xAI Grok 4 Heavy API were ever allow-listed in ActionGuard, the
    analysis_backend() method can be extended to route to it. Until then,
    all inference runs locally on the dual-GPU system.

Security constraints:
    - Runs entirely LOCAL (127.0.0.1)
    - No external API calls (ActionGuard enforced)
    - No secrets in prompts or logs
    - No eval()/exec() usage
    - Results stored in local audit log only

Usage:
    python slate/grok_heavy_slate_procedure.py --status           # Show procedure status
    python slate/grok_heavy_slate_procedure.py --audit            # Run full security audit
    python slate/grok_heavy_slate_procedure.py --audit-file <path> # Audit a single file
    python slate/grok_heavy_slate_procedure.py --audit-k8s        # Audit K8s manifests
    python slate/grok_heavy_slate_procedure.py --report           # Show latest audit report
"""

import argparse
import json
import logging
import os
import re
import subprocess
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

# Ensure workspace root is on path
WORKSPACE_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(WORKSPACE_ROOT))

from slate.action_guard import ActionGuard, ActionResult
from slate.pii_scanner import scan_text, redact_text, scan_k8s_manifest
from slate.sdk_source_guard import SDKSourceGuard

logger = logging.getLogger("slate.grok_heavy")

# ── Configuration ───────────────────────────────────────────────────────

OLLAMA_HOST = os.environ.get("OLLAMA_HOST", "http://127.0.0.1:11434")

# Models for different analysis tasks (local Ollama)
ANALYSIS_MODELS = {
    "code_audit": "slate-coder",       # 12B — deep code analysis
    "security_plan": "slate-planner",  # 7B — security planning & recommendations
    "triage": "slate-fast",            # 3B — quick classification
}

# Fallback if SLATE custom models not available
FALLBACK_MODELS = {
    "code_audit": "mistral-nemo",
    "security_plan": "mistral",
    "triage": "llama3.2",
}

# Files to skip during audit
SKIP_PATTERNS = [
    r"\.git/",
    r"__pycache__/",
    r"\.venv/",
    r"node_modules/",
    r"\.egg-info/",
    r"actions-runner/",
    r"actions-runner-\d+/",
    r"_temp/",
    r"\.pyc$",
    r"\.pyo$",
    r"\.so$",
    r"\.dll$",
]

# Security audit prompt templates
AUDIT_PROMPTS = {
    "code_vulnerability": """Analyze this Python code for security vulnerabilities using SLATE security protocols.

SLATE Security Rules:
1. ALL network bindings must use 127.0.0.1 (never 0.0.0.0)
2. No eval(), exec(), __import__() usage
3. No hardcoded secrets, tokens, or credentials
4. No subprocess.call with shell=True
5. No os.system() calls
6. File operations must use encoding='utf-8'
7. No external paid API calls (local-first enforcement)
8. Base64 decode of untrusted data is blocked

File: {file_path}
```python
{code}
```

Report ONLY actual vulnerabilities found. For each:
- Severity: CRITICAL / HIGH / MEDIUM / LOW
- Line number (approximate)
- Description of the vulnerability
- Recommended fix

If no vulnerabilities found, state "No vulnerabilities detected."
""",

    "k8s_security": """Analyze this Kubernetes manifest for security issues using SLATE security protocols.

SLATE K8s Security Rules:
1. No privileged containers
2. No hostNetwork, hostPID, hostIPC
3. runAsNonRoot: true required
4. allowPrivilegeEscalation: false required
5. Drop ALL capabilities
6. readOnlyRootFilesystem preferred
7. Services should use ClusterIP (not NodePort/LoadBalancer)
8. automountServiceAccountToken: false unless needed
9. Resource limits must be set
10. No hardcoded secrets in env vars

File: {file_path}
```yaml
{code}
```

Report ONLY actual security issues found. For each:
- Severity: CRITICAL / HIGH / MEDIUM / LOW
- Line number (approximate)
- Description
- Recommended fix
""",

    "docker_security": """Analyze this Dockerfile for security issues.

Security Rules:
1. Use specific image tags (not :latest in production)
2. Run as non-root user
3. Minimize installed packages
4. No secrets in build args or ENV
5. Use multi-stage builds where possible
6. HEALTHCHECK should not use curl (use Python urllib)

File: {file_path}
```dockerfile
{code}
```

Report vulnerabilities with severity, description, and fix.
""",
}

# Audit report storage
AUDIT_LOG_DIR = WORKSPACE_ROOT / "slate_logs" / "security_audits"


# ── Data Classes ────────────────────────────────────────────────────────

@dataclass
class Finding:
    """A security finding from the audit."""
    severity: str  # CRITICAL, HIGH, MEDIUM, LOW, INFO
    file_path: str
    line_number: int
    description: str
    recommendation: str
    source: str  # "llm_analysis", "action_guard", "pii_scanner", "sdk_guard"
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict:
        return {
            "severity": self.severity,
            "file": self.file_path,
            "line": self.line_number,
            "description": self.description,
            "recommendation": self.recommendation,
            "source": self.source,
            "timestamp": self.timestamp,
        }


@dataclass
class AuditReport:
    """Complete security audit report."""
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    findings: list[Finding] = field(default_factory=list)
    files_scanned: int = 0
    duration_seconds: float = 0.0
    model_used: str = ""
    status: str = "pending"  # pending, running, completed, failed

    def to_dict(self) -> dict:
        return {
            "timestamp": self.timestamp,
            "status": self.status,
            "files_scanned": self.files_scanned,
            "duration_seconds": round(self.duration_seconds, 2),
            "model_used": self.model_used,
            "summary": {
                "total": len(self.findings),
                "critical": sum(1 for f in self.findings if f.severity == "CRITICAL"),
                "high": sum(1 for f in self.findings if f.severity == "HIGH"),
                "medium": sum(1 for f in self.findings if f.severity == "MEDIUM"),
                "low": sum(1 for f in self.findings if f.severity == "LOW"),
                "info": sum(1 for f in self.findings if f.severity == "INFO"),
            },
            "findings": [f.to_dict() for f in self.findings],
        }

    def save(self, path: Optional[Path] = None) -> Path:
        """Save audit report to JSON file."""
        if path is None:
            AUDIT_LOG_DIR.mkdir(parents=True, exist_ok=True)
            ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
            path = AUDIT_LOG_DIR / f"audit_{ts}.json"

        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=2)

        return path


# ── Grok Heavy Procedure ───────────────────────────────────────────────

class GrokHeavySlateProcedure:
    """
    Automated security audit procedure using local LLM analysis.

    Combines:
    1. Static analysis via ActionGuard, PII Scanner, SDK Source Guard
    2. LLM-powered deep code analysis via local Ollama models
    3. K8s manifest security scanning
    4. Unified reporting with severity classification

    All analysis runs locally. No external API calls.
    """

    def __init__(self):
        self.action_guard = ActionGuard()
        self.sdk_guard = SDKSourceGuard()
        self._ollama_available: Optional[bool] = None
        self._available_models: list[str] = []

    # ── Ollama Backend ──────────────────────────────────────────────────

    def _check_ollama(self) -> bool:
        """Check if Ollama is running and accessible."""
        if self._ollama_available is not None:
            return self._ollama_available

        try:
            import urllib.request
            req = urllib.request.Request(f"{OLLAMA_HOST}/api/tags", method="GET")
            with urllib.request.urlopen(req, timeout=5) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                self._available_models = [m["name"].split(":")[0] for m in data.get("models", [])]
                self._ollama_available = True
        except Exception:
            self._ollama_available = False
            self._available_models = []

        return self._ollama_available

    def _select_model(self, task: str) -> Optional[str]:
        """Select the best available model for a task."""
        if not self._check_ollama():
            return None

        # Try SLATE custom model first
        preferred = ANALYSIS_MODELS.get(task)
        if preferred and preferred in self._available_models:
            return preferred

        # Try fallback
        fallback = FALLBACK_MODELS.get(task)
        if fallback and fallback in self._available_models:
            return fallback

        # Try any available model
        if self._available_models:
            return self._available_models[0]

        return None

    def _llm_analyze(self, prompt: str, task: str = "code_audit") -> Optional[str]:
        """Send a prompt to the local LLM for analysis.

        Args:
            prompt: The analysis prompt
            task: Task type for model selection

        Returns:
            LLM response text, or None if unavailable
        """
        model = self._select_model(task)
        if not model:
            logger.warning("No LLM model available for analysis")
            return None

        # Validate the prompt doesn't contain PII before sending
        pii_matches = scan_text(prompt)
        if pii_matches:
            # Redact PII from the prompt
            prompt, _ = redact_text(prompt)
            logger.info(f"Redacted {len(pii_matches)} PII matches from prompt")

        try:
            import urllib.request
            payload = json.dumps({
                "model": model,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": 0.1,  # Low temperature for deterministic analysis
                    "num_predict": 2048,
                },
            }).encode("utf-8")

            req = urllib.request.Request(
                f"{OLLAMA_HOST}/api/generate",
                data=payload,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=120) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                return data.get("response", "")

        except Exception as e:
            logger.error(f"LLM analysis failed: {e}")
            return None

    # ── Static Analysis ─────────────────────────────────────────────────

    def _static_scan_file(self, file_path: Path) -> list[Finding]:
        """Run static security checks on a file using built-in guards."""
        findings = []

        try:
            content = file_path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, PermissionError):
            return findings

        # ActionGuard pattern scan
        result = self.action_guard.validate_action("file_scan", content)
        if not result.allowed:
            findings.append(Finding(
                severity="HIGH",
                file_path=str(file_path.relative_to(WORKSPACE_ROOT)),
                line_number=0,
                description=f"ActionGuard violation: {result.reason}",
                recommendation="Remove or replace the blocked pattern",
                source="action_guard",
            ))

        # PII scan
        pii_matches = scan_text(content)
        for match in pii_matches:
            line_num = content[:match.start].count("\n") + 1
            findings.append(Finding(
                severity="MEDIUM" if match.pii_type in ("email", "ip_address") else "HIGH",
                file_path=str(file_path.relative_to(WORKSPACE_ROOT)),
                line_number=line_num,
                description=f"PII detected: {match.pii_type}",
                recommendation=f"Remove or redact {match.pii_type} from source code",
                source="pii_scanner",
            ))

        return findings

    def _static_scan_requirements(self) -> list[Finding]:
        """Scan requirements.txt for package safety."""
        findings = []
        req_path = WORKSPACE_ROOT / "requirements.txt"
        if not req_path.exists():
            return findings

        results = self.sdk_guard.validate_requirements(str(req_path))
        for result in results:
            if not result.valid:
                findings.append(Finding(
                    severity="CRITICAL",
                    file_path="requirements.txt",
                    line_number=0,
                    description=f"Blocked package: {result.package} — {result.reason}",
                    recommendation="Remove the package or verify it is legitimate",
                    source="sdk_guard",
                ))

        return findings

    # ── LLM Analysis ────────────────────────────────────────────────────

    def _llm_scan_file(self, file_path: Path) -> list[Finding]:
        """Use LLM to deep-scan a file for vulnerabilities."""
        findings = []

        try:
            content = file_path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, PermissionError):
            return findings

        # Determine prompt template
        suffix = file_path.suffix.lower()
        if suffix in (".py",):
            template = AUDIT_PROMPTS["code_vulnerability"]
            task = "code_audit"
        elif suffix in (".yaml", ".yml"):
            # Check if it's a K8s manifest
            if "kind:" in content and ("apiVersion:" in content or "metadata:" in content):
                template = AUDIT_PROMPTS["k8s_security"]
                task = "security_plan"
            else:
                return findings  # Skip non-K8s YAML
        elif file_path.name.startswith("Dockerfile"):
            template = AUDIT_PROMPTS["docker_security"]
            task = "code_audit"
        else:
            return findings  # Skip unsupported file types

        # Truncate very large files to prevent prompt overflow
        max_chars = 8000
        if len(content) > max_chars:
            content = content[:max_chars] + "\n# ... (truncated for analysis)"

        prompt = template.format(
            file_path=str(file_path.relative_to(WORKSPACE_ROOT)),
            code=content,
        )

        response = self._llm_analyze(prompt, task)
        if not response:
            return findings

        # Parse LLM response for findings
        findings.extend(self._parse_llm_response(response, file_path))

        return findings

    def _parse_llm_response(self, response: str, file_path: Path) -> list[Finding]:
        """Parse LLM analysis response into structured findings."""
        findings = []

        if not response or "no vulnerabilities" in response.lower():
            return findings

        # Pattern: "Severity: CRITICAL/HIGH/MEDIUM/LOW"
        severity_pattern = re.compile(
            r"(?:severity|level):\s*(CRITICAL|HIGH|MEDIUM|LOW)",
            re.IGNORECASE,
        )

        # Split response into sections (each finding typically starts with severity or a number)
        sections = re.split(r"\n(?=\d+\.|[-*]\s*(?:Severity|Level|Issue|Vulnerability))", response)

        for section in sections:
            severity_match = severity_pattern.search(section)
            if not severity_match:
                continue

            severity = severity_match.group(1).upper()

            # Extract line number if mentioned
            line_match = re.search(r"[Ll]ine\s*(?:number)?\s*[:#]?\s*~?(\d+)", section)
            line_num = int(line_match.group(1)) if line_match else 0

            # Clean up description
            desc = section.strip()
            if len(desc) > 500:
                desc = desc[:500] + "..."

            findings.append(Finding(
                severity=severity,
                file_path=str(file_path.relative_to(WORKSPACE_ROOT)),
                line_number=line_num,
                description=desc,
                recommendation="See LLM analysis details above",
                source="llm_analysis",
            ))

        return findings

    # ── Audit Orchestration ─────────────────────────────────────────────

    def _should_skip(self, path: Path) -> bool:
        """Check if a file should be skipped during audit."""
        rel = str(path.relative_to(WORKSPACE_ROOT))
        for pattern in SKIP_PATTERNS:
            if re.search(pattern, rel):
                return True
        return False

    def _collect_files(self, directory: Optional[Path] = None) -> list[Path]:
        """Collect all auditable files from the workspace."""
        root = directory or WORKSPACE_ROOT
        files = []

        # Python files
        for py_file in root.rglob("*.py"):
            if not self._should_skip(py_file):
                files.append(py_file)

        # K8s manifests
        k8s_dir = WORKSPACE_ROOT / "k8s"
        if k8s_dir.exists():
            for yaml_file in k8s_dir.glob("*.yaml"):
                files.append(yaml_file)

        # Dockerfiles
        for df in root.glob("Dockerfile*"):
            if not self._should_skip(df):
                files.append(df)

        # docker-compose files
        for dc in root.glob("docker-compose*.yml"):
            if not self._should_skip(dc):
                files.append(dc)

        return sorted(set(files))

    def audit_file(self, file_path: str) -> AuditReport:
        """Run a security audit on a single file.

        Args:
            file_path: Path to the file to audit

        Returns:
            AuditReport with findings
        """
        report = AuditReport(status="running")
        start = time.time()
        path = Path(file_path).resolve()

        if not path.exists():
            report.status = "failed"
            report.findings.append(Finding(
                severity="INFO",
                file_path=file_path,
                line_number=0,
                description=f"File not found: {file_path}",
                recommendation="Verify the file path",
                source="system",
            ))
            return report

        # Static analysis
        report.findings.extend(self._static_scan_file(path))

        # LLM analysis
        model = self._select_model("code_audit")
        if model:
            report.model_used = model
            report.findings.extend(self._llm_scan_file(path))

        report.files_scanned = 1
        report.duration_seconds = time.time() - start
        report.status = "completed"
        return report

    def audit_k8s(self) -> AuditReport:
        """Run a security audit on all Kubernetes manifests.

        Returns:
            AuditReport with K8s-specific findings
        """
        report = AuditReport(status="running")
        start = time.time()

        k8s_dir = WORKSPACE_ROOT / "k8s"
        if not k8s_dir.exists():
            report.status = "completed"
            report.findings.append(Finding(
                severity="INFO",
                file_path="k8s/",
                line_number=0,
                description="No k8s/ directory found",
                recommendation="Create K8s manifests in k8s/ directory",
                source="system",
            ))
            return report

        yaml_files = list(k8s_dir.glob("*.yaml")) + list(k8s_dir.glob("*.yml"))

        for yaml_file in yaml_files:
            report.files_scanned += 1

            # PII/secret scan
            result = scan_k8s_manifest(str(yaml_file))
            if result["has_secrets"]:
                for v in result["violations"]:
                    if isinstance(v, dict):
                        report.findings.append(Finding(
                            severity="CRITICAL",
                            file_path=str(yaml_file.relative_to(WORKSPACE_ROOT)),
                            line_number=v.get("line_approx", 0),
                            description=f"Hardcoded secret: {v['type']}",
                            recommendation="Use sealed-secrets or external-secrets operator",
                            source="pii_scanner",
                        ))

            # ActionGuard K8s manifest scan
            try:
                content = yaml_file.read_text(encoding="utf-8")
                guard_result = self.action_guard.validate_k8s_manifest(content)
                if not guard_result.allowed:
                    report.findings.append(Finding(
                        severity="HIGH",
                        file_path=str(yaml_file.relative_to(WORKSPACE_ROOT)),
                        line_number=0,
                        description=f"K8s security violation: {guard_result.reason}",
                        recommendation="Fix the security violation per SLATE K8s policy",
                        source="action_guard",
                    ))
            except Exception as e:
                logger.error(f"Failed to scan {yaml_file}: {e}")

            # LLM deep analysis
            model = self._select_model("security_plan")
            if model:
                report.model_used = model
                report.findings.extend(self._llm_scan_file(yaml_file))

            # SDK guard: validate container images in manifest
            image_results = self.sdk_guard.validate_k8s_manifest_images(str(yaml_file))
            for img_result in image_results:
                if not img_result.valid:
                    report.findings.append(Finding(
                        severity="HIGH",
                        file_path=str(yaml_file.relative_to(WORKSPACE_ROOT)),
                        line_number=0,
                        description=f"Untrusted container image: {img_result.package}",
                        recommendation=f"Use a trusted registry. {img_result.reason}",
                        source="sdk_guard",
                    ))

        report.duration_seconds = time.time() - start
        report.status = "completed"
        return report

    def audit_full(self) -> AuditReport:
        """Run a complete security audit of the SLATE codebase.

        Performs:
        1. Static analysis (ActionGuard, PII Scanner, SDK Guard) on all files
        2. LLM-powered deep analysis on Python files, K8s manifests, Dockerfiles
        3. Requirements.txt package validation
        4. K8s manifest security audit

        Returns:
            AuditReport with all findings
        """
        report = AuditReport(status="running")
        start = time.time()

        print("=" * 60)
        print("  Grok Heavy SLATE Procedure — Security Audit")
        print("=" * 60)

        # 1. Check Ollama availability
        ollama_ok = self._check_ollama()
        model = self._select_model("code_audit")
        if model:
            report.model_used = model
            print(f"  LLM Backend: {model} (via Ollama at {OLLAMA_HOST})")
        else:
            print("  LLM Backend: UNAVAILABLE (static analysis only)")

        # 2. Collect files
        files = self._collect_files()
        print(f"  Files to scan: {len(files)}")

        # 3. Static scan: requirements.txt
        print("\n  [1/4] Scanning requirements.txt...")
        report.findings.extend(self._static_scan_requirements())

        # 4. Static + LLM scan each file
        print(f"  [2/4] Scanning {len(files)} source files...")
        for i, file_path in enumerate(files):
            report.files_scanned += 1
            if (i + 1) % 10 == 0 or i == 0:
                print(f"         {i + 1}/{len(files)}: {file_path.name}")

            # Static analysis (fast)
            report.findings.extend(self._static_scan_file(file_path))

            # LLM analysis (slow — only for key files)
            if model and file_path.suffix in (".py",):
                # Only LLM-scan slate/ and agents/ directories (core security-sensitive code)
                rel = str(file_path.relative_to(WORKSPACE_ROOT))
                if rel.startswith("slate/") or rel.startswith("agents/"):
                    report.findings.extend(self._llm_scan_file(file_path))

        # 5. K8s audit
        print("  [3/4] Scanning Kubernetes manifests...")
        k8s_report = self.audit_k8s()
        report.findings.extend(k8s_report.findings)

        # 6. Docker audit
        print("  [4/4] Scanning Dockerfiles...")
        for df in WORKSPACE_ROOT.glob("Dockerfile*"):
            if model:
                report.findings.extend(self._llm_scan_file(df))

        report.duration_seconds = time.time() - start
        report.status = "completed"

        # Save report
        report_path = report.save()

        # Print summary
        summary = report.to_dict()["summary"]
        print(f"\n  Audit Complete in {report.duration_seconds:.1f}s")
        print(f"  Files scanned: {report.files_scanned}")
        print(f"  Findings: {summary['total']} total")
        print(f"    CRITICAL: {summary['critical']}")
        print(f"    HIGH:     {summary['high']}")
        print(f"    MEDIUM:   {summary['medium']}")
        print(f"    LOW:      {summary['low']}")
        print(f"    INFO:     {summary['info']}")
        print(f"  Report saved: {report_path}")
        print("=" * 60)

        return report

    def get_latest_report(self) -> Optional[dict]:
        """Load the most recent audit report."""
        if not AUDIT_LOG_DIR.exists():
            return None

        reports = sorted(AUDIT_LOG_DIR.glob("audit_*.json"), reverse=True)
        if not reports:
            return None

        with open(reports[0], "r", encoding="utf-8") as f:
            return json.load(f)

    def status(self) -> dict:
        """Get procedure status."""
        ollama_ok = self._check_ollama()
        model = self._select_model("code_audit")
        latest = self.get_latest_report()

        return {
            "procedure": "Grok Heavy SLATE Procedure",
            "version": "1.0.0",
            "ollama_available": ollama_ok,
            "ollama_host": OLLAMA_HOST,
            "analysis_model": model or "unavailable",
            "available_models": self._available_models,
            "slate_models": {
                name: name in self._available_models
                for name in ANALYSIS_MODELS.values()
            },
            "guards": {
                "action_guard": True,
                "pii_scanner": True,
                "sdk_source_guard": True,
            },
            "k8s_manifests": (WORKSPACE_ROOT / "k8s").exists(),
            "audit_log_dir": str(AUDIT_LOG_DIR),
            "latest_report": {
                "timestamp": latest["timestamp"] if latest else None,
                "findings": latest["summary"]["total"] if latest else 0,
            } if latest else None,
        }


# ── CLI ─────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Grok Heavy SLATE Procedure — Automated Security Audit"
    )
    parser.add_argument("--status", action="store_true", help="Show procedure status")
    parser.add_argument("--audit", action="store_true", help="Run full security audit")
    parser.add_argument("--audit-file", help="Audit a single file")
    parser.add_argument("--audit-k8s", action="store_true", help="Audit K8s manifests only")
    parser.add_argument("--report", action="store_true", help="Show latest audit report")
    parser.add_argument("--json", action="store_true", help="Output as JSON")

    args = parser.parse_args()
    proc = GrokHeavySlateProcedure()

    if args.status:
        status = proc.status()
        if args.json:
            print(json.dumps(status, indent=2))
        else:
            print("=" * 60)
            print("  Grok Heavy SLATE Procedure — Status")
            print("=" * 60)
            print(f"  Ollama:     {'OK' if status['ollama_available'] else 'UNAVAILABLE'}")
            print(f"  Host:       {status['ollama_host']}")
            print(f"  Model:      {status['analysis_model']}")
            print(f"  SLATE Models:")
            for name, avail in status["slate_models"].items():
                print(f"    {name}: {'OK' if avail else 'NOT LOADED'}")
            print(f"  Guards:     ActionGuard, PII Scanner, SDK Source Guard")
            print(f"  K8s:        {'Manifests found' if status['k8s_manifests'] else 'No manifests'}")
            if status["latest_report"]:
                print(f"  Last Audit: {status['latest_report']['timestamp']}")
                print(f"  Findings:   {status['latest_report']['findings']}")
            else:
                print("  Last Audit: None")
            print("=" * 60)
        return 0

    if args.audit:
        report = proc.audit_full()
        if args.json:
            print(json.dumps(report.to_dict(), indent=2))
        return 1 if report.to_dict()["summary"]["critical"] > 0 else 0

    if args.audit_file:
        report = proc.audit_file(args.audit_file)
        if args.json:
            print(json.dumps(report.to_dict(), indent=2))
        else:
            for f in report.findings:
                print(f"  [{f.severity}] {f.file_path}:{f.line_number} — {f.description}")
            if not report.findings:
                print("  No issues found.")
        return 1 if report.to_dict()["summary"]["critical"] > 0 else 0

    if args.audit_k8s:
        report = proc.audit_k8s()
        if args.json:
            print(json.dumps(report.to_dict(), indent=2))
        else:
            print("=" * 60)
            print("  K8s Security Audit")
            print("=" * 60)
            for f in report.findings:
                print(f"  [{f.severity}] {f.file_path}:{f.line_number} — {f.description}")
            if not report.findings:
                print("  No K8s security issues found.")
            print(f"\n  Files scanned: {report.files_scanned}")
            print("=" * 60)
        return 1 if report.to_dict()["summary"]["critical"] > 0 else 0

    if args.report:
        latest = proc.get_latest_report()
        if not latest:
            print("No audit reports found. Run --audit first.")
            return 1
        if args.json:
            print(json.dumps(latest, indent=2))
        else:
            print("=" * 60)
            print(f"  Latest Audit Report: {latest['timestamp']}")
            print("=" * 60)
            s = latest["summary"]
            print(f"  Status:   {latest['status']}")
            print(f"  Files:    {latest['files_scanned']}")
            print(f"  Duration: {latest['duration_seconds']}s")
            print(f"  Model:    {latest['model_used']}")
            print(f"  Findings: {s['total']} (C:{s['critical']} H:{s['high']} M:{s['medium']} L:{s['low']})")
            if latest["findings"]:
                print("\n  Details:")
                for f in latest["findings"][:20]:
                    print(f"    [{f['severity']}] {f['file']}:{f['line']} — {f['description'][:80]}")
                if len(latest["findings"]) > 20:
                    print(f"    ... and {len(latest['findings']) - 20} more")
            print("=" * 60)
        return 0

    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
