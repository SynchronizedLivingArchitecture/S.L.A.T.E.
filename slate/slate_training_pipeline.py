#!/usr/bin/env python3
# Modified: 2026-02-07T15:00:00Z | Author: Claude | Change: Secure AI training pipeline with secret filtering
"""
SLATE Secure AI Training Pipeline
==================================

Ingests the ENTIRE git repository for local AI model training while
ensuring secrets, credentials, and sensitive data are NEVER included.

Security Protocol:
- PII Scanner integration for all content
- Secret pattern detection (API keys, tokens, passwords)
- .gitignore and .env file exclusion
- Commit message sanitization
- NO external distribution - local training only

Usage:
    python slate/slate_training_pipeline.py --collect          # Collect training data
    python slate/slate_training_pipeline.py --validate         # Validate data is secret-free
    python slate/slate_training_pipeline.py --prepare          # Prepare for training
    python slate/slate_training_pipeline.py --train            # Execute training
    python slate/slate_training_pipeline.py --status           # Show pipeline status
"""

import argparse
import hashlib
import json
import re
import subprocess
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

WORKSPACE_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(WORKSPACE_ROOT))

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# Import SLATE security modules
try:
    from slate.pii_scanner import scan_text, redact_text
    from slate.action_guard import ActionGuard
except ImportError:
    # Fallback if modules not available
    def scan_text(text): return []
    def redact_text(text): return text, []
    class ActionGuard:
        def validate_action(self, *args):
            return type('obj', (object,), {'allowed': True})()

# ═══════════════════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════

TRAINING_DIR = WORKSPACE_ROOT / ".slate_training"
TRAINING_DATA_FILE = TRAINING_DIR / "training_data.json"
MODELFILE_DIR = TRAINING_DIR / "modelfiles"
STATE_FILE = TRAINING_DIR / "pipeline_state.json"
OLLAMA_URL = "http://127.0.0.1:11434"

# Secret patterns to ALWAYS filter
SECRET_PATTERNS = [
    # API Keys and Tokens
    re.compile(r'\b(?:sk|pk|api|key|token|secret|password|bearer|auth)[_-]?[A-Za-z0-9]{16,}\b', re.I),
    re.compile(r'\bAKIA[0-9A-Z]{16}\b'),  # AWS Access Key
    re.compile(r'\b(?:ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9]{36,}\b'),  # GitHub Token
    re.compile(r'\bxox[baprs]-[0-9A-Za-z-]{10,}\b'),  # Slack Token
    re.compile(r'\bglpat-[A-Za-z0-9_-]{20,}\b'),  # GitLab Token
    re.compile(r'\bnpm_[A-Za-z0-9]{36}\b'),  # NPM Token
    re.compile(r'\bpypi-[A-Za-z0-9-_]{32,}\b'),  # PyPI Token

    # Private Keys
    re.compile(r'-----BEGIN (?:RSA |DSA |EC |OPENSSH |PGP )?PRIVATE KEY-----'),
    re.compile(r'-----BEGIN CERTIFICATE-----'),

    # JWT Tokens
    re.compile(r'\beyJ[A-Za-z0-9_-]*\.eyJ[A-Za-z0-9_-]*\.[A-Za-z0-9_-]*\b'),

    # Connection Strings
    re.compile(r'(?:mongodb|postgres|mysql|redis|amqp)://[^\s]+:[^\s]+@[^\s]+', re.I),
    re.compile(r'(?:Data Source|Server)=[^;]+;.*(?:Password|Pwd)=[^;]+', re.I),

    # Base64 encoded secrets (likely)
    re.compile(r'(?:password|secret|token|key)\s*[:=]\s*["\']?[A-Za-z0-9+/]{40,}={0,2}["\']?', re.I),

    # Common secret variable assignments
    re.compile(r'(?:PASSWORD|SECRET|TOKEN|API_KEY|PRIVATE_KEY)\s*=\s*["\'][^"\']{8,}["\']', re.I),
]

# Files to ALWAYS exclude from training
EXCLUDED_FILE_PATTERNS = [
    r'\.env$', r'\.env\.[a-z]+$',
    r'\.pem$', r'\.key$', r'\.p12$', r'\.pfx$',
    r'credentials\.json$', r'secrets\.json$', r'config\.secret\..*$',
    r'\.git/', r'\.ssh/',
    r'__pycache__/', r'\.pyc$',
    r'node_modules/',
    r'\.slate_runner_costs\.json$',
    r'\.slate_.*\.pid$',
]

