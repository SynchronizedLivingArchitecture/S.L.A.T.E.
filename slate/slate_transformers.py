"""
SLATE Transformer Pipeline — HuggingFace Transformers for CI/CD Analysis
# Modified: 2026-02-07T18:00:00Z | Author: COPILOT | Change: Initial transformer pipeline module

GPU-accelerated transformer pipelines for code analysis, commit classification,
security scanning, and code quality evaluation using HuggingFace transformers.

Pipelines:
    - text-classification: Commit intent classification, code quality scoring
    - feature-extraction: Code embeddings for similarity search
    - text-generation: Code review & documentation generation
    - zero-shot-classification: Security pattern detection, issue categorization

Usage:
    python slate/slate_transformers.py --status           # Pipeline status & available models
    python slate/slate_transformers.py --classify "text"   # Classify text intent
    python slate/slate_transformers.py --embed "code"      # Generate code embedding
    python slate/slate_transformers.py --security "code"   # Security pattern scan
    python slate/slate_transformers.py --benchmark         # Pipeline benchmarks on both GPUs
    python slate/slate_transformers.py --batch-classify file.jsonl  # Batch classification
"""

# Modified: 2026-02-07T18:00:00Z | Author: COPILOT | Change: Initial module setup
import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

WORKSPACE_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(WORKSPACE_ROOT))

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")


# ═══════════════════════════════════════════════════════════════════════════════
# Model Registry — small, fast models suitable for CI pipelines
# ═══════════════════════════════════════════════════════════════════════════════
# Modified: 2026-02-07T18:00:00Z | Author: COPILOT | Change: Model registry for CI pipelines
PIPELINE_MODELS = {
    "text-classification": {
        "model": "microsoft/codebert-base",
        "description": "Code understanding & classification (125M params)",
        "gpu": 1,  # Secondary GPU for quick tasks
        "max_length": 512,
    },
    "feature-extraction": {
        "model": "microsoft/codebert-base",
        "description": "Code embeddings for similarity (125M params)",
        "gpu": 1,
        "max_length": 512,
    },
    "zero-shot-classification": {
        "model": "facebook/bart-large-mnli",
        "description": "Zero-shot classification for security/intent (407M params)",
        "gpu": 0,  # Primary GPU for larger model
        "max_length": 1024,
    },
    "text-generation": {
        "model": "microsoft/phi-2",
        "description": "Code generation & review (2.7B params)",
        "gpu": 0,
        "max_length": 2048,
    },
}

# Security patterns for zero-shot classification
# Modified: 2026-02-07T18:00:00Z | Author: COPILOT | Change: Security scan labels
SECURITY_LABELS = [
    "SQL injection vulnerability",
    "cross-site scripting (XSS)",
    "hardcoded credentials or secrets",
    "insecure deserialization",
    "path traversal attack",
    "command injection",
    "insecure network binding",
    "safe and secure code",
]

# Commit intent labels for classification
COMMIT_INTENT_LABELS = [
    "bug fix",
    "new feature",
    "refactoring",
    "documentation",
    "testing",
    "CI/CD configuration",
    "dependency update",
    "security patch",
    "performance optimization",
]


