# Epic Domain Taxonomy

This document defines the Epic EMR domains being tracked for learning progression.

## Domain Structure

Each domain has:
- **Subdomains**: Specific areas within the domain
- **Key Concepts**: Core knowledge to acquire
- **Complexity Indicators**: What distinguishes novice from expert
- **Common Pitfalls**: Frequent issues to learn from

---

## 1. Orderset Builds

**Description:** Creating and configuring clinical order sets, preferences, and ordering workflows.

### Subdomains
- **SmartSets**: Multi-order templates with logic
- **Quick Lists**: Simple grouped orders
- **Panels**: Lab/imaging order groupings
- **Preference Lists**: Provider-specific defaults
- **Order Transmit**: Routing and communication
- **Dynamic Documentation**: Auto-filling order details

### Key Concepts
- SmartGroups vs Sections vs Order Sets hierarchy
- Phantom defaults in OCC (Order Composer Component)
- Preference list cascading logic (system → department → provider)
- Dynamic defaults using SmartData Elements
- Order sentence structure and customization
- Redirector sections (routing to different order types)
- Phase/frequency configuration
- Order panel nesting limits

### Complexity Indicators
- **Novice**: Can create basic order sets
- **Beginner**: Understands hierarchy and defaults
- **Intermediate**: Uses dynamic defaults and logic
- **Advanced**: Builds complex redirectors and cascading preferences
- **Expert**: Optimizes for workflow efficiency, troubleshoots edge cases

### Common Pitfalls
- Forgetting phantom defaults override manual selections
- Preference lists not cascading due to naming mismatches
- Redirector sections pointing to wrong order types
- Order transmit rules blocking expected routing

---

## 2. Interfaces

**Description:** HL7, Bridges, and data integration between Epic and external systems.

### Subdomains
- **HL7 Messages**: ADT, ORM, ORU, MDM, etc.
- **Bridges**: Epic-to-external data connectors
- **Provider Matching**: Linking external provider IDs
- **Data Mapping**: Field translation and transformation
- **Interface Monitoring**: Debugging and error handling
- **Web Services**: REST/SOAP integrations

### Key Concepts
- HL7 segment structure (PID, PV1, OBX, etc.)
- Provider matching: NPI vs internal ID vs external ID
- Bridge configuration workflow
- Message routing and filtering rules
- Error queue management
- Identifier cross-referencing
- Real-time vs batch interfaces
- ACK/NAK handling

### Complexity Indicators
- **Novice**: Understands HL7 message basics
- **Beginner**: Can map fields and configure simple bridges
- **Intermediate**: Troubleshoots provider matching and routing
- **Advanced**: Builds custom transformations and handles edge cases
- **Expert**: Designs interface architecture, optimizes performance

### Common Pitfalls
- Provider matching fails due to identifier type mismatches
- HL7 segment ordering breaking parsers
- Missing required fields in outbound messages
- Bridge timing issues (real-time assumptions on batch interfaces)
- Not accounting for duplicate message handling

---

## 3. ClinDoc Configuration

**Description:** Clinical documentation templates, SmartTools, and workflow optimization.

### Subdomains
- **SmartPhrases**: Text shortcuts
- **SmartTexts**: Auto-populated text
- **SmartLists**: Dropdown selections
- **SmartLinks**: Navigational shortcuts
- **Documentation templates**: Note structures
- **Flowsheets**: Discrete data entry
- **Navigator sections**: Custom workspace layouts

### Key Concepts
- SmartTool syntax and nesting
- Context-aware SmartTexts (patient-specific data)
- Template inheritance and overrides
- Flowsheet row/column configuration
- Documentation auto-import rules
- Co-signature workflows
- Note status transitions

### Complexity Indicators
- **Novice**: Creates basic SmartPhrases
- **Beginner**: Uses SmartTexts with patient data
- **Intermediate**: Builds complex templates with logic
- **Advanced**: Optimizes flowsheets and Navigator layouts
- **Expert**: Designs specialty-specific documentation systems

### Common Pitfalls
- SmartText syntax errors breaking auto-population
- Template inheritance conflicts
- Flowsheet data not flowing to expected reports
- Over-complicating documentation (user adoption issues)

---

## 4. Cardiac Rehab Integrations

**Description:** Specialized integrations for cardiac rehabilitation systems (VersaCare, ScottCare, etc.).

