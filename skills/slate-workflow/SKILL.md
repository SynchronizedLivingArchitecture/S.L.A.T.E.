# /slate-workflow

Manage the SLATE task workflow queue and monitor task health.

## Usage
/slate-workflow [--status | --cleanup | --enforce]

## Description
This skill manages the SLATE workflow system which tracks tasks through their lifecycle:
- View current task queue and status
- Identify stale, abandoned, or duplicate tasks
- Clean up problematic tasks automatically
- Enforce workflow rules (max concurrent tasks)

## Instructions

When the user invokes this skill:

**For status check (default):**
```powershell
.\.venv\Scripts\python.exe slate/slate_workflow_manager.py --status
```

**For cleanup:**
```powershell
.\.venv\Scripts\python.exe slate/slate_workflow_manager.py --cleanup
```

**For enforcement check:**
```powershell
.\.venv\Scripts\python.exe slate/slate_workflow_manager.py --enforce
```

Report findings including:
1. Number of tasks by status (pending, in_progress, completed)
2. Stale tasks (in-progress > 4 hours)
3. Abandoned tasks (pending > 24 hours)
4. Duplicate tasks detected
5. Whether new tasks can be accepted

## Automatic Rules
- **Stale** (in-progress > 4h) → auto-reset to pending
- **Abandoned** (pending > 24h) → flagged for review
- **Duplicates** → auto-archived
- **Max concurrent** → 5 tasks before blocking

## Examples

User: "/slate-workflow"
→ Show current workflow status

User: "/slate-workflow --cleanup"
→ Auto-clean stale and duplicate tasks

User: "Are there any stuck tasks?"
→ Check for stale/abandoned tasks
