# Antigravity Skills Library

A collection of specialized AI-powered skills for software development guidance. Each skill provides expert-level assistance in a specific domain.

## Available Skills

| Skill | Command | Description |
|-------|---------|-------------|
| [Architect](#architect) | `/architect` | System design, architecture planning, and code organization |
| [Tester](#tester) | `/tester` | Testing strategies, test implementation, and quality assurance |
| [Troubleshooter](#troubleshooter) | `/troubleshooter` | Debugging, error diagnosis, and problem resolution |
| [Reviewer](#reviewer) | `/reviewer` | Code review, PR analysis, and quality feedback |
| [Refactorer](#refactorer) | `/refactorer` | Code cleanup, improvement, and modernization |
| [Documenter](#documenter) | `/documenter` | Documentation writing, API docs, and technical writing |
| [Optimizer](#optimizer) | `/optimizer` | Performance tuning, profiling, and optimization |
| [Database](#database) | `/database` | Database design, schema modeling, and data architecture |

---

## Architect

**File:** [`architect/SKILL.md`](architect/SKILL.md)

Expert guidance for software architecture and system design.

### When to Use
- Designing new systems or components
- Restructuring existing codebases
- Evaluating architectural patterns
- Reducing technical debt
- Planning scalability improvements

### Key Capabilities
- System design and component architecture
- SOLID principles and design patterns
- Dependency analysis and management
- Layered and hexagonal architectures
- Refactoring strategies (Strangler Fig, Branch by Abstraction)

### Example Prompts
```
"How should I structure a new Python CLI app?"
"This file has grown to 2000 lines, help me break it up"
"What pattern should I use for this feature?"
"Help me reduce coupling between these modules"
```

---

## Tester

**File:** [`tester/SKILL.md`](tester/SKILL.md)

Expert guidance for software testing and quality assurance.

### When to Use
- Designing test strategies
- Writing unit, integration, or E2E tests
- Improving test coverage
- Debugging flaky tests
- Setting up test automation

### Key Capabilities
- Test pyramid design and implementation
- Mocking, stubbing, and fixture patterns
- TDD/BDD methodologies
- Coverage analysis and improvement
- CI/CD test integration

### Example Prompts
```
"How should I test this async function?"
"My tests are taking 10 minutes, help me speed them up"
"How do I mock this external API?"
"Write unit tests for this class"
```

---

## Troubleshooter

**File:** [`troubleshooter/SKILL.md`](troubleshooter/SKILL.md)

Expert guidance for debugging and problem resolution.

### When to Use
- Diagnosing errors and crashes
- Interpreting stack traces and logs
- Finding root causes
- Debugging performance issues
- Resolving integration problems

### Key Capabilities
- Stack trace analysis
- Log investigation techniques
- Root cause analysis (5 Whys, Fishbone)
- Performance profiling
- Binary search debugging

### Example Prompts
```
"I'm getting a NullPointerException, here's the stack trace..."
"My API returns 500 but I don't know why"
"The application is slow, how do I find the bottleneck?"
"Help me understand this error message"
```

---

## Reviewer

**File:** [`reviewer/SKILL.md`](reviewer/SKILL.md)

Expert guidance for code review and quality feedback.

### When to Use
- Reviewing code changes or PRs
- Identifying bugs and security issues
- Suggesting improvements
- Ensuring best practices
- Providing constructive feedback

### Key Capabilities
- Bug and logic error detection
- Security vulnerability scanning
- Performance issue identification
- Style and maintainability review
- Constructive feedback patterns

### Example Prompts
```
"Review this function for potential bugs"
"What security issues do you see in this API?"
"Is this the right way to structure this?"
"Help me review this PR before merging"
```

---

## Refactorer

**File:** [`refactorer/SKILL.md`](refactorer/SKILL.md)

Expert guidance for code improvement and cleanup.

### When to Use
- Cleaning up messy code
- Reducing complexity
- Eliminating duplication
- Modernizing legacy code
- Improving readability

### Key Capabilities
- Code smell detection
- Extract, rename, and inline refactorings
- Complexity reduction techniques
- Deduplication strategies
- Safe transformation workflows

### Example Prompts
```
"This function is 200 lines, help me break it up"
"I have the same code in three places"
"How do I remove these nested if statements?"
"Help me modernize this old code"
```

---

## Documenter

**File:** [`documenter/SKILL.md`](documenter/SKILL.md)

Expert guidance for documentation and technical writing.

### When to Use
- Creating READMEs
- Writing API documentation
- Adding code comments and docstrings
- Creating architecture decision records
- Writing changelogs and release notes

### Key Capabilities
- README and quickstart creation
- API endpoint documentation
- Docstring/JSDoc/Javadoc patterns
- Architecture Decision Records (ADRs)
- Changelog best practices

### Example Prompts
```
"Write a README for this project"
"Add docstrings to these functions"
"Document this REST API"
"Create an ADR for our database choice"
```

---

---

## Optimizer

**File:** [`optimizer/SKILL.md`](optimizer/SKILL.md)

Expert guidance for performance tuning and optimization.

### When to Use
- Diagnosing slow code or systems
- Profiling CPU and memory usage
- Identifying bottlenecks
- Implementing caching strategies
- Optimizing database queries

### Key Capabilities
- CPU, memory, and I/O profiling
- Bottleneck identification
- Caching strategies (in-memory, distributed)
- Database query optimization
- Async and concurrency patterns

### Example Prompts
```
"This API endpoint takes 5 seconds, help me speed it up"
"How do I profile this Python function?"
"My memory usage keeps growing"
"What caching strategy should I use?"
```

---

## Database

**File:** [`database/SKILL.md`](database/SKILL.md)

Expert guidance for database design and data modeling.

### When to Use
- Designing new database schemas
- Modeling relationships between entities
- Planning indexes for performance
- Writing safe migrations
- Choosing between SQL and NoSQL

### Key Capabilities
- Entity-relationship modeling
- Normalization and denormalization
- Index strategy planning
- Migration best practices
- NoSQL data patterns

### Example Prompts
```
"Design a database schema for an e-commerce app"
"How should I model users and their roles?"
"What indexes should I add for this query?"
"How do I add a column without downtime?"
```

---

## Skill Integration Map

Skills work together across the development lifecycle:

```
┌─────────────────────────────────────────────────────────────────────────┐
│                       DEVELOPMENT LIFECYCLE                              │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│   ┌──────────┐     ┌──────────┐     ┌───────────┐     ┌──────────┐     │
│   │ ARCHITECT│────►│ DATABASE │────►│ DOCUMENTER│────►│  TESTER  │     │
│   │  Design  │     │  Schema  │     │  Document │     │   Test   │     │
│   └──────────┘     └──────────┘     └───────────┘     └──────────┘     │
│        │                                                   │            │
│        │                                                   ▼            │
│        │           ┌───────────────────────────────────────────┐       │
│        │           │              REVIEWER                     │       │
│        │           │           Code Review                     │       │
│        │           └───────────────────────────────────────────┘       │
│        │                              │                                 │
│        ▼                              ▼                                 │
│   ┌──────────┐     ┌──────────────┐     ┌───────────┐                  │
│   │REFACTORER│◄────│TROUBLESHOOTER│────►│ OPTIMIZER │                  │
│   │ Improve  │     │    Debug     │     │  Optimize │                  │
│   └──────────┘     └──────────────┘     └───────────┘                  │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

### Common Skill Combinations

| Scenario | Primary Skill | Supporting Skills |
|----------|---------------|-------------------|
| New feature | Architect | Database, Documenter, Tester |
| Bug fix | Troubleshooter | Tester, Reviewer |
| Code cleanup | Refactorer | Reviewer, Tester |
| PR review | Reviewer | Tester, Documenter |
| Tech debt | Architect | Refactorer, Documenter |
| Slow system | Optimizer | Database, Troubleshooter |
| New data model | Database | Architect, Documenter |

---

## Quick Reference

### Invoke a Skill
Use the slash command in chat:
```
/architect How should I structure this microservice?
/database Design a schema for user permissions
/tester Write tests for the UserService class
/troubleshooter Why am I getting this NullPointerException?
/reviewer Review this PR for security issues
/refactorer Clean up this 500-line function
/documenter Write a README for this project
/optimizer This query is slow, help me speed it up
```

### Skill Files Location
```
.gemini/skills/
├── README.md           ← This file
├── architect/
│   └── SKILL.md
├── database/
│   └── SKILL.md
├── documenter/
│   └── SKILL.md
├── optimizer/
│   └── SKILL.md
├── refactorer/
│   └── SKILL.md
├── reviewer/
│   └── SKILL.md
├── tester/
│   └── SKILL.md
└── troubleshooter/
    └── SKILL.md
```

---

*Skills designed for Thanos + Antigravity integration*