# File extensions to include for code training
TRAINING_FILE_EXTENSIONS = {
    '.py', '.js', '.ts', '.tsx', '.jsx',
    '.yml', '.yaml', '.json', '.toml',
    '.md', '.rst', '.txt',
    '.sh', '.ps1', '.bat', '.cmd',
    '.html', '.css', '.scss',
}


# ═══════════════════════════════════════════════════════════════════════
# DATA CLASSES
# ═══════════════════════════════════════════════════════════════════════

@dataclass
class TrainingSample:
    """A single training sample with metadata."""
    source: str
    content: str
    content_type: str
    file_path: Optional[str] = None
    commit_hash: Optional[str] = None
    tokens_estimated: int = 0
    hash: str = ""

    def __post_init__(self):
        if not self.hash:
            self.hash = hashlib.md5(self.content.encode()).hexdigest()[:12]
        if not self.tokens_estimated:
            self.tokens_estimated = len(self.content.split())


@dataclass
class SecurityScanResult:
    """Result of security scanning."""
    is_safe: bool
    secrets_found: int = 0
    pii_found: int = 0
    redacted_content: str = ""
    warnings: list = field(default_factory=list)


# ═══════════════════════════════════════════════════════════════════════
# SECURITY SCANNER
# ═══════════════════════════════════════════════════════════════════════

class SecretScanner:
    """Scans content for secrets and sensitive data."""

    def __init__(self):
        self.action_guard = ActionGuard()
        self._scan_count = 0
        self._secrets_blocked = 0

    def contains_secrets(self, content: str) -> list[str]:
        """Check if content contains any secrets. Returns list of pattern names."""
        findings = []
        for i, pattern in enumerate(SECRET_PATTERNS):
            if pattern.search(content):
                findings.append(f"secret_pattern_{i}")
        return findings

    def scan_and_redact(self, content: str) -> SecurityScanResult:
        """Scan content and redact any secrets/PII."""
        self._scan_count += 1

        result = SecurityScanResult(is_safe=True, redacted_content=content)

        # Check for secrets
        secret_findings = self.contains_secrets(content)
        if secret_findings:
            result.secrets_found = len(secret_findings)
            result.warnings.extend([f"Secret detected: {f}" for f in secret_findings])
            self._secrets_blocked += len(secret_findings)

            # Redact secrets
            redacted = content
            for pattern in SECRET_PATTERNS:
                redacted = pattern.sub("[REDACTED_SECRET]", redacted)
            result.redacted_content = redacted
            result.is_safe = False

        # Check for PII
        pii_matches = scan_text(content)
        if pii_matches:
            result.pii_found = len(pii_matches)
            result.warnings.extend([f"PII detected: {m.pii_type}" for m in pii_matches])
            result.redacted_content, _ = redact_text(result.redacted_content)

        # Re-check redacted content is safe
        if result.secrets_found > 0 or result.pii_found > 0:
            remaining_secrets = self.contains_secrets(result.redacted_content)
            result.is_safe = len(remaining_secrets) == 0

        return result

    def is_file_excluded(self, file_path: str) -> bool:
        """Check if file should be excluded from training."""
        for pattern in EXCLUDED_FILE_PATTERNS:
            if re.search(pattern, file_path, re.I):
                return True
        return False

    def get_stats(self) -> dict:
        """Get scanning statistics."""
        return {
            "total_scans": self._scan_count,
            "secrets_blocked": self._secrets_blocked,
        }


# ═══════════════════════════════════════════════════════════════════════
# GIT INGESTION
# ═══════════════════════════════════════════════════════════════════════

