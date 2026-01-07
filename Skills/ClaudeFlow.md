# Claude Flow Shortcuts

## Natural Language Routing

When Jeremy says → Do this:

### Swarm Commands
- **"CF status"** / **"swarm status"** → `swarm_status` + `health_check`
- **"CF init"** / **"spin up swarm"** → `swarm_init(topology: hierarchical, maxAgents: 8)`
- **"CF kill"** / **"shutdown swarm"** → `swarm_destroy`

### Agent Commands
- **"spawn [type]"** → `agent_spawn(type: [type])`
- **"spawn team for [task]"** → `agents_spawn_parallel` with context-appropriate agents
- **"who's active"** / **"list agents"** → `agent_list`

### Task Commands
- **"CF run [task]"** / **"orchestrate [task]"** → `task_orchestrate(task: [task], strategy: adaptive)`
- **"task status"** → `task_status`
- **"parallel [tasks]"** → `parallel_execute`

### Memory Commands
- **"CF remember [key]: [value]"** → `memory_usage(action: store, key, value, namespace: thanos)`
- **"CF recall [key]"** → `memory_usage(action: retrieve, key, namespace: thanos)`
- **"CF search [pattern]"** → `memory_search(pattern)`
- **"CF save session"** → `memory_persist`

### Performance Commands
- **"CF perf"** / **"CF report"** → `performance_report(timeframe: 24h, format: summary)`
- **"CF benchmark"** → `benchmark_run`
- **"CF bottlenecks"** → `bottleneck_analyze`

### Neural Commands
- **"CF neural"** → `neural_status`
- **"CF patterns"** → `neural_patterns(action: analyze)`

## Agent Type Shortcuts
- **"architect"** → system-architect
- **"analyzer"** → code-analyzer
- **"perf"** → perf-analyzer
- **"reviewer"** → reviewer
- **"tester"** → tester
- **"docs"** → documenter

## Examples
- "CF status" → Full health check
- "spawn team for code review" → Spawns architect + analyzer + reviewer
- "CF remember decision-auth: went with JWT" → Stores in thanos namespace
- "CF recall decision-auth" → Retrieves it
- "CF run analyze the auth module" → Orchestrates analysis task
