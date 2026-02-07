# Modified: 2026-02-07T09:00:00Z | Author: COPILOT | Change: Add K8s Secret/ConfigMap/env scanning
"""
PII Scanner for SLATE Project Boards and Kubernetes Manifests

Prevents personal identifiable information from being exposed in public project boards
and Kubernetes Secret/ConfigMap/environment variable definitions.
Scans issue/PR titles, descriptions, comments, and K8s manifests before deployment.
"""

import re
import sys
from pathlib import Path
from typing import NamedTuple

# PII detection patterns
PII_PATTERNS: dict[str, re.Pattern] = {
    "email": re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"),
    "phone_us": re.compile(r"\b(?:\+1[-.\s]?)?\(?[0-9]{3}\)?[-.\s]?[0-9]{3}[-.\s]?[0-9]{4}\b"),
    "phone_intl": re.compile(r"\b\+[0-9]{1,3}[-.\s]?[0-9]{6,14}\b"),
    "ssn": re.compile(r"\b[0-9]{3}[-\s]?[0-9]{2}[-\s]?[0-9]{4}\b"),
    "credit_card": re.compile(r"\b(?:4[0-9]{12}(?:[0-9]{3})?|5[1-5][0-9]{14}|3[47][0-9]{13}|6(?:011|5[0-9]{2})[0-9]{12})\b"),
    "ip_address": re.compile(r"\b(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\b"),
    "api_key": re.compile(r"\b(?:sk|pk|api|key|token|secret|password|bearer)[-_]?[A-Za-z0-9]{16,}\b", re.IGNORECASE),
    "aws_key": re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    "github_token": re.compile(r"\b(?:ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9]{36,}\b"),
    "private_key": re.compile(r"-----BEGIN (?:RSA |DSA |EC |OPENSSH )?PRIVATE KEY-----"),
    "jwt": re.compile(r"\beyJ[A-Za-z0-9_-]*\.eyJ[A-Za-z0-9_-]*\.[A-Za-z0-9_-]*\b"),
    "home_address": re.compile(r"\b\d{1,5}\s+[\w\s]+(?:street|st|avenue|ave|road|rd|boulevard|blvd|lane|ln|drive|dr|court|ct|way|place|pl)\b", re.IGNORECASE),
    "date_of_birth": re.compile(r"\b(?:dob|birth\s*date|date\s*of\s*birth)[:\s]+[0-9]{1,2}[/-][0-9]{1,2}[/-][0-9]{2,4}\b", re.IGNORECASE),
}

# Allowlist patterns (things that look like PII but aren't)
ALLOWLIST_PATTERNS: list[re.Pattern] = [
    re.compile(r"\b127\.0\.0\.1\b"),  # localhost
    re.compile(r"\b0\.0\.0\.0\b"),  # any interface
    re.compile(r"\b192\.168\.\d+\.\d+\b"),  # private IP
    re.compile(r"\b10\.\d+\.\d+\.\d+\b"),  # private IP
    re.compile(r"\b172\.(?:1[6-9]|2[0-9]|3[01])\.\d+\.\d+\b"),  # private IP
    re.compile(r"\bexample\.com\b"),  # example domain
    re.compile(r"\btest@test\.com\b"),  # test email
    re.compile(r"\buser@example\.com\b"),  # example email
    re.compile(r"\bnoreply@anthropic\.com\b"),  # Claude co-author
    re.compile(r"\bnoreply@github\.com\b"),  # GitHub noreply
]


class PIIMatch(NamedTuple):
    """Represents a PII match found in text."""
    pii_type: str
    value: str
    start: int
    end: int


def is_allowlisted(text: str, match: re.Match) -> bool:
    """Check if a match is in the allowlist."""
    matched_text = match.group()
    for pattern in ALLOWLIST_PATTERNS:
        if pattern.search(matched_text):
            return True
    return False


def scan_text(text: str) -> list[PIIMatch]:
    """
    Scan text for PII patterns.

    Args:
        text: The text to scan

    Returns:
        List of PII matches found
    """
    if not text:
        return []

    matches: list[PIIMatch] = []

    for pii_type, pattern in PII_PATTERNS.items():
        for match in pattern.finditer(text):
            if not is_allowlisted(text, match):
                matches.append(PIIMatch(
                    pii_type=pii_type,
                    value=match.group(),
                    start=match.start(),
                    end=match.end()
                ))

    return matches


