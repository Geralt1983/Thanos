# /pa:brainstorm - Ideation & Planning Command

Structured brainstorming with guided exploration and actionable outcomes.

## Usage
```
/pa:brainstorm [topic] [options]
```

## Workflow

### Phase 1: Divergent Thinking
- Explore the problem space broadly
- Ask clarifying questions
- Generate multiple perspectives
- No judgment - capture all ideas

### Phase 2: Convergent Thinking
- Evaluate ideas against criteria
- Identify patterns and themes
- Prioritize promising directions
- Select focus areas

### Phase 3: Action Planning
- Break selected ideas into next steps
- Identify blockers and dependencies
- Create concrete action items
- Set review checkpoints

## Brainstorming Modes

### `--mode explore`
Open-ended exploration for early-stage ideas.
- What if questions
- Analogies from other domains
- Constraint removal exercises

### `--mode solve`
Problem-focused for specific challenges.
- Root cause analysis
- Solution brainstorming
- Trade-off evaluation

### `--mode plan`
Strategic planning for initiatives.
- Goal clarification
- Resource identification
- Milestone mapping

### `--mode decide`
Decision support for choices.
- Option enumeration
- Criteria definition
- Weighted evaluation

## Output Format
```markdown
## Brainstorm: [Topic]

### Understanding
[Problem/opportunity summary]
[Key questions explored]

### Ideas Generated
1. **[Idea Name]**
   - Description: [What it is]
   - Pros: [Benefits]
   - Cons: [Drawbacks]
   - Effort: [Low/Medium/High]

2. **[Idea Name]**
   ...

### Patterns Noticed
- [Theme 1]
- [Theme 2]

### Recommended Direction
[Selected approach with reasoning]

### Next Steps
- [ ] [Concrete action 1]
- [ ] [Concrete action 2]
- [ ] [Concrete action 3]

### Open Questions
- [What still needs exploration]
```

## Techniques Available

### For Exploration
- **SCAMPER**: Substitute, Combine, Adapt, Modify, Put to other uses, Eliminate, Reverse
- **Six Thinking Hats**: Facts, Emotions, Caution, Benefits, Creativity, Process
- **First Principles**: Break down to fundamentals, rebuild from there

### For Evaluation
- **Weighted Matrix**: Score options against criteria
- **Pros/Cons/Interesting**: De Bono's PMI method
- **Reversibility Test**: How hard to undo this decision?

### For Planning
- **Working Backwards**: Start from desired outcome
- **Premortem**: Imagine failure, identify causes
- **Dependencies Map**: What must happen first?

## Integration Points
- Save outcomes to tasks system
- Link to relevant projects
- Create follow-up reminders

## Flags
- `--mode [explore|solve|plan|decide]`: Brainstorming focus
- `--time [Xm]`: Timeboxed session
- `--output [tasks|notes|both]`: What to generate
- `--project [name]`: Link to project
- `--solo`: Skip clarifying questions, dive in
