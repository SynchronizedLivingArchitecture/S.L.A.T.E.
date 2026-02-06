# Self-Hosted GitHub Actions Runners

SLATE supports self-hosted GitHub Actions runners for GPU-intensive CI/CD tasks. This guide covers setup, configuration, environment provisioning, and management.

## Overview

Self-hosted runners allow SLATE to:
- Run GPU-accelerated tests (CUDA, PyTorch)
- Execute full SLATE system validation locally
- Avoid GitHub-hosted runner time limits
- Use your local hardware (RTX 5070 Ti, etc.)
- Auto-start on boot with Windows Task Scheduler

## Prerequisites

- Windows 10/11 or Linux
- NVIDIA GPU with CUDA support
- Python 3.11+
- GitHub account with repo admin access

## Quick Setup

### Option A: Via SLATE Installer (Recommended)

```powershell
# Full install with runner setup
python install_slate.py --runner

# Full install with runner + auto-configure
python install_slate.py --runner --runner-token YOUR_TOKEN
```

The installer handles: download → configure → provision SLATE env → startup scripts.

### Option B: Via Runner Manager CLI

#### 1. Get Registration Token

1. Go to [S.L.A.T.E. Settings > Actions > Runners](https://github.com/SynchronizedLivingArchitecture/S.L.A.T.E./settings/actions/runners)
2. Click **New self-hosted runner**
3. Copy the registration token

#### 2. Run SLATE Runner Manager

```powershell
# Check current status
.\.venv\Scripts\python.exe aurora_core/slate_runner_manager.py --status

# Download the runner
.\.venv\Scripts\python.exe aurora_core/slate_runner_manager.py --download

# Configure with your token
.\.venv\Scripts\python.exe aurora_core/slate_runner_manager.py --configure --token YOUR_TOKEN

# Provision SLATE environment on runner
.\.venv\Scripts\python.exe aurora_core/slate_runner_manager.py --provision

# Create startup + auto-start scripts
.\.venv\Scripts\python.exe aurora_core/slate_runner_manager.py --create-startup

# Start the runner
.\.venv\Scripts\python.exe aurora_core/slate_runner_manager.py --start
```

#### 3. Verify Registration

Check GitHub Settings > Actions > Runners to see your runner listed as "Idle".

## SLATE Environment Provisioning

The `--provision` command sets up a complete SLATE environment on the runner:

| Step | Description |
|------|-------------|
| 1 | Verify SLATE workspace exists |
| 2 | Create/verify virtual environment |
| 3 | Install core dependencies from `requirements.txt` |
| 4 | Install test dependencies (`pytest`, `pytest-cov`) |
| 5 | Editable install of SLATE package |
| 6 | Verify GPU/CUDA availability |
| 7 | Validate SLATE SDK imports |
| 8 | Create runner environment script (`slate_env.ps1`/`.sh`) |
| 9 | Create pre-job hook for automatic env activation |
| 10 | Save provisioning state |

This ensures every GitHub Actions job on the runner has full access to:
- SLATE SDK (`aurora_core`)
- GPU/CUDA drivers
- All Python dependencies
- Correct environment variables

## Runner Labels

SLATE automatically detects and applies these labels:

| Label | Description |
|-------|-------------|
| `self-hosted` | Standard self-hosted label |
| `slate` | SLATE system runner |
| `gpu` | Has NVIDIA GPU |
| `cuda` | CUDA available |
| `windows` / `linux` | Operating system |
| `gpu-2` | Number of GPUs |
| `blackwell` | RTX 50 series (CC 12.x) |
| `ada-lovelace` | RTX 40 series (CC 8.9) |
| `ampere` | RTX 30 series (CC 8.x) |

## Startup Scripts & Auto-Start

### Creating Startup Scripts

```powershell
.\.venv\Scripts\python.exe aurora_core/slate_runner_manager.py --create-startup
```

This creates:
- **Windows**: `start-slate-runner.ps1` in the runner directory
- **Linux**: `start-slate-runner.sh` in the runner directory

The startup script activates the SLATE environment before launching the runner.

### Windows Auto-Start (Task Scheduler)

The `--create-startup` command also registers a Windows Task Scheduler task:

- **Task name**: `SLATE-Runner`
- **Trigger**: At system startup
- **Action**: Runs the startup script with SLATE env
- **Runs as**: Current user

```powershell
# View task
schtasks /Query /TN "SLATE-Runner" /FO LIST

# Disable auto-start
schtasks /Change /TN "SLATE-Runner" /DISABLE

# Re-enable
schtasks /Change /TN "SLATE-Runner" /ENABLE

# Remove
schtasks /Delete /TN "SLATE-Runner" /F
```

### Running as Windows Service

For persistent background operation without Task Scheduler:

```powershell
# Install and start as service (requires Admin)
.\.venv\Scripts\python.exe aurora_core/slate_runner_manager.py --start --service

# Stop the service
.\.venv\Scripts\python.exe aurora_core/slate_runner_manager.py --stop
```

## Pre-Job Hooks

The provisioning system creates a pre-job hook at `{runner_dir}/hooks/pre-job.ps1`. This hook:

1. Activates the SLATE virtual environment
2. Sets `SLATE_WORKSPACE`, `SLATE_RUNNER`, `PYTHONIOENCODING` environment variables
3. Runs before every job on the runner

## Workflows Using Self-Hosted Runners

### Dedicated Runner Workflow (`slate-runner.yml`)

Runs the complete SLATE system stack on self-hosted:

- Environment validation (GPU detection, SDK version)
- Core SLATE systems (status, runtime, hardware optimizer)
- Dashboard & API smoke tests
- Agent system validation
- GPU & CUDA tests (PyTorch compute)
- ML pipeline validation (nightly/manual)
- Package build validation

### Integration in Existing Workflows

`slate.yml` and `nightly.yml` include self-hosted GPU validation jobs with `continue-on-error: true`:

```yaml
jobs:
  gpu-slate-validation:
    runs-on: [self-hosted, slate, gpu, windows]
    continue-on-error: true
    steps:
      - uses: actions/checkout@v4
      # ... GPU-enabled steps
```

## CLI Reference

```
slate_runner_manager.py [OPTIONS]

Status & Info:
  --status              Show runner status
  --json                Output in JSON format

Setup:
  --download            Download GitHub Actions runner
  --configure           Configure runner (requires --token)
  --token TOKEN         GitHub registration token
  --repo URL            Repository URL (default: S.L.A.T.E.)
  --name NAME           Custom runner name

Environment:
  --provision           Provision SLATE environment on runner
  --workspace DIR       SLATE workspace directory

Startup:
  --create-startup      Create startup scripts + Windows auto-start
  --start               Start runner (interactive)
  --start --service     Start as Windows service
  --stop                Stop runner service

Utility:
  --setup-script        Generate manual setup script
  --runner-dir DIR      Override runner directory
```

## Security Considerations

- Self-hosted runners execute code from PRs
- Only enable for **private repos** or **trusted contributors**
- Runners have access to your local machine
- Use dedicated runner accounts when possible
- All SLATE operations are LOCAL ONLY (127.0.0.1)

### Recommended Security Settings

1. **Repository Settings > Actions > General**
   - "Require approval for all outside collaborators"

2. **Limit runner scope**
   - Register per-repository, not organization-wide

3. **Network isolation**
   - Runner binds to localhost only
   - ActionGuard blocks external API calls

## Troubleshooting

### Runner Not Appearing

```powershell
.\.venv\Scripts\python.exe aurora_core/slate_runner_manager.py --status
.\.venv\Scripts\python.exe aurora_core/slate_runner_manager.py --configure --token NEW_TOKEN
```

### Provisioning Failed

```powershell
.\.venv\Scripts\python.exe aurora_core/slate_runner_manager.py --provision
.\.venv\Scripts\python.exe aurora_core/slate_runner_manager.py --status --json
```

### GPU Not Detected

```powershell
nvidia-smi
python -c "import torch; print(torch.cuda.is_available())"
```

### Service Won't Start

```powershell
# Run interactively to see errors
.\.venv\Scripts\python.exe aurora_core/slate_runner_manager.py --start

# Check for existing runner process
Get-Process Runner.Listener -ErrorAction SilentlyContinue
```

## Related Documentation

- [Configuration.md](Configuration.md) - Environment setup
- [Development.md](Development.md) - Contributing guide
- [Releases.md](Releases.md) - Release process
- [Troubleshooting.md](Troubleshooting.md) - Common issues
