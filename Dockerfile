# S.L.A.T.E. Docker Image (GPU Variant)
# Base: NVIDIA CUDA 12.4 Runtime on Ubuntu 22.04
# Author: SLATE | Created: 2026-02-06

FROM nvidia/cuda:12.4.1-runtime-ubuntu22.04

LABEL org.opencontainers.image.source="https://github.com/SynchronizedLivingArchitecture/S.L.A.T.E"
LABEL org.opencontainers.image.description="SLATE - Synchronized Living Architecture for Transformation and Evolution (GPU)"
LABEL org.opencontainers.image.licenses="MIT"

# Prevent interactive prompts during package installation
ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Install Python 3.11 and system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3.11 \
    python3.11-venv \
    python3.11-dev \
    python3-pip \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && ln -sf /usr/bin/python3.11 /usr/bin/python \
    && ln -sf /usr/bin/python3.11 /usr/bin/python3

# Set working directory
WORKDIR /slate

# Copy requirements first for layer caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# Copy SLATE codebase
COPY slate/ ./slate/
COPY agents/ ./agents/
COPY slate_core/ ./slate_core/
COPY pyproject.toml .
COPY current_tasks.json .
COPY .slate_tech_tree/ ./.slate_tech_tree/

# Set Python path
ENV PYTHONPATH="/slate:${PYTHONPATH}"

# Create non-root user for security
RUN useradd -m -s /bin/bash slate \
    && chown -R slate:slate /slate
USER slate

# Expose dashboard port
EXPOSE 8080

# Modified: 2026-02-07T09:00:00Z | Author: COPILOT | Change: Fix healthcheck to use Python instead of curl
# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8080/api/health', timeout=5)" || exit 1

# Default entrypoint: start SLATE orchestrator
ENTRYPOINT ["python", "slate/slate_orchestrator.py"]
CMD ["start", "--mode", "prod"]
