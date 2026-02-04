# Troubleshooting Guide (NotebookLM CLI v0.3+)

## Authentication Issues

### Session Expired

**Problem:** Commands fail with authentication errors.

**Solution:**
```bash
nlm login
```

NotebookLM sessions can expire. Re-authenticate when commands start failing.

### Chrome Not Found

**Problem:** `nlm login` fails because Chrome is not installed or not found.

**Solution:**
- Ensure Google Chrome is installed
- Verify Chrome is available in PATH

### Cookie Extraction Failed

**Problem:** Authentication fails during cookie extraction.

**Solution:**
- Close Chrome before running `nlm login`
- Log into NotebookLM manually in Chrome first

### Auth Validation

```bash
nlm auth check
nlm auth check --test
```

## Network Issues

### Connection Timeout

**Problem:** Commands timeout when connecting to NotebookLM.

**Solution:**
- Check internet connection
- Verify NotebookLM is accessible (notebooklm.google.com)
- Retry after a short delay

### Rate Limiting

**Problem:** "Too many requests" errors.

**Solution:**
- Slow down requests
- Batch queries when possible

## Source Issues

### Drive/URL Source Not Updating

**Problem:** Source content is outdated.

**Solution:**
```bash
nlm source stale <source-id>
nlm source refresh <source-id>
```

### URL Source Fails

**Problem:** Adding URL source fails.

**Solution:**
- Verify URL is accessible
- Some sites block automated access
- Use `--text` with copied content instead

## Content Generation Issues

### Generation Timeout

**Problem:** Content generation times out.

**Solution:**
- Large notebooks take longer
- Reduce sources or scope
- Use `--wait` only when needed

### Artifact Not Found

**Problem:** Cannot find generated artifact.

**Solution:**
```bash
nlm artifact list -n <notebook-id>
```

## Output Format Issues

### JSON Parse Error

**Problem:** `--json` output is invalid.

**Solution:**
- Check for auth errors in stderr
- Retry without `--json` to inspect output

## Research Issues

### Research Timeout

**Problem:** Research takes too long.

**Solution:**
- Deep research can take several minutes
- Use `--no-wait` and then `nlm research status` / `nlm research wait`

### No Sources Found

**Problem:** Research returns no sources.

**Solution:**
- Try different search queries
- Use more specific terms
- Try `--from drive` for Google Drive search

## Common Error Messages

### "Authentication required"
Run `nlm login` to authenticate.

### "Session expired"
Run `nlm login` to refresh session.

### "Notebook not found"
Verify notebook IDs with `nlm list`.

### "Source not found"
Verify source IDs with `nlm source list -n <notebook-id>`.

### "Rate limit exceeded"
Wait before making more requests.