### Subdomains
- **VersaCare Integration**: Telemonitoring data ingest
- **ScottCare Integration**: Exercise/monitoring data
- **Rehab Workflows**: Enrollment, sessions, outcomes
- **Device Data**: Wearables, monitors, transmitters
- **Reporting**: Outcomes tracking and compliance

### Key Concepts
- Cardiac rehab program enrollment triggers
- Telemonitoring data HL7 structure
- Device identifier mapping
- Session attendance tracking
- Outcome measure discrete data points
- Insurance authorization workflows
- Provider assignment for rehab sessions

### Complexity Indicators
- **Novice**: Understands rehab program basics
- **Beginner**: Can configure data ingest
- **Intermediate**: Troubleshoots device data issues
- **Advanced**: Optimizes workflows for clinical efficiency
- **Expert**: Designs end-to-end rehab systems

### Common Pitfalls
- Device identifiers not matching Epic patient context
- Missing insurance auth blocking session creation
- Data mapping issues for outcomes tracking
- Provider matching failures for supervision documentation

---

## 5. Workflow Optimization

**Description:** Improving clinical efficiency, reducing clicks, enhancing usability.

### Subdomains
- **BPA (Best Practice Advisories)**: Clinical decision support
- **Order Sets vs Preference Lists**: When to use which
- **In Basket Management**: Message routing and efficiency
- **SmartSet Design**: Optimizing for speed
- **User Roles & Security**: Access and workflow alignment

### Key Concepts
- BPA firing logic and suppression rules
- Click reduction analysis
- Parallel vs sequential workflows
- Default-driven ordering (minimize manual entry)
- Role-based workspace customization
- Task delegation and routing
- Time-motion studies for Epic workflows

### Complexity Indicators
- **Novice**: Identifies workflow inefficiencies
- **Beginner**: Proposes basic improvements
- **Intermediate**: Implements BPAs and optimized order sets
- **Advanced**: Conducts workflow analysis and redesign
- **Expert**: Leads system-wide optimization initiatives

### Common Pitfalls
- BPAs firing too often (alert fatigue)
- Over-optimization making workflows fragile
- Not considering edge cases (breaks for some users)
- Forgetting training impact (adoption issues)

---

## 6. Cutover Procedures

**Description:** Go-live preparation, data migration, validation, and post-live support.

### Subdomains
- **Pre-Cutover Validation**: Testing and sign-off
- **Data Migration**: Converting legacy data
- **Go-Live Support**: Command center operations
- **Post-Live Monitoring**: Issue triage and fixes
- **Optimization Cycles**: Post-live improvements

### Key Concepts
- Cutover checklist and timeline
- Data conversion validation rules
- Smoke testing protocols
- Command center roles and escalation
- Break-fix prioritization
- User feedback loops
- Optimization sprints (post-live)

### Complexity Indicators
- **Novice**: Understands cutover phases
- **Beginner**: Executes checklist items
- **Intermediate**: Leads validation workstreams
- **Advanced**: Manages command center operations
- **Expert**: Designs cutover strategy for complex organizations

### Common Pitfalls
- Insufficient validation time (issues discovered at go-live)
- Data migration mapping errors
- Unclear escalation paths during go-live
- Not prioritizing critical vs cosmetic issues
- Forgetting to schedule optimization cycles

---

## Strength Level Definitions

### Novice (0-5 concepts)
- Basic awareness of domain
- Can discuss high-level concepts
- Needs significant guidance

### Beginner (6-15 concepts)
- Foundational understanding
- Can perform simple tasks with supervision
- Recognizes common patterns

### Intermediate (16-30 concepts)
- Solid working knowledge
- Can work independently on standard tasks
- Understands relationships between concepts

### Advanced (31-50 concepts)
- Deep expertise in most areas
- Can troubleshoot complex issues
- Mentors others in the domain

### Expert (51+ concepts)
- Mastery across all subdomains
- Designs solutions for edge cases
- Recognized authority, drives best practices

---

## Learning Progression Notes

**Cross-Domain Connections:**
- Orderset builds + Interfaces: Order transmit routing
- ClinDoc + Workflow Optimization: Template efficiency
- Cardiac Rehab + Interfaces: Device data ingest
- Workflow Optimization + Cutover: Post-live improvement cycles

**Priority Domains (Jeremy's current focus):**
1. Orderset Builds (active client work)
2. Interfaces (frequent troubleshooting)
3. Cardiac Rehab Integrations (specialty focus)

**Learning Strategy:**
- Capture real solutions > theoretical knowledge
- Focus on "why" over "what"
- Document decision patterns, not just facts
- Track knowledge gaps to guide questioning