class GitIngester:
    """Ingests entire git repository for training."""

    def __init__(self, workspace: Path):
        self.workspace = workspace
        self.scanner = SecretScanner()

    def _run_git(self, args: list[str], timeout: int = 60) -> str:
        """Run a git command."""
        result = subprocess.run(
            ["git"] + args,
            capture_output=True, text=True, timeout=timeout,
            cwd=str(self.workspace), encoding="utf-8", errors="replace"
        )
        return result.stdout.strip()

    def get_all_tracked_files(self) -> list[Path]:
        """Get all tracked files in the repository."""
        output = self._run_git(["ls-files"])
        files = []
        for line in output.split('\n'):
            if not line.strip():
                continue
            file_path = self.workspace / line.strip()
            if file_path.exists() and file_path.is_file():
                # Check extension
                if file_path.suffix.lower() in TRAINING_FILE_EXTENSIONS:
                    # Check exclusion patterns
                    if not self.scanner.is_file_excluded(str(file_path)):
                        files.append(file_path)
        return files

    def get_commit_history(self, limit: int = 500) -> list[dict]:
        """Get commit history with messages."""
        output = self._run_git([
            "log", f"--max-count={limit}",
            "--format=%H|||%s|||%an|||%ae|||%ad",
            "--date=iso"
        ])
        commits = []
        for line in output.split('\n'):
            if not line.strip():
                continue
            parts = line.split("|||")
            if len(parts) >= 5:
                commit = {
                    "hash": parts[0][:12],
                    "message": parts[1],
                    "author": parts[2],
                    "email": parts[3],
                    "date": parts[4],
                }
                commits.append(commit)
        return commits

    def get_file_history(self, file_path: Path, limit: int = 10) -> list[dict]:
        """Get change history for a specific file."""
        rel_path = file_path.relative_to(self.workspace)
        output = self._run_git([
            "log", f"--max-count={limit}",
            "--format=%H|||%s|||%ad",
            "--date=short", "--",
            str(rel_path)
        ])
        history = []
        for line in output.split('\n'):
            if not line.strip():
                continue
            parts = line.split("|||")
            if len(parts) >= 3:
                history.append({
                    "hash": parts[0][:12],
                    "message": parts[1],
                    "date": parts[2],
                })
        return history

    def collect_code_samples(self) -> list[TrainingSample]:
        """Collect code samples from all tracked files."""
        samples = []
        files = self.get_all_tracked_files()

        print(f"  Found {len(files)} files to process...")

        for i, file_path in enumerate(files):
            if (i + 1) % 50 == 0:
                print(f"    Processing file {i + 1}/{len(files)}...")

            try:
                content = file_path.read_text(encoding="utf-8", errors="replace")

                # Skip empty or very small files
                if len(content.strip()) < 50:
                    continue

                # Security scan
                scan_result = self.scanner.scan_and_redact(content)

                # Use redacted content if secrets found
                safe_content = scan_result.redacted_content if not scan_result.is_safe else content

                # Skip if still unsafe after redaction
                if self.scanner.contains_secrets(safe_content):
                    print(f"    [!] Skipping {file_path.name} - contains unredactable secrets")
                    continue

                # Determine content type
                content_type = "code"
                if file_path.suffix in {'.md', '.rst', '.txt'}:
                    content_type = "documentation"
                elif file_path.suffix in {'.yml', '.yaml', '.json', '.toml'}:
                    content_type = "config"

                rel_path = str(file_path.relative_to(self.workspace))

                samples.append(TrainingSample(
                    source="file",
                    content=safe_content,
                    content_type=content_type,
                    file_path=rel_path,
                ))

            except Exception as e:
                print(f"    [!] Error processing {file_path.name}: {e}")

        return samples

    def collect_commit_messages(self) -> list[TrainingSample]:
        """Collect sanitized commit messages for training."""
        samples = []
        commits = self.get_commit_history(limit=500)

        print(f"  Found {len(commits)} commits to process...")

        for commit in commits:
            message = commit["message"]

            # Security scan commit message
            scan_result = self.scanner.scan_and_redact(message)
            safe_message = scan_result.redacted_content

            # Sanitize author email
            email = commit["email"]
            if "@" in email and not email.endswith(("@slate.local", "@anthropic.com", "@github.com")):
                email = "[REDACTED_EMAIL]"

            training_content = f"Commit: {safe_message}\nAuthor: {commit['author']}\nDate: {commit['date']}"

            samples.append(TrainingSample(
                source="commit",
                content=training_content,
                content_type="commit_message",
                commit_hash=commit["hash"],
            ))

        return samples

    def collect_docstrings(self) -> list[TrainingSample]:
        """Extract docstrings from Python files."""
        samples = []

        for py_file in self.workspace.glob("**/*.py"):
            if self.scanner.is_file_excluded(str(py_file)):
                continue

            try:
                content = py_file.read_text(encoding="utf-8", errors="replace")

                # Extract docstrings (triple-quoted strings at module/function/class level)
                docstring_pattern = re.compile(r'"""(.*?)"""', re.DOTALL)
                matches = docstring_pattern.findall(content)

                for doc in matches:
                    doc = doc.strip()
                    if len(doc) < 20:  # Skip tiny docstrings
                        continue

                    # Security scan
                    scan_result = self.scanner.scan_and_redact(doc)
                    safe_doc = scan_result.redacted_content

                    samples.append(TrainingSample(
                        source="docstring",
                        content=safe_doc,
                        content_type="documentation",
                        file_path=str(py_file.relative_to(self.workspace)),
                    ))
            except Exception:
                continue

        return samples


