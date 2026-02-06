# Agent System

SLATE uses a multi-agent architecture where specialized agents handle different types of tasks.

## Agent Overview

| Agent | Role | Hardware | Specialization |
|-------|------|----------|----------------|
| **ALPHA** | Implementation | GPU-preferred | Code generation, refactoring, bug fixes |
| **BETA** | Validation | GPU-preferred | Testing, code review, security analysis |
| **GAMMA** | Planning | CPU-preferred | Architecture, research, documentation |
| **DELTA** | Integration | API-based | External service coordination |

## ALPHA Agent

The primary coding agent, optimized for implementation tasks.

### Capabilities
- Code generation from specifications
- Bug fixing and debugging
- Code refactoring
- Feature implementation
- API development

### Best For
```
- "Implement user authentication"
- "Fix the login bug"
- "Refactor the database layer"
- "Add dark mode support"
```

### Configuration
```python
ALPHA_CONFIG = {
    "model_preference": "mistral-nemo",
    "temperature": 0.2,  # Lower for more deterministic code
    "max_tokens": 4096,
    "hardware": "GPU_PREFERRED"
}
```

## BETA Agent

The testing and validation agent.

### Capabilities
- Test case generation
- Code review
- Security vulnerability detection
- Performance analysis
- Quality assurance

### Best For
```
- "Write tests for the auth module"
- "Review this pull request"
- "Check for security issues"
- "Analyze performance bottlenecks"
```

### Configuration
```python
BETA_CONFIG = {
    "model_preference": "mistral-nemo",
    "temperature": 0.3,
    "max_tokens": 2048,
    "hardware": "GPU_PREFERRED"
}
```

## GAMMA Agent

The planning and research agent.

### Capabilities
- Architecture design
- Technical research
- Documentation writing
- Project planning
- Requirement analysis

### Best For
```
- "Design the authentication system"
- "Research best practices for caching"
- "Document the API endpoints"
- "Plan the sprint tasks"
```

### Configuration
```python
GAMMA_CONFIG = {
    "model_preference": "phi",  # Lightweight, fast
    "temperature": 0.5,  # More creative for planning
    "max_tokens": 2048,
    "hardware": "CPU_PREFERRED"
}
```

## DELTA Agent

The integration agent for external services.

### Capabilities
- External API coordination
- Service integration
- Webhook handling
- Cross-system communication

### Best For
```
- "Integrate with Slack notifications"
- "Connect to the payment gateway"
- "Set up GitHub webhooks"
```

### Configuration
```python
DELTA_CONFIG = {
    "model_preference": "external",  # Uses API when needed
    "temperature": 0.2,
    "max_tokens": 1024,
    "hardware": "API_BASED"
}
```

## Task Routing

### Automatic Routing

Tasks are automatically routed based on content analysis:

```python
from aurora_core import create_task

# Automatically routes to ALPHA (implementation task)
task = create_task(
    title="Implement login endpoint",
    description="Add POST /api/login with JWT"
)
print(f"Assigned to: {task.assigned_to}")  # ALPHA

# Automatically routes to BETA (testing task)
task = create_task(
    title="Write tests for auth",
    description="Unit tests for authentication module"
)
print(f"Assigned to: {task.assigned_to}")  # BETA
```

### Manual Assignment

```python
task = create_task(
    title="Design new feature",
    description="...",
    assigned_to="GAMMA"  # Force specific agent
)
```

### Routing Rules

```
Keywords → Agent
─────────────────────────────
implement, fix, build, code, add → ALPHA
test, review, check, verify, validate → BETA
design, plan, research, document, analyze → GAMMA
integrate, connect, webhook, external → DELTA
```

## Task Management

### Task States

```
PENDING → IN_PROGRESS → COMPLETED
              │
              └──→ FAILED
              │
              └──→ BLOCKED (dependencies)
              │
              └──→ TIMEOUT
```

### Task Priority

| Priority | Description | SLA |
|----------|-------------|-----|
| 1 | Critical | Immediate |
| 2 | High | < 1 hour |
| 3 | Normal | < 4 hours |
| 4 | Low | < 24 hours |
| 5 | Background | Best effort |

### Task Structure

```json
{
  "id": "task_20260206_abc123",
  "title": "Implement user registration",
  "description": "Create POST /api/register endpoint...",
  "status": "pending",
  "priority": 2,
  "assigned_to": "ALPHA",
  "created_at": "2026-02-06T12:00:00Z",
  "dependencies": [],
  "files_affected": ["src/api/auth.py"],
  "complexity_score": 45,
  "estimated_tokens": 2000
}
```

## Agent Communication

### Event-Based

Agents communicate through the message broker:

```python
from aurora_core import get_broker, create_event

broker = get_broker()

# ALPHA completes task, notifies BETA
broker.publish("agent_events", create_event(
    event_type="task_completed",
    source="ALPHA",
    data={
        "task_id": "t001",
        "files_changed": ["src/api/auth.py"],
        "needs_tests": True
    }
))

# BETA receives and creates test task
def on_task_completed(event):
    if event.data.get("needs_tests"):
        create_task(
            title=f"Write tests for {event.data['task_id']}",
            assigned_to="BETA"
        )

broker.subscribe("agent_events", on_task_completed)
```

### Handoff Protocol

When agents need to pass work:

```python
from aurora_core import handoff_task

# ALPHA hands off to BETA for review
handoff_task(
    task_id="t001",
    from_agent="ALPHA",
    to_agent="BETA",
    context={
        "code_changes": ["..."],
        "test_hints": ["..."]
    }
)
```

## Load Balancing

### Strategy Options

```python
from aurora_core import get_load_balancer, BalancingStrategy

balancer = get_load_balancer()

# Round-robin (default)
balancer.set_strategy(BalancingStrategy.ROUND_ROBIN)

# Least loaded agent
balancer.set_strategy(BalancingStrategy.LEAST_LOADED)

# Resource-aware (considers GPU/memory)
balancer.set_strategy(BalancingStrategy.RESOURCE_AWARE)
```

### Agent Health Monitoring

```python
from aurora_core import get_agent_health

health = get_agent_health("ALPHA")
print(f"Status: {health.status}")
print(f"Tasks completed: {health.tasks_completed}")
print(f"Error rate: {health.error_rate}%")
print(f"Avg response time: {health.avg_response_time}ms")
```

## Best Practices

### 1. Task Granularity

Break large tasks into smaller, focused tasks:

```python
# Good - specific and focused
create_task(title="Implement JWT token generation")
create_task(title="Add token validation middleware")
create_task(title="Create refresh token endpoint")

# Avoid - too broad
create_task(title="Implement authentication")
```

### 2. Dependencies

Specify dependencies to ensure proper ordering:

```python
task1 = create_task(title="Create user model")
task2 = create_task(
    title="Add user registration",
    dependencies=[task1.id]
)
```

### 3. Context Passing

Provide relevant context for better results:

```python
create_task(
    title="Fix login error",
    description="""
    Error: "Invalid credentials" even with correct password

    Relevant files:
    - src/api/auth.py (line 45)
    - src/models/user.py

    User report: Started after password reset feature was added
    """
)
```

## Next Steps

- [Configure AI Backends](AI-Backends)
- [CLI Reference](CLI-Reference)
- [Troubleshooting](Troubleshooting)