def redact_text(text: str) -> tuple[str, list[PIIMatch]]:
    """
    Redact PII from text.

    Args:
        text: The text to redact

    Returns:
        Tuple of (redacted text, list of matches)
    """
    if not text:
        return text, []

    matches = scan_text(text)
    if not matches:
        return text, []

    # Sort by position (reverse) to replace from end
    sorted_matches = sorted(matches, key=lambda m: m.start, reverse=True)

    redacted = text
    for match in sorted_matches:
        redaction = f"[REDACTED:{match.pii_type.upper()}]"
        redacted = redacted[:match.start] + redaction + redacted[match.end:]

    return redacted, matches


def scan_github_content(title: str, body: str | None = None) -> dict:
    """
    Scan GitHub issue/PR content for PII.

    Args:
        title: Issue/PR title
        body: Issue/PR body/description

    Returns:
        Dict with scan results
    """
    results = {
        "has_pii": False,
        "title_pii": [],
        "body_pii": [],
        "redacted_title": title,
        "redacted_body": body,
        "blocked": False,
        "message": ""
    }

    # Scan title
    title_matches = scan_text(title)
    if title_matches:
        results["has_pii"] = True
        results["title_pii"] = [{"type": m.pii_type, "value": "[hidden]"} for m in title_matches]
        results["redacted_title"], _ = redact_text(title)

    # Scan body
    if body:
        body_matches = scan_text(body)
        if body_matches:
            results["has_pii"] = True
            results["body_pii"] = [{"type": m.pii_type, "value": "[hidden]"} for m in body_matches]
            results["redacted_body"], _ = redact_text(body)

    # Determine if blocked
    critical_types = {"ssn", "credit_card", "private_key", "aws_key"}
    all_matches = title_matches + (scan_text(body) if body else [])

    for match in all_matches:
        if match.pii_type in critical_types:
            results["blocked"] = True
            results["message"] = f"Critical PII detected ({match.pii_type}). Item blocked from public project."
            break

    if results["has_pii"] and not results["blocked"]:
        results["message"] = "PII detected. Content will be redacted before adding to public project."

    return results


# ── Kubernetes Scanning ─────────────────────────────────────────────────

# K8s-specific patterns for hardcoded secrets in manifests
K8S_SECRET_PATTERNS: dict[str, re.Pattern] = {
    "hardcoded_password": re.compile(
        r"(?:password|passwd|secret|token|api[_-]?key):\s*[\"']?[A-Za-z0-9+/=]{8,}[\"']?",
        re.IGNORECASE,
    ),
    "base64_secret_data": re.compile(
        r"data:\s*\n(?:\s+\w+:\s*[A-Za-z0-9+/=]{20,}\s*\n)+",
        re.MULTILINE,
    ),
    "env_secret_inline": re.compile(
        r"value:\s*[\"']?(?:sk-|pk-|ghp_|gho_|ghu_|AKIA|bearer\s)[A-Za-z0-9_-]+[\"']?",
        re.IGNORECASE,
    ),
    "connection_string": re.compile(
        r"(?:mongodb|postgres|mysql|redis)://[^\s\"']+:[^\s\"']+@",
        re.IGNORECASE,
    ),
}

# Safe patterns in K8s (template refs, not actual secrets)
K8S_ALLOWLIST = [
    re.compile(r"\$\{\{.*\}\}"),  # GitHub Actions template
    re.compile(r"\$\(.*\)"),  # Shell expansion
    re.compile(r"secretKeyRef"),  # K8s secret reference (safe)
    re.compile(r"configMapKeyRef"),  # ConfigMap reference (safe)
    re.compile(r"valueFrom:"),  # Dynamic value reference (safe)
]


def scan_k8s_manifest(manifest_path: str) -> dict:
    """Scan a Kubernetes manifest file for hardcoded secrets and PII.

    Checks for:
    - Hardcoded passwords/tokens in env vars
    - Base64-encoded secret data that should use sealed-secrets
    - Connection strings with embedded credentials
    - Standard PII patterns (emails, keys, etc.)

    Args:
        manifest_path: Path to the YAML manifest file

    Returns:
        Dict with scan results including violations and recommendations
    """
    results = {
        "file": manifest_path,
        "has_secrets": False,
        "has_pii": False,
        "violations": [],
        "pii_matches": [],
        "recommendations": [],
        "blocked": False,
    }

    try:
        content = Path(manifest_path).read_text(encoding="utf-8")
    except (FileNotFoundError, PermissionError) as e:
        results["violations"].append(f"Cannot read file: {e}")
        return results

    # Check for hardcoded secrets
    for secret_type, pattern in K8S_SECRET_PATTERNS.items():
        for match in pattern.finditer(content):
            matched_text = match.group()
            # Skip if it's a template reference
            if any(allow.search(matched_text) for allow in K8S_ALLOWLIST):
                continue
            results["has_secrets"] = True
            results["violations"].append({
                "type": secret_type,
                "line_approx": content[:match.start()].count("\n") + 1,
                "context": matched_text[:80],
            })

    # Standard PII scan on the full content
    pii_matches = scan_text(content)
    if pii_matches:
        results["has_pii"] = True
        results["pii_matches"] = [
            {"type": m.pii_type, "line_approx": content[:m.start].count("\n") + 1}
            for m in pii_matches
        ]

    # Generate recommendations
    if results["has_secrets"]:
        results["blocked"] = True
        results["recommendations"].append(
            "Use Kubernetes Secrets with sealed-secrets operator instead of hardcoded values"
        )
        results["recommendations"].append(
            "Reference secrets via secretKeyRef in env vars, not inline values"
        )

    if results["has_pii"]:
        results["recommendations"].append(
            "Remove PII from manifest files. Use ConfigMaps or external-secrets"
        )

    return results


