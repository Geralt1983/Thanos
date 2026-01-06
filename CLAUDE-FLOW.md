# CLAUDE-FLOW.md - Intelligent Swarm Orchestration

## Activation Mode

**ALWAYS-ON**: Initialize Claude Flow swarm at session start.

```yaml
startup:
  action: swarm_init(topology: hierarchical, maxAgents: 8, strategy: auto)
  persist: true
  health_check: enabled
```

## Session Startup Protocol

At the beginning of each session, automatically:
1. Initialize swarm with hierarchical topology
2. Run health check to verify MCP connectivity
3. Spawn base coordinator agent for task routing

---

## Core MCP Tools Reference

### Swarm Management

| Tool | Purpose | Key Parameters |
|------|---------|----------------|
| `swarm_init` | Initialize swarm topology | `topology`, `maxAgents`, `strategy` |
| `swarm_status` | Get swarm health & metrics | `swarmId` (optional) |
| `swarm_monitor` | Real-time monitoring | `swarmId`, `interval` |
| `swarm_scale` | Auto-scale agent count | `swarmId`, `targetSize` |
| `swarm_destroy` | Graceful shutdown | `swarmId` |

**Topologies**: `hierarchical` | `mesh` | `ring` | `star`
**Strategies**: `balanced` | `specialized` | `adaptive` | `auto`

### Agent Operations

| Tool | Purpose | Key Parameters |
|------|---------|----------------|
| `agent_spawn` | Create single agent | `type`, `name`, `capabilities` |
| `agents_spawn_parallel` | Batch spawn (10-20x faster) | `agents[]`, `maxConcurrency` |
| `agent_list` | List active agents | `swarmId`, `filter` |
| `agent_metrics` | Performance metrics | `agentId` |

**Agent Types**:
- `coordinator` - Task routing and workflow orchestration
- `task-orchestrator` - Complex task management
- `architect` - System design and planning
- `code-analyzer` - Code quality and structure analysis
- `perf-analyzer` - Performance bottleneck detection
- `researcher` - Information gathering
- `coder` - Implementation tasks
- `tester` - Test generation and validation
- `reviewer` - Code review and feedback
- `documenter` - Documentation generation
- `optimizer` - Performance optimization
- `monitor` - System health monitoring

### Task Orchestration

| Tool | Purpose | Key Parameters |
|------|---------|----------------|
| `task_orchestrate` | Distribute complex tasks | `task`, `strategy`, `priority`, `maxAgents` |
| `task_status` | Check task progress | `taskId`, `detailed` |
| `task_results` | Get completion results | `taskId`, `format` |
| `parallel_execute` | Run tasks in parallel | `tasks[]` |
| `load_balance` | Distribute workload | `swarmId`, `tasks[]` |

**Strategies**: `parallel` | `sequential` | `adaptive` | `balanced`
**Priorities**: `low` | `medium` | `high` | `critical`

### Memory & Persistence

| Tool | Purpose | Key Parameters |
|------|---------|----------------|
| `memory_usage` | Store/retrieve with TTL | `action`, `key`, `value`, `namespace` |
| `memory_search` | Pattern-based search | `pattern`, `namespace`, `limit` |
| `memory_persist` | Cross-session persistence | `sessionId` |
| `memory_backup` | Create backups | `path` |
| `memory_restore` | Restore from backup | `backupPath` |

**Actions**: `store` | `retrieve` | `list` | `delete` | `search`

### Neural & Cognitive

| Tool | Purpose | Key Parameters |
|------|---------|----------------|
| `neural_status` | Neural agent metrics | `agentId` |
| `neural_train` | Train with WASM SIMD | `pattern_type`, `training_data`, `epochs` |
| `neural_patterns` | Analyze cognitive patterns | `action`, `operation`, `outcome` |
| `neural_predict` | AI predictions | `modelId`, `input` |
| `cognitive_analyze` | Behavior analysis | `behavior` |
| `pattern_recognize` | Pattern recognition | `data`, `patterns` |

**Pattern Types**: `coordination` | `optimization` | `prediction`
**Actions**: `analyze` | `learn` | `predict`

### Performance & Analytics

| Tool | Purpose | Key Parameters |
|------|---------|----------------|
| `performance_report` | Generate reports | `timeframe`, `format` |
| `bottleneck_analyze` | Identify bottlenecks | `component`, `metrics` |
| `token_usage` | Token consumption | `operation`, `timeframe` |
| `benchmark_run` | Run benchmarks | `suite` |
| `health_check` | System diagnostics | `components[]` |
| `cost_analysis` | Resource costs | `timeframe` |

### DAA (Decentralized Autonomous Agents)