class SlateTransformerPipeline:
    """
    GPU-accelerated HuggingFace transformer pipelines for SLATE CI/CD.

    Manages pipeline lifecycle, GPU placement, and batch processing
    across dual RTX 5070 Ti GPUs.
    """

    # Modified: 2026-02-07T18:00:00Z | Author: COPILOT | Change: Pipeline manager class

    def __init__(self):
        self._pipelines: dict[str, Any] = {}
        self._load_times: dict[str, float] = {}
        self._torch_available = False
        self._cuda_available = False
        self._gpu_count = 0
        self._init_torch()

    def _init_torch(self) -> None:
        """Initialize PyTorch and detect GPU configuration."""
        try:
            import torch
            self._torch_available = True
            self._cuda_available = torch.cuda.is_available()
            self._gpu_count = torch.cuda.device_count() if self._cuda_available else 0
        except ImportError:
            pass

    def _get_device(self, gpu_index: int) -> int | str:
        """Get device for pipeline. Returns GPU index or -1 for CPU."""
        if not self._cuda_available:
            return -1
        if gpu_index < self._gpu_count:
            return gpu_index
        return 0  # Fallback to GPU 0

    def load_pipeline(self, task: str) -> Any:
        """Load a transformer pipeline for the given task, with GPU placement."""
        if task in self._pipelines:
            return self._pipelines[task]

        if task not in PIPELINE_MODELS:
            raise ValueError(
                f"Unknown pipeline task: {task}. "
                f"Available: {list(PIPELINE_MODELS.keys())}"
            )

        config = PIPELINE_MODELS[task]
        model_name = config["model"]
        device = self._get_device(config["gpu"])

        print(f"Loading pipeline: {task} ({model_name}) on "
              f"{'GPU ' + str(device) if device >= 0 else 'CPU'}...")

        start = time.time()
        try:
            from transformers import pipeline as hf_pipeline

            kwargs: dict[str, Any] = {
                "task": task,
                "model": model_name,
                "device": device,
            }

            # Task-specific configuration
            if task == "text-generation":
                kwargs["torch_dtype"] = "auto"
                kwargs["trust_remote_code"] = True

            pipe = hf_pipeline(**kwargs)
            elapsed = time.time() - start

            self._pipelines[task] = pipe
            self._load_times[task] = elapsed
            print(f"  Loaded in {elapsed:.1f}s")
            return pipe

        except Exception as e:
            print(f"  Failed to load {task}: {e}")
            raise

    def classify_text(self, text: str, labels: list[str] | None = None) -> dict:
        """
        Classify text using zero-shot classification.

        Args:
            text: Input text to classify
            labels: Custom labels (defaults to COMMIT_INTENT_LABELS)

        Returns:
            Dict with labels, scores, and top prediction
        """
        # Modified: 2026-02-07T18:00:00Z | Author: COPILOT | Change: Zero-shot classification
        if labels is None:
            labels = COMMIT_INTENT_LABELS

        pipe = self.load_pipeline("zero-shot-classification")
        result = pipe(text, candidate_labels=labels, multi_label=False)

        return {
            "text": text[:200],
            "labels": result["labels"],
            "scores": [round(s, 4) for s in result["scores"]],
            "top_label": result["labels"][0],
            "top_score": round(result["scores"][0], 4),
            "model": PIPELINE_MODELS["zero-shot-classification"]["model"],
        }

    def classify_commits(self, commits: list[str]) -> list[dict]:
        """Batch classify commit messages by intent."""
        pipe = self.load_pipeline("zero-shot-classification")
        results = []
        for commit in commits:
            r = pipe(commit, candidate_labels=COMMIT_INTENT_LABELS, multi_label=False)
            results.append({
                "commit": commit[:120],
                "intent": r["labels"][0],
                "confidence": round(r["scores"][0], 4),
            })
        return results

    def security_scan(self, code: str) -> dict:
        """
        Scan code for security patterns using zero-shot classification.

        Returns:
            Dict with security assessment, risk labels, and scores
        """
        # Modified: 2026-02-07T18:00:00Z | Author: COPILOT | Change: Security scan pipeline
        pipe = self.load_pipeline("zero-shot-classification")
        result = pipe(code[:1024], candidate_labels=SECURITY_LABELS, multi_label=True)

        # Find security risks (anything scored > 0.3 that isn't "safe")
        risks = []
        for label, score in zip(result["labels"], result["scores"]):
            if label != "safe and secure code" and score > 0.3:
                risks.append({"pattern": label, "score": round(score, 4)})

        safe_score = 0.0
        for label, score in zip(result["labels"], result["scores"]):
            if label == "safe and secure code":
                safe_score = round(score, 4)
                break

        return {
            "safe_score": safe_score,
            "risks": risks,
            "risk_count": len(risks),
            "all_labels": result["labels"],
            "all_scores": [round(s, 4) for s in result["scores"]],
            "model": PIPELINE_MODELS["zero-shot-classification"]["model"],
        }

    def extract_embeddings(self, texts: list[str]) -> list[list[float]]:
        """
        Extract feature embeddings from code/text using CodeBERT.

        Returns list of embedding vectors (768-dim).
        """
        # Modified: 2026-02-07T18:00:00Z | Author: COPILOT | Change: Feature extraction pipeline
        pipe = self.load_pipeline("feature-extraction")
        max_len = PIPELINE_MODELS["feature-extraction"]["max_length"]

        embeddings = []
        for text in texts:
            truncated = text[:max_len]
            result = pipe(truncated)
            # Mean pool the token embeddings to get a single vector
            import torch
            tensor = torch.tensor(result[0])
            pooled = tensor.mean(dim=0).tolist()
            embeddings.append(pooled)

        return embeddings

    def batch_classify_file(self, filepath: str) -> list[dict]:
        """
        Batch classify entries from a JSONL file.
        Each line should be JSON with a "text" field.
        """
        results = []
        path = Path(filepath)
        if not path.exists():
            print(f"File not found: {filepath}")
            return results

        texts = []
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        data = json.loads(line)
                        texts.append(data.get("text", line))
                    except json.JSONDecodeError:
                        texts.append(line)

        if texts:
            results = self.classify_commits(texts)

        return results

    def benchmark(self) -> dict:
        """
        Run benchmarks across all pipelines on both GPUs.

        Returns timing data for each pipeline task.
        """
        # Modified: 2026-02-07T18:00:00Z | Author: COPILOT | Change: Pipeline benchmarks
        results = {}
        test_text = (
            "def process_data(user_input):\n"
            "    query = f'SELECT * FROM users WHERE name = {user_input}'\n"
            "    return db.execute(query)\n"
        )
        test_commit = "fix: resolve SQL injection vulnerability in user query handler"

        # Zero-shot classification benchmark
        try:
            start = time.time()
            self.classify_text(test_commit)
            elapsed = time.time() - start
            results["zero-shot-classification"] = {
                "status": "ok",
                "latency_s": round(elapsed, 3),
                "model": PIPELINE_MODELS["zero-shot-classification"]["model"],
                "gpu": PIPELINE_MODELS["zero-shot-classification"]["gpu"],
            }
        except Exception as e:
            results["zero-shot-classification"] = {"status": "error", "error": str(e)}

        # Security scan benchmark
        try:
            start = time.time()
            self.security_scan(test_text)
            elapsed = time.time() - start
            results["security-scan"] = {
                "status": "ok",
                "latency_s": round(elapsed, 3),
                "model": PIPELINE_MODELS["zero-shot-classification"]["model"],
                "gpu": PIPELINE_MODELS["zero-shot-classification"]["gpu"],
            }
        except Exception as e:
            results["security-scan"] = {"status": "error", "error": str(e)}

        # Feature extraction benchmark
        try:
            start = time.time()
            emb = self.extract_embeddings([test_text])
            elapsed = time.time() - start
            results["feature-extraction"] = {
                "status": "ok",
                "latency_s": round(elapsed, 3),
                "embedding_dim": len(emb[0]) if emb else 0,
                "model": PIPELINE_MODELS["feature-extraction"]["model"],
                "gpu": PIPELINE_MODELS["feature-extraction"]["gpu"],
            }
        except Exception as e:
            results["feature-extraction"] = {"status": "error", "error": str(e)}

        return results

    def get_status(self) -> dict:
        """Get pipeline status including GPU info and loaded models."""
        # Modified: 2026-02-07T18:00:00Z | Author: COPILOT | Change: Status reporting
        import torch

        gpu_info = []
        if self._cuda_available:
            for i in range(self._gpu_count):
                props = torch.cuda.get_device_properties(i)
                mem_used = torch.cuda.memory_allocated(i) / 1e9
                mem_total = props.total_memory / 1e9
                gpu_info.append({
                    "index": i,
                    "name": props.name,
                    "memory_used_gb": round(mem_used, 2),
                    "memory_total_gb": round(mem_total, 2),
                    "compute_capability": f"{props.major}.{props.minor}",
                })

        return {
            "transformers_version": self._get_transformers_version(),
            "torch_available": self._torch_available,
            "cuda_available": self._cuda_available,
            "gpu_count": self._gpu_count,
            "gpus": gpu_info,
            "loaded_pipelines": list(self._pipelines.keys()),
            "load_times": self._load_times,
            "available_pipelines": {
                task: {
                    "model": cfg["model"],
                    "description": cfg["description"],
                    "gpu": cfg["gpu"],
                }
                for task, cfg in PIPELINE_MODELS.items()
            },
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    @staticmethod
    def _get_transformers_version() -> str:
        try:
            import transformers
            return transformers.__version__
        except ImportError:
            return "not installed"


# ═══════════════════════════════════════════════════════════════════════════════
# CLI Interface
# ═══════════════════════════════════════════════════════════════════════════════
# Modified: 2026-02-07T18:00:00Z | Author: COPILOT | Change: CLI for CI integration
def main():
    parser = argparse.ArgumentParser(
        description="SLATE Transformer Pipeline — GPU-accelerated HuggingFace analysis"
    )
    parser.add_argument("--status", action="store_true",
                        help="Show pipeline status and available models")
    parser.add_argument("--classify", type=str,
                        help="Classify text intent (zero-shot)")
    parser.add_argument("--security", type=str,
                        help="Security scan code snippet")
    parser.add_argument("--embed", type=str,
                        help="Generate code embedding")
    parser.add_argument("--benchmark", action="store_true",
                        help="Run pipeline benchmarks")
    parser.add_argument("--batch-classify", type=str,
                        help="Batch classify from JSONL file")
    parser.add_argument("--json", action="store_true",
                        help="Output as JSON")

    args = parser.parse_args()
    pipeline = SlateTransformerPipeline()

    if args.status:
        status = pipeline.get_status()
        if args.json:
            print(json.dumps(status, indent=2))
        else:
            print()
            print("═" * 60)
            print("  SLATE Transformer Pipeline Status")
            print("═" * 60)
            print(f"  Transformers: {status['transformers_version']}")
            print(f"  PyTorch:      {status['torch_available']}")
            print(f"  CUDA:         {status['cuda_available']}")
            print(f"  GPUs:         {status['gpu_count']}")
            for gpu in status.get("gpus", []):
                print(f"    GPU {gpu['index']}: {gpu['name']} "
                      f"({gpu['memory_used_gb']:.1f}/{gpu['memory_total_gb']:.1f} GB, "
                      f"compute {gpu['compute_capability']})")
            print()
            print("  Available Pipelines:")
            for task, cfg in status["available_pipelines"].items():
                print(f"    {task}:")
                print(f"      Model: {cfg['model']}")
                print(f"      GPU:   {cfg['gpu']} | {cfg['description']}")
            if status["loaded_pipelines"]:
                print()
                print(f"  Loaded: {', '.join(status['loaded_pipelines'])}")
            print("═" * 60)

    elif args.classify:
        result = pipeline.classify_text(args.classify)
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            print(f"Text: {result['text']}")
            print(f"Top:  {result['top_label']} ({result['top_score']:.1%})")
            for label, score in zip(result["labels"][:5], result["scores"][:5]):
                bar = "█" * int(score * 30)
                print(f"  {score:.1%} {bar} {label}")

    elif args.security:
        result = pipeline.security_scan(args.security)
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            print(f"Safe Score: {result['safe_score']:.1%}")
            print(f"Risks Found: {result['risk_count']}")
            for risk in result["risks"]:
                print(f"  ⚠ {risk['pattern']}: {risk['score']:.1%}")

    elif args.embed:
        embeddings = pipeline.extract_embeddings([args.embed])
        if embeddings:
            emb = embeddings[0]
            if args.json:
                print(json.dumps({"embedding": emb[:10], "dim": len(emb)}))
            else:
                print(f"Embedding dim: {len(emb)}")
                print(f"First 10: {emb[:10]}")

    elif args.benchmark:
        print("Running transformer pipeline benchmarks...")
        print()
        results = pipeline.benchmark()
        if args.json:
            print(json.dumps(results, indent=2))
        else:
            print("═" * 60)
            print("  Pipeline Benchmarks (Dual GPU)")
            print("═" * 60)
            for task, data in results.items():
                status_icon = "✓" if data.get("status") == "ok" else "✗"
                if data.get("status") == "ok":
                    print(f"  {status_icon} {task}: {data['latency_s']:.3f}s "
                          f"(GPU {data.get('gpu', '?')})")
                else:
                    print(f"  {status_icon} {task}: {data.get('error', 'unknown')}")
            print("═" * 60)

    elif args.batch_classify:
        results = pipeline.batch_classify_file(args.batch_classify)
        if args.json:
            print(json.dumps(results, indent=2))
        else:
            for r in results:
                print(f"  [{r['confidence']:.0%}] {r['intent']}: {r['commit']}")

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