def scan_k8s_directory(directory: str) -> list[dict]:
    """Scan all YAML files in a directory for K8s security issues.

    Args:
        directory: Path to directory containing K8s manifests

    Returns:
        List of scan results, one per file
    """
    results = []
    dir_path = Path(directory)
    if not dir_path.exists():
        return results

    for yaml_file in sorted(dir_path.glob("*.yaml")):
        result = scan_k8s_manifest(str(yaml_file))
        results.append(result)

    for yml_file in sorted(dir_path.glob("*.yml")):
        result = scan_k8s_manifest(str(yml_file))
        results.append(result)

    return results


def main():
    """CLI interface for PII scanner."""
    import argparse
    import json

    parser = argparse.ArgumentParser(description="SLATE PII Scanner")
    parser.add_argument("--text", help="Text to scan")
    parser.add_argument("--title", help="Issue/PR title")
    parser.add_argument("--body", help="Issue/PR body")
    parser.add_argument("--k8s-dir", help="Scan K8s manifest directory")
    parser.add_argument("--k8s-file", help="Scan a single K8s manifest file")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    parser.add_argument("--test", action="store_true", help="Run self-test")

    args = parser.parse_args()

    if args.test:
        # Self-test with sample PII
        test_cases = [
            ("Clean title", "This is a clean issue"),
            ("Email", "Contact me at user@example.com"),
            ("Phone", "Call me at 555-123-4567"),
            ("SSN", "My SSN is 123-45-6789"),
            ("API Key", "Use api_key_abc123def456ghi789"),
            ("GitHub Token", "Token: ghp_abcdefghijklmnopqrstuvwxyz123456"),
            ("Private IP (allowed)", "Server at 192.168.1.100"),
        ]

        print("PII Scanner Self-Test")
        print("=" * 50)
        for name, text in test_cases:
            matches = scan_text(text)
            status = "DETECTED" if matches else "CLEAN"
            types = ", ".join(m.pii_type for m in matches) if matches else "-"
            print(f"{name:25} | {status:10} | {types}")
        return 0

    if args.k8s_dir:
        results = scan_k8s_directory(args.k8s_dir)
        if args.json:
            print(json.dumps(results, indent=2))
        else:
            for r in results:
                status = "BLOCKED" if r["blocked"] else ("WARNING" if r["has_secrets"] or r["has_pii"] else "CLEAN")
                print(f"  {status:8} | {r['file']}")
                for v in r.get("violations", []):
                    if isinstance(v, dict):
                        print(f"           -> {v['type']} (line ~{v['line_approx']})")
                for rec in r.get("recommendations", []):
                    print(f"           ** {rec}")
        blocked = any(r["blocked"] for r in results)
        return 1 if blocked else 0

    if args.k8s_file:
        result = scan_k8s_manifest(args.k8s_file)
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            status = "BLOCKED" if result["blocked"] else ("WARNING" if result["has_secrets"] else "CLEAN")
            print(f"{status}: {result['file']}")
            for v in result.get("violations", []):
                if isinstance(v, dict):
                    print(f"  -> {v['type']} (line ~{v['line_approx']})")
        return 1 if result["blocked"] else 0

    if args.title:
        results = scan_github_content(args.title, args.body)
        if args.json:
            print(json.dumps(results, indent=2))
        else:
            if results["has_pii"]:
                print(f"PII DETECTED: {results['message']}")
                if results["blocked"]:
                    return 1
            else:
                print("No PII detected")
        return 1 if results["blocked"] else 0

    if args.text:
        matches = scan_text(args.text)
        if args.json:
            print(json.dumps([{"type": m.pii_type, "start": m.start, "end": m.end} for m in matches]))
        else:
            if matches:
                print(f"Found {len(matches)} PII match(es):")
                for m in matches:
                    print(f"  - {m.pii_type}: position {m.start}-{m.end}")
            else:
                print("No PII detected")
        return 1 if matches else 0

    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
