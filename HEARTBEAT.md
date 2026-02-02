# HEARTBEAT.md

## Memory Capture (Every Heartbeat)

Check if there's been meaningful conversation since last capture:

### 1. Graphiti (Knowledge Graph)
Push entities and relationships:
```bash
mcporter call "http://localhost:8000/sse.add_episode" \
  name="<descriptive name>" \
  episode_body="<facts and context>" \
  source_description="OpenClaw main session" \
  --allow-http
```

### 2. Memory V2 (Vector Store)
Push to semantic search:
```bash
mcporter call --stdio "node mcp-servers/memory-v2-mcp/dist/index.js" \
  thanos_memory_add \
  content="<memory content>" \
  source="openclaw" \
  memory_type="<fact|decision|pattern|note>"
```

### 3. Daily Notes
Update `memory/YYYY-MM-DD.md` with session notes.

### 4. Track State
Update `memory/heartbeat-state.json` with last capture timestamp.

---

## What to Capture

| Type | Graphiti | Memory V2 |
|------|----------|-----------|
| Decisions made | ✅ | ✅ |
| Technical learnings | ✅ | ✅ |
| People/relationships | ✅ | - |
| Entity connections | ✅ | - |
| Searchable facts | - | ✅ |
| Patterns observed | - | ✅ |

**Skip:** Routine status checks, already-captured content, ephemeral chatter.

---

## Morning System Check (Tasks + Weather)

**When:** 
- After morning brief
- If user asks about tasks/priorities
- When readiness data updates

**Commands:**
```bash
# Energy-Aware Tasks
cd ~/Projects/Thanos && .venv/bin/python Tools/energy_aware_tasks.py

# Weather Recommendations
cd ~/Projects/Thanos && .venv/bin/python Tools/weather_monitor.py
```

**Checks:**
- Tasks matched to Oura readiness
- Morning weather forecast
- Actionable recommendations for car/clothing
- Defers complex tasks on low-energy days

---

## Vigilance (Work Hours Only: Mon-Fri 9am-5pm)

### Quick Checks (silent unless action needed)

**1. Spiral/Scatter Detection**
- Count brain dumps in last 60 min
- If 5+ dumps with 0 completions → SPIRAL intervention
- If 4+ different topics in 30 min → SCATTER intervention

**2. Stuck Detection**
- Check WorkOS for task status changes
- If no movement in 2+ hours → prompt "Status. What's blocking you?"

**3. Drift Detection**
- Compare current work context vs morning priorities
- If working on wrong thing → redirect

**4. Energy Crash (2pm check)**
- If 0/3 morning priorities done by 2pm → intervention
- If LOW energy day → suggest wrapping up early

### When to Alert (Telegram)
- 🔥 Fire: Urgent client message (keywords: ASAP, urgent, blocker, go-live)
- 📅 Meeting: 15 min before calendar event (with context)
- 🚨 Spiral: 5+ dumps, 0 completions
- ⚠️ Drift: Wrong priority being worked on
- ⏰ Stuck: 2+ hours no progress

### When to Stay Silent
- Normal work flow
- Already responded recently (<10 min)
- Quiet hours (10pm-6am)
- DND mode active
- Weekend (unless commitment decay)

---

## Self-Improvement (Every Heartbeat)

After memory capture, analyze recent conversation for learnings:

### Signal Detection
Look for correction signals in recent messages:
- **HIGH confidence**: "never", "always", "wrong", "stop", "the rule is"
- **MEDIUM confidence**: "perfect", "exactly", "that's right", approved output
- **LOW confidence**: Patterns that worked but not explicitly validated

### When Signals Detected
1. Classify the learning (Code Style, Process, Domain, Tools)
2. Map to target file (AGENTS.md, SOUL.md, skills, or new skill)
3. Propose change with diff
4. Apply if clear improvement, otherwise note for review

### Auto-Apply Rules
Apply without asking if:
- HIGH confidence correction
- Clearly improves agent behavior
- Doesn't conflict with existing rules

Otherwise, log to `memory/pending-learnings.md` for review.

### State Files
- `~/.reflect/reflect-state.yaml` - State tracking
- `~/.reflect/reflect-metrics.yaml` - Metrics

---

## Service Health (2-3x daily)

### Graphiti MCP
```bash
curl -s -I http://localhost:8000/sse | head -1
```
If down:
```bash
launchctl start com.thanos.graphiti
# or manually:
cd /Users/jeremy/Projects/mcp-graphiti && NEO4J_URI=bolt://localhost:7687 nohup uv run python graphiti_mcp_server.py > /tmp/graphiti.log 2>&1 &
```

### Neo4j
```bash
docker ps | grep neo4j  # Should show "healthy"
```

### Memory V2 (test)
```bash
cd /Users/jeremy/Projects/Thanos && .venv/bin/python -c "from Tools.memory_v2.mcp_tools import memory_search; print(memory_search(query='test', limit=1))"
```