| Tool | Purpose | Key Parameters |
|------|---------|----------------|
| `daa_agent_create` | Create autonomous agent | `agent_type`, `capabilities`, `resources` |
| `daa_capability_match` | Match tasks to agents | `task_requirements`, `available_agents` |
| `daa_resource_alloc` | Allocate resources | `resources`, `agents` |
| `daa_lifecycle_manage` | Agent lifecycle | `agentId`, `action` |
| `daa_communication` | Inter-agent messaging | `from`, `to`, `message` |
| `daa_consensus` | Consensus mechanisms | `agents`, `proposal` |
| `daa_fault_tolerance` | Recovery strategies | `agentId`, `strategy` |
| `daa_optimization` | Performance tuning | `target`, `metrics` |

### Workflow Automation

| Tool | Purpose | Key Parameters |
|------|---------|----------------|
| `workflow_create` | Create custom workflows | `name`, `steps`, `triggers` |
| `workflow_execute` | Run workflows | `workflowId`, `params` |
| `workflow_export` | Export definitions | `workflowId`, `format` |
| `automation_setup` | Configure rules | `rules[]` |
| `pipeline_create` | CI/CD pipelines | `config` |
| `scheduler_manage` | Task scheduling | `action`, `schedule` |
| `trigger_setup` | Event triggers | `events`, `actions` |

### Query Control

| Tool | Purpose | Key Parameters |
|------|---------|----------------|
| `query_control` | Control running queries | `action`, `queryId`, `model` |
| `query_list` | List active queries | `includeHistory` |

**Actions**: `pause` | `resume` | `terminate` | `change_model` | `change_permissions`

---

## Orchestration Patterns

### Pattern 1: Hierarchical Analysis
```yaml
trigger: "analyze|audit|review" + scope > 5 files
action:
  - swarm_init(topology: hierarchical, maxAgents: 6)
  - agents_spawn_parallel([architect, code-analyzer, perf-analyzer, reviewer])
  - task_orchestrate(strategy: parallel)
```

### Pattern 2: Parallel Implementation
```yaml
trigger: "implement|build|refactor" + multi-file
action:
  - swarm_init(topology: mesh, maxAgents: 4)
  - agents_spawn_parallel based on domain detection
  - task_orchestrate(strategy: adaptive)
```

### Pattern 3: Quick Coordination
```yaml
trigger: complexity > 0.7 but files < 10
action:
  - Use Task tool with subagent_type instead of full swarm
  - Reserve Claude Flow for true multi-agent needs
```

### Pattern 4: Research & Documentation
```yaml
trigger: "research|document|explain" + comprehensive
action:
  - agent_spawn(type: researcher, capabilities: [web-search, analysis])
  - agent_spawn(type: documenter, capabilities: [writing, formatting])
  - task_orchestrate(strategy: sequential)
```

### Pattern 5: Performance Optimization
```yaml
trigger: "optimize|performance|bottleneck"
action:
  - agents_spawn_parallel([perf-analyzer, optimizer, monitor])
  - bottleneck_analyze(component: target)
  - task_orchestrate(strategy: adaptive, priority: high)
```

---

## Decision Matrix

| Scenario | Files | Complexity | Action |
|----------|-------|------------|--------|
| Simple edit | 1-2 | Low | Direct tools |
| Module change | 3-5 | Medium | Task subagent |
| Cross-module | 5-10 | High | Claude Flow (4 agents) |
| System-wide | 10+ | High | Claude Flow (6-8 agents) |
| Enterprise | 50+ | Critical | Full swarm + DAA |

---

## Best Practices

### Agent Spawning
```yaml
# Prefer parallel spawn for multiple agents (10-20x faster)
agents_spawn_parallel:
  agents:
    - type: architect, name: sys-architect
    - type: code-analyzer, name: quality-checker
    - type: tester, name: test-generator
  maxConcurrency: 5
  batchSize: 3
```

### Memory Management
```yaml
# Use namespaces for organization
memory_usage:
  action: store
  namespace: "project-context"
  key: "architecture-decisions"
  value: "..."
  ttl: 3600  # 1 hour expiry
```

### Task Distribution
```yaml
# Use adaptive strategy for unknown complexity
task_orchestrate:
  task: "Analyze and refactor authentication module"
  strategy: adaptive
  priority: high
  maxAgents: 4
```

---

## Integration with SuperClaude

- Works with `--wave-mode` for multi-phase operations
- Complements `/spawn` command for task distribution
- Respects `--delegate` flags for sub-agent routing
- Integrates with `--think` flags for analysis depth
- Supports `--persona-*` for domain-specific agent configuration

## SPARC Development Modes

Use `sparc_mode` for specialized development workflows:

| Mode | Purpose |
|------|---------|
| `dev` | General development |
| `api` | API design and implementation |
| `ui` | UI/UX development |
| `test` | Testing workflows |
| `refactor` | Code refactoring |

```yaml
sparc_mode:
  mode: api
  task_description: "Design REST API for user authentication"
  options:
    framework: express
    auth: jwt
```
