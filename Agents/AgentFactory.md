# Agent Factory - Template for Creating New Agents

Use this template when you need to create a new specialized agent for Thanos.

## Agent Template

```yaml
---
name: [AgentName]
role: [One-line description of role]
voice: [2-3 adjectives describing communication style]
triggers: ["phrase 1", "phrase 2", "phrase 3"]
---
```

```markdown
# [AgentName] Agent

## Personality
- [Key trait 1]
- [Key trait 2]
- [Key trait 3]
- [Key trait 4]

## Primary Functions
- [Function 1]
- [Function 2]
- [Function 3]
- [Function 4]

## Communication Style
- [Style element 1]
- [Style element 2]
- [Style element 3]

## Skills Access
- [Skill path 1]
- [Skill path 2]
- [Context paths]
- [Memory access?]

## Trigger Phrases
- "[Phrase that activates this agent]"
- "[Another trigger phrase]"

## Key Protocols

### [Protocol Name 1]
[Describe the process or decision tree]

### [Protocol Name 2]
[Describe the process or decision tree]

## Example Interactions

**User:** "[Example user input]"
**[AgentName]:** "[Example agent response]"

---

**User:** "[Another example]"
**[AgentName]:** "[Response showing personality and style]"
```

## Guidelines for Creating Agents

### When to Create a New Agent
- Repeated need for specialized expertise
- Distinct communication style needed
- Specific domain knowledge required
- Clear trigger patterns exist

### Agent Design Principles
1. **Clear Role:** One agent, one responsibility
2. **Distinct Voice:** Should feel different from other agents
3. **Useful Triggers:** Natural phrases users would say
4. **Bounded Access:** Only access files/skills needed
5. **Practical Protocols:** Concrete, actionable processes

### Existing Agents
- **Ops:** Daily tactics, tasks, planning
- **Coach:** Accountability, patterns, confrontation
- **Health:** Energy, Vyvanse, supplements
- **Strategy:** Long-term, quarterly, goals

### Potential Future Agents
- **Finance:** Deep dive on money, invoicing, taxes
- **Relationships:** Ashley-specific, family dynamics
- **Learning:** Professional development, skills
- **Creative:** Writing, content, side projects

## Integration Checklist

When creating a new agent:
- [ ] Create file in Agents/
- [ ] Add to LIFE-OS.md routing
- [ ] Define trigger phrases
- [ ] Specify Skills/Context access
- [ ] Write example interactions
- [ ] Test with sample queries
