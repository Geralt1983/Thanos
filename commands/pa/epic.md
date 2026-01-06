# /pa:epic - Epic Consulting Command

Specialized commands for Epic Systems consulting work.

## Usage
```
/pa:epic [action] [options]
```

## Actions

### status
Overview of all Epic projects and tasks.
```
/pa:epic status
```

### orderset
Orderset-related workflows.
```
/pa:epic orderset --action review --name "Sepsis Bundle"
```

### interface
HL7/interface troubleshooting and documentation.
```
/pa:epic interface --type hl7 --direction inbound
```

### build
Epic build documentation and tracking.
```
/pa:epic build --module orders --environment test
```

### ticket
Manage Epic support tickets and issues.
```
/pa:epic ticket --list --priority high
```

## Orderset Workflows

### Review Checklist
- [ ] Clinical content accuracy
- [ ] Order sentence clarity
- [ ] Default values appropriate
- [ ] Required fields identified
- [ ] Alerts and BPAs configured
- [ ] Testing scenarios documented
- [ ] Provider sign-off obtained

### Documentation Template
```markdown
## Orderset: [Name]
**Module:** [Orders/Medications/etc]
**Version:** [X.X]
**Last Updated:** [Date]

### Purpose
[Clinical use case]

### Components
- [Order groups]
- [Individual orders]
- [Linked alerts]

### Build Notes
[Technical implementation details]

### Testing
[Test scenarios and results]
```

## Interface Patterns

### HL7 Message Analysis
```
/pa:epic interface --analyze --message "[paste HL7]"
```
- Parse message segments
- Identify mapping issues
- Suggest fixes

### Integration Documentation
- Source system details
- Message types and triggers
- Transform rules
- Error handling

## Epic-Specific Outputs

### Build Documentation
```markdown
## Build Record: [Name]

**Environment:** [PRD/TST/DEV]
**Record Type:** [Type]
**Record ID:** [ID]

### Configuration
[Key settings and values]

### Dependencies
[Related records and integrations]

### Change History
| Date | Change | By |
|------|--------|-----|
| [Date] | [Description] | [Name] |
```

### Go-Live Checklist
- [ ] Build validated in TEST
- [ ] Security review complete
- [ ] Training materials ready
- [ ] Communication plan executed
- [ ] Support escalation path defined
- [ ] Rollback plan documented

## Integration Points
- Epic UserWeb for documentation
- Jira/ServiceNow for tickets
- Confluence for knowledge base
- Teams/Slack for communication

## Flags
- `--module [orders|meds|notes|etc]`: Filter by Epic module
- `--environment [prd|tst|dev]`: Target environment
- `--client [name]`: Filter by client
- `--template [orderset|interface|build]`: Output template
- `--export [pdf|docx|confluence]`: Export format
