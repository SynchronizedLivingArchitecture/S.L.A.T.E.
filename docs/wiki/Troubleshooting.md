# Troubleshooting

Common issues and their solutions.

## Quick Diagnostics

Run these commands to identify issues:

```bash
# System status
python aurora_core/slatepi_status.py --quick

# Check all integrations
python aurora_core/slatepi_runtime.py --check-all

# Test Ollama connection
curl http://127.0.0.1:11434/api/tags
```

## Ollama Issues

### Ollama Not Running

**Symptoms:**
- Connection refused on port 11434
- "Could not connect to Ollama" errors

**Solutions:**

```bash
# Start Ollama service
ollama serve

# Or on Windows, run the Ollama application

# Verify it's running
curl http://127.0.0.1:11434/api/tags
```

### No Models Available

**Symptoms:**
- Empty model list
- "Model not found" errors

**Solutions:**

```bash
# List available models
ollama list

# Pull recommended model
ollama pull mistral-nemo

# Verify model is loaded
ollama list
```

### Model Load Failures

**Symptoms:**
- "Out of memory" errors
- Model loading hangs

**Solutions:**

```bash
# Check GPU memory
nvidia-smi

# Use a smaller model
ollama pull phi:latest  # Only 1.6GB

# Unload other models
ollama rm unused-model
```

## GPU Issues

### GPU Not Detected

**Symptoms:**
- "No CUDA devices found"
- Operations falling back to CPU

**Solutions:**

```bash
# Check NVIDIA driver
nvidia-smi

# Check CUDA installation
nvcc --version

# Verify PyTorch CUDA
python -c "import torch; print(torch.cuda.is_available())"
```

### CUDA Version Mismatch

**Symptoms:**
- PyTorch CUDA errors
- "CUDA driver version is insufficient"

**Solutions:**

```bash
# Check versions
python aurora_core/slatepi_hardware_optimizer.py --verbose

# Reinstall PyTorch with correct CUDA
pip uninstall torch
pip install torch --index-url https://download.pytorch.org/whl/cu124
```

### Out of GPU Memory

**Symptoms:**
- CUDA out of memory errors
- Process crashes during inference

**Solutions:**

```python
# Reduce batch size in config
# Use smaller models
# Enable memory growth

# Clear GPU memory
import torch
torch.cuda.empty_cache()
```

## Import Errors

### Module Not Found

**Symptoms:**
- `ModuleNotFoundError: No module named 'aurora_core'`

**Solutions:**

```bash
# Ensure virtual environment is activated
.\.venv\Scripts\activate  # Windows
source .venv/bin/activate  # Linux/macOS

# Install in development mode
pip install -e .

# Add to PYTHONPATH
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
```

### Circular Import

**Symptoms:**
- `ImportError: cannot import name 'X' from partially initialized module`

**Solutions:**

```python
# Move import inside function
def my_function():
    from aurora_core.other_module import something
    ...

# Or use TYPE_CHECKING
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from aurora_core.other_module import SomeClass
```

## Dashboard Issues

### Dashboard Won't Start

**Symptoms:**
- Port already in use
- Server fails to bind

**Solutions:**

```bash
# Check if port is in use
netstat -an | findstr 8080  # Windows
lsof -i :8080               # Linux/macOS

# Kill existing process
taskkill /F /PID <pid>      # Windows
kill -9 <pid>               # Linux/macOS

# Use different port
python agents/aurora_dashboard_server.py --port 9000
```

### Dashboard Not Loading

**Symptoms:**
- Blank page in browser
- JavaScript errors

**Solutions:**

```bash
# Clear browser cache
# Try incognito/private window
# Check browser console for errors (F12)

# Verify server is responding
curl http://127.0.0.1:8080/api/status
```

## Task Queue Issues

### Tasks Not Processing

**Symptoms:**
- Tasks stuck in pending
- No agent picking up tasks

**Solutions:**

