# Command Reference (NotebookLM CLI v0.3+)

## Authentication

### nlm login
Authenticate with NotebookLM by launching Chrome and saving session state.

```bash
nlm login
```

### nlm auth check
Validate stored auth state.

```bash
nlm auth check
nlm auth check --test
nlm auth check --json
```

## Notebook Commands

### List notebooks
```bash
nlm list
nlm list --json
```

### Create notebook
```bash
nlm create "Notebook Title"
```

### Rename notebook
```bash
nlm rename -n <notebook-id> "New Title"
```

### Delete notebook
```bash
nlm delete -n <notebook-id> -y
```

### Summary
```bash
nlm summary -n <notebook-id>
nlm summary -n <notebook-id> --topics
```

### Context
```bash
nlm use <notebook-id>
nlm status
nlm clear
```

## Source Commands

### List sources
```bash
nlm source list -n <notebook-id>
```

### Add sources
```bash
nlm source add -n <notebook-id> --url "https://example.com/article"
nlm source add -n <notebook-id> --text "Content" --title "Notes"
nlm source add-drive -n <notebook-id> --doc <doc-id>
```

### Research + import
```bash
nlm source add-research -n <notebook-id> "search query"
nlm source add-research -n <notebook-id> "search query" --mode deep
nlm source add-research -n <notebook-id> "search query" --from drive
```

### Source tools
```bash
nlm source guide <source-id>
nlm source fulltext <source-id>
nlm source refresh <source-id>
nlm source wait <source-id>
```

## Chat

### Ask questions
```bash
nlm ask -n <notebook-id> --new "Your question"
nlm ask -n <notebook-id> "Follow-up question"
nlm ask -n <notebook-id> --json "Question with references"
```

### Configure + history
```bash
nlm configure -n <notebook-id>
nlm history -n <notebook-id>
```

## Generate Artifacts

```bash
nlm generate audio -n <notebook-id> "brief overview"
nlm generate report -n <notebook-id> "study guide"
nlm generate quiz -n <notebook-id> "key concepts"
nlm generate flashcards -n <notebook-id> "definitions"
nlm generate slide-deck -n <notebook-id> "stakeholder deck"
nlm generate infographic -n <notebook-id> "visual summary"
nlm generate data-table -n <notebook-id> "extract key metrics"
nlm generate mind-map -n <notebook-id> "concept map"
nlm generate video -n <notebook-id> "short explainer"
```

Add `--wait` to block until completion.

## Artifacts (Management)

```bash
nlm artifact list -n <notebook-id>
nlm artifact get <artifact-id>
nlm artifact export <artifact-id>
nlm artifact delete <artifact-id>
nlm artifact wait <artifact-id>
```

## Claude Code Skill Integration

```bash
nlm skill install
nlm skill status
nlm skill show
nlm skill uninstall
```
