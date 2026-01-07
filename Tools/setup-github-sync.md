# Thanos GitHub Sync Setup

## One-Time GitHub Setup

1. **Create private GitHub repo:**
   ```bash
   gh repo create thanos --private --source=/Users/jeremy/.claude
   ```

2. **Or manually:**
   - Go to https://github.com/new
   - Name: `thanos`
   - Private: ✓
   - Don't initialize with README
   - Create repository

3. **Add remote:**
   ```bash
   cd /Users/jeremy/.claude
   git remote add origin git@github.com:YOUR_USERNAME/thanos.git
   ```

4. **Initial push:**
   ```bash
   cd /Users/jeremy/.claude
   git add .
   git commit -m "Initial Thanos commit"
   git push -u origin main
   ```

## Verify Sync

Test the sync script:
```bash
bash /Users/jeremy/.claude/Tools/sync-lifeos.sh
```

Should auto-commit and push any changes.

## Manual Sync (if needed)

```bash
cd /Users/jeremy/.claude
git add .
git commit -m "Manual sync"
git push
```

## Mobile Access

Already configured:
- Termux + Tailscale for remote access
- Git clone on mobile: `git clone git@github.com:YOUR_USERNAME/thanos.git ~/.claude`
- Auto-sync on session close

---

*Part of Thanos Thanos*