```bash
# Check task queue
python aurora_core/slatepi_status.py --tasks

# Verify agents are running
python aurora_core/slatepi_status.py

# Check for file lock issues
# Delete stale lock files if present
```

### Corrupted Task File

**Symptoms:**
- JSON parse errors
- Task operations fail

**Solutions:**

```bash
# Backup current file
cp current_tasks.json current_tasks.json.bak

# Reset to empty queue
echo '{"tasks": []}' > current_tasks.json
```

## Foundry Local Issues

### Foundry Not Available

**Symptoms:**
- Connection refused on port 5272
- "Foundry not found" errors

**Solutions:**

```bash
# Check if Foundry is installed
foundry --version

# Start Foundry service
foundry serve

# Verify connection
curl http://127.0.0.1:5272/health
```

### Model Download Fails

**Symptoms:**
- Download hangs or fails
- Insufficient disk space

**Solutions:**

```bash
# Check disk space
df -h  # Linux/macOS
wmic logicaldisk get size,freespace,caption  # Windows

# Retry download
foundry model download microsoft/Phi-3.5-mini-instruct-onnx

# Check Foundry logs
```

## Test Failures

### Tests Hang

**Symptoms:**
- Tests never complete
- Timeout errors

**Solutions:**

```bash
# Run with timeout
python -m pytest tests/ --timeout=30

# Run specific test
python -m pytest tests/test_greeting.py -v

# Check for blocking I/O or network calls
```

### Import Errors in Tests

**Symptoms:**
- Tests fail before running
- Module import failures

**Solutions:**

```bash
# Run from project root
cd /path/to/slate

# Check PYTHONPATH
python -c "import sys; print(sys.path)"

# Install in editable mode
pip install -e ".[dev]"
```

## ChromaDB Issues

### Vector Store Corruption

**Symptoms:**
- ChromaDB errors on startup
- Query failures

**Solutions:**

```bash
# Backup and reset
mv .slate_index .slate_index.bak
python -c "from aurora_core import init_chroma; init_chroma()"
```

### Embedding Dimension Mismatch

**Symptoms:**
- "Embedding dimension mismatch" errors

**Solutions:**

```python
# Reset collection with correct dimensions
import chromadb
client = chromadb.PersistentClient(path=".slate_index")
client.delete_collection("slate_memory")
# Reinitialize
```

## Performance Issues

### Slow Inference

**Symptoms:**
- Long response times
- High latency

**Solutions:**

```bash
# Check GPU utilization
nvidia-smi -l 1

# Use faster model
ollama pull phi:latest

# Enable caching
# Check slate_cache/ is being used
```

### High Memory Usage

**Symptoms:**
- System slowdown
- Out of memory errors

**Solutions:**

```bash
# Monitor memory
top  # Linux
taskmgr  # Windows

# Reduce concurrent tasks
# Use smaller models
# Restart services to clear memory
```

## Getting More Help

### Collect Diagnostic Info

```bash
# Full system report
python aurora_core/slatepi_status.py > status.txt
python aurora_core/slatepi_runtime.py --check-all >> status.txt
python aurora_core/slatepi_hardware_optimizer.py --verbose >> status.txt
```

### Log Files

Check these locations for detailed logs:
- `.slate_errors/` - Error logs with context
- Console output - Real-time logging
- `slate_cache/` - Cached responses (may indicate issues)

### Reset to Clean State

If all else fails:

```bash
# Backup important data
cp current_tasks.json tasks_backup.json

# Clean caches
rm -rf slate_cache/
rm -rf .slate_index/
rm -rf .slate_errors/

# Reinstall dependencies
pip install -e ".[dev]" --force-reinstall

# Verify
python aurora_core/slatepi_status.py --quick
```

## Next Steps

- [Configuration](Configuration) - Check your settings
- [CLI Reference](CLI-Reference) - Command documentation
- [Development](Development) - Contributing guide
