# Workflows (NotebookLM CLI v0.3+)

## Workflow 1: Create Audio Podcast from Research Sources

### Goal
Generate an audio overview from notebook sources.

### Steps

1. **Authenticate**
   ```bash
   nlm login
   ```

2. **Create Notebook**
   ```bash
   nlm create "Podcast Project"
   ```

3. **Add Sources**
   ```bash
   nlm source add -n <notebook-id> --url "https://example.com/article1"
   nlm source add -n <notebook-id> --url "https://example.com/article2"
   nlm source add -n <notebook-id> --text "Additional notes here" --title "My Notes"
   ```

4. **Verify Sources**
   ```bash
   nlm source list -n <notebook-id>
   ```

5. **Generate Audio**
   ```bash
   nlm generate audio -n <notebook-id> "brief overview" --wait
   ```

6. **Check Artifacts**
   ```bash
   nlm artifact list -n <notebook-id>
   ```

---

## Workflow 2: Create Study Materials from Documents

### Goal
Generate quizzes, flashcards, and reports for studying.

### Steps

1. **Setup Notebook**
   ```bash
   nlm create "Study Materials"
   nlm source add -n <notebook-id> --url "https://lecture-notes.edu/course1"
   nlm source add-drive -n <notebook-id> --doc <doc-id>
   ```

2. **Generate Materials**
   ```bash
   nlm generate quiz -n <notebook-id> "focus on key definitions" --wait
   nlm generate flashcards -n <notebook-id> "key terms" --wait
   nlm generate report -n <notebook-id> "study guide" --wait
   ```

3. **Review Outputs**
   ```bash
   nlm artifact list -n <notebook-id>
   ```

---

## Workflow 3: Create Presentation from Research

### Goal
Generate slides and infographics from sources.

### Steps

1. **Prepare Notebook**
   ```bash
   nlm create "Q4 Report"
   nlm source add -n <notebook-id> --url "https://company-reports.com/q4-summary"
   ```

2. **Generate Visual Content**
   ```bash
   nlm generate slide-deck -n <notebook-id> "stakeholder deck" --wait
   nlm generate infographic -n <notebook-id> "visual summary" --wait
   ```

3. **Check Outputs**
   ```bash
   nlm artifact list -n <notebook-id>
   ```

---

## Workflow 4: Research and Import Sources

### Goal
Discover and import sources automatically.

### Steps

1. **Create Notebook**
   ```bash
   nlm create "AI Research"
   ```

2. **Start Research**
   ```bash
   nlm source add-research -n <notebook-id> "large language model prompting techniques" --mode deep --no-wait
   ```

3. **Check Progress**
   ```bash
   nlm research status
   nlm research wait
   ```

---

## Workflow 5: Interactive Q&A Session

### Goal
Ask questions of notebook sources.

### Steps

1. **Ask Questions**
   ```bash
   nlm ask -n <notebook-id> --new "What are the main arguments?"
   nlm ask -n <notebook-id> "Summarize the key points."
   ```

2. **Configure Persona (Optional)**
   ```bash
   nlm configure -n <notebook-id>
   ```

3. **Review History (Optional)**
   ```bash
   nlm history -n <notebook-id>
   ```

---

## Workflow 6: Export Artifacts

### Goal
Export generated artifacts to Google Docs/Sheets.

### Steps

```bash
nlm artifact list -n <notebook-id>
nlm artifact export <artifact-id>
```

---

## Notes

- Use partial IDs (prefixes) for notebooks, sources, and artifacts.
- Add `--wait` to generation commands when you need blocking output.