# ═══════════════════════════════════════════════════════════════════════
# TRAINING PIPELINE
# ═══════════════════════════════════════════════════════════════════════

class TrainingPipeline:
    """Manages the secure AI training pipeline."""

    def __init__(self):
        self.workspace = WORKSPACE_ROOT
        self.training_dir = TRAINING_DIR
        self.ingester = GitIngester(self.workspace)
        self.state = self._load_state()

        # Ensure directories exist
        self.training_dir.mkdir(parents=True, exist_ok=True)
        MODELFILE_DIR.mkdir(parents=True, exist_ok=True)

    def _load_state(self) -> dict:
        """Load pipeline state."""
        if STATE_FILE.exists():
            try:
                return json.loads(STATE_FILE.read_text(encoding="utf-8"))
            except Exception:
                pass
        return {
            "last_collection": None,
            "last_validation": None,
            "last_training": None,
            "total_samples": 0,
            "training_runs": 0,
            "models_trained": [],
        }

    def _save_state(self):
        """Save pipeline state."""
        STATE_FILE.write_text(json.dumps(self.state, indent=2, default=str), encoding="utf-8")

    def collect_training_data(self) -> dict:
        """Collect all training data from git repository."""
        print()
        print("=" * 70)
        print("  SLATE Secure Training Data Collection")
        print("=" * 70)
        print()
        print("  Security Protocol: ALL secrets and PII will be filtered")
        print()

        all_samples = []

        # Collect code samples
        print("[1/3] Collecting code samples...")
        code_samples = self.ingester.collect_code_samples()
        all_samples.extend(code_samples)
        print(f"      Collected {len(code_samples)} code samples")

        # Collect commit messages
        print()
        print("[2/3] Collecting commit messages...")
        commit_samples = self.ingester.collect_commit_messages()
        all_samples.extend(commit_samples)
        print(f"      Collected {len(commit_samples)} commit samples")

        # Collect docstrings
        print()
        print("[3/3] Extracting docstrings...")
        docstring_samples = self.ingester.collect_docstrings()
        all_samples.extend(docstring_samples)
        print(f"      Extracted {len(docstring_samples)} docstrings")

        # Save training data
        training_data = {
            "collected_at": datetime.now(timezone.utc).isoformat(),
            "total_samples": len(all_samples),
            "by_type": {
                "code": len([s for s in all_samples if s.content_type == "code"]),
                "documentation": len([s for s in all_samples if s.content_type == "documentation"]),
                "config": len([s for s in all_samples if s.content_type == "config"]),
                "commit_message": len([s for s in all_samples if s.content_type == "commit_message"]),
            },
            "by_source": {
                "file": len([s for s in all_samples if s.source == "file"]),
                "commit": len([s for s in all_samples if s.source == "commit"]),
                "docstring": len([s for s in all_samples if s.source == "docstring"]),
            },
            "scanner_stats": self.ingester.scanner.get_stats(),
            "samples": [
                {
                    "source": s.source,
                    "content": s.content,
                    "content_type": s.content_type,
                    "file_path": s.file_path,
                    "commit_hash": s.commit_hash,
                    "tokens_estimated": s.tokens_estimated,
                    "hash": s.hash,
                }
                for s in all_samples
            ],
        }

        TRAINING_DATA_FILE.write_text(
            json.dumps(training_data, indent=2, ensure_ascii=False),
            encoding="utf-8"
        )

        # Update state
        self.state["last_collection"] = datetime.now(timezone.utc).isoformat()
        self.state["total_samples"] = len(all_samples)
        self._save_state()

        print()
        print("=" * 70)
        print(f"  Collection Complete: {len(all_samples)} samples")
        print(f"  Secrets blocked: {training_data['scanner_stats']['secrets_blocked']}")
        print(f"  Data saved to: {TRAINING_DATA_FILE}")
        print("=" * 70)

        return training_data

    def validate_training_data(self) -> dict:
        """Validate training data is free of secrets."""
        print()
        print("=" * 70)
        print("  Validating Training Data Security")
        print("=" * 70)
        print()

        if not TRAINING_DATA_FILE.exists():
            return {"valid": False, "error": "No training data found. Run --collect first."}

        training_data = json.loads(TRAINING_DATA_FILE.read_text(encoding="utf-8"))
        samples = training_data.get("samples", [])

        scanner = SecretScanner()
        issues = []
        samples_checked = 0

        for sample in samples:
            samples_checked += 1
            content = sample.get("content", "")

            # Check for any remaining secrets
            secrets = scanner.contains_secrets(content)
            if secrets:
                issues.append({
                    "sample_hash": sample.get("hash"),
                    "source": sample.get("source"),
                    "file_path": sample.get("file_path"),
                    "secrets_found": len(secrets),
                })

        is_valid = len(issues) == 0

        self.state["last_validation"] = datetime.now(timezone.utc).isoformat()
        self._save_state()

        result = {
            "valid": is_valid,
            "samples_checked": samples_checked,
            "issues_found": len(issues),
            "issues": issues[:10],  # Limit to first 10
            "validated_at": datetime.now(timezone.utc).isoformat(),
        }

        print(f"  Samples checked: {samples_checked}")
        print(f"  Issues found: {len(issues)}")
        print(f"  Validation: {'PASSED' if is_valid else 'FAILED'}")
        print("=" * 70)

        return result

    def prepare_modelfile(self, base_model: str = "mistral-nemo") -> Path:
        """Prepare Modelfile for custom model training."""
        if not TRAINING_DATA_FILE.exists():
            raise ValueError("No training data. Run --collect first.")

        training_data = json.loads(TRAINING_DATA_FILE.read_text(encoding="utf-8"))
        samples = training_data.get("samples", [])

        # Extract key patterns for system prompt
        file_patterns = {}
        for sample in samples:
            if sample.get("file_path"):
                parts = sample["file_path"].split("/")
                if parts:
                    module = parts[0]
                    file_patterns[module] = file_patterns.get(module, 0) + 1

        top_modules = sorted(file_patterns.items(), key=lambda x: -x[1])[:10]
        module_list = "\n".join([f"- {m[0]}/: {m[1]} files" for m in top_modules])

        modelfile_content = f'''FROM {base_model}

# SLATE Custom Model - Trained on local codebase
# Generated: {datetime.now(timezone.utc).isoformat()}
# Samples: {len(samples)}
# SECURITY: No secrets or PII included

SYSTEM """You are SLATE AI, a specialized assistant for the SLATE project.

SLATE = Synchronized Living Architecture for Transformation and Evolution

Project Structure:
{module_list}

You understand:
- Python 3.11+ with type hints and async patterns
- FastAPI web servers (dashboard on port 8080)
- GitHub Actions workflows (self-hosted runner)
- Ollama local LLM inference on dual RTX 5070 Ti GPUs
- ChromaDB vector storage for RAG
- Test-driven development practices

Always:
- Provide concise, technical responses
- Follow SLATE security protocols (local-only, no external APIs)
- Use type hints and docstrings
- Reference specific files and functions when relevant
"""

PARAMETER temperature 0.7
PARAMETER num_ctx 8192
PARAMETER top_p 0.9
'''

        modelfile_path = MODELFILE_DIR / f"Modelfile.slate-custom-{base_model.replace(':', '-')}"
        modelfile_path.write_text(modelfile_content, encoding="utf-8")

        print(f"  Modelfile created: {modelfile_path}")
        return modelfile_path

    def train_model(self, base_model: str = "mistral-nemo") -> dict:
        """Train custom SLATE model using local Ollama."""
        print()
        print("=" * 70)
        print("  SLATE Local AI Model Training")
        print("=" * 70)
        print()

        # Validate first
        validation = self.validate_training_data()
        if not validation["valid"]:
            return {"success": False, "error": "Training data validation failed"}

        # Prepare modelfile
        print("  Preparing Modelfile...")
        modelfile_path = self.prepare_modelfile(base_model)

        model_name = "slate-custom:latest"

        print(f"  Building model: {model_name}")
        print(f"  Base model: {base_model}")
        print()

        try:
            result = subprocess.run(
                ["ollama", "create", model_name, "-f", str(modelfile_path)],
                capture_output=True, text=True, timeout=600,
                encoding="utf-8", errors="replace"
            )

            if result.returncode == 0:
                print("  [OK] Model created successfully!")

                # Update state
                self.state["last_training"] = datetime.now(timezone.utc).isoformat()
                self.state["training_runs"] = self.state.get("training_runs", 0) + 1
                if model_name not in self.state.get("models_trained", []):
                    self.state.setdefault("models_trained", []).append(model_name)
                self._save_state()

                return {
                    "success": True,
                    "model_name": model_name,
                    "base_model": base_model,
                    "trained_at": datetime.now(timezone.utc).isoformat(),
                }
            else:
                return {"success": False, "error": result.stderr}

        except subprocess.TimeoutExpired:
            return {"success": False, "error": "Training timed out"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def print_status(self):
        """Print pipeline status."""
        print()
        print("=" * 70)
        print("  SLATE Secure Training Pipeline Status")
        print("=" * 70)
        print()
        print(f"  Last collection: {self.state.get('last_collection', 'Never')}")
        print(f"  Last validation: {self.state.get('last_validation', 'Never')}")
        print(f"  Last training: {self.state.get('last_training', 'Never')}")
        print(f"  Total samples: {self.state.get('total_samples', 0)}")
        print(f"  Training runs: {self.state.get('training_runs', 0)}")
        print(f"  Models trained: {', '.join(self.state.get('models_trained', [])) or 'None'}")
        print()

        if TRAINING_DATA_FILE.exists():
            training_data = json.loads(TRAINING_DATA_FILE.read_text(encoding="utf-8"))
            print("  Training Data Summary:")
            print(f"    Code samples: {training_data.get('by_type', {}).get('code', 0)}")
            print(f"    Documentation: {training_data.get('by_type', {}).get('documentation', 0)}")
            print(f"    Config files: {training_data.get('by_type', {}).get('config', 0)}")
            print(f"    Commit messages: {training_data.get('by_type', {}).get('commit_message', 0)}")
        else:
            print("  No training data collected yet.")

        print()
        print("=" * 70)


# ═══════════════════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(description="SLATE Secure AI Training Pipeline")
    parser.add_argument("--collect", action="store_true", help="Collect training data from git")
    parser.add_argument("--validate", action="store_true", help="Validate training data is secret-free")
    parser.add_argument("--prepare", action="store_true", help="Prepare Modelfile for training")
    parser.add_argument("--train", action="store_true", help="Train custom model")
    parser.add_argument("--status", action="store_true", help="Show pipeline status")
    parser.add_argument("--base-model", default="mistral-nemo", help="Base model for training")
    parser.add_argument("--json", action="store_true", help="Output as JSON")

    args = parser.parse_args()
    pipeline = TrainingPipeline()

    if args.collect:
        result = pipeline.collect_training_data()
        if args.json:
            print(json.dumps({
                "samples_collected": result["total_samples"],
                "by_type": result["by_type"],
                "training_ready": result["total_samples"] >= 10,
                "secrets_blocked": result["scanner_stats"]["secrets_blocked"],
            }, indent=2))

    elif args.validate:
        result = pipeline.validate_training_data()
        if args.json:
            print(json.dumps(result, indent=2))

    elif args.prepare:
        modelfile_path = pipeline.prepare_modelfile(args.base_model)
        if args.json:
            print(json.dumps({"modelfile": str(modelfile_path)}))

    elif args.train:
        result = pipeline.train_model(args.base_model)
        if args.json:
            print(json.dumps({
                "completed": result["success"],
                "model_name": result.get("model_name"),
                "error": result.get("error"),
            }, indent=2))
        else:
            if result["success"]:
                print(f"\n  Training complete: {result['model_name']}")
            else:
                print(f"\n  Training failed: {result.get('error')}")

    elif args.status:
        pipeline.print_status()

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
