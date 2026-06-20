# Publish to GitHub + GitHub Pages

Run these from the **local copy** in `C:\Dev\rmbs-rwa-pipeline` (not the OneDrive one).

## A. Push the repo

### Easiest — GitHub CLI (`gh`)
```powershell
winget install GitHub.cli      # if you don't have it; then restart the terminal
gh auth login                  # browser sign-in, once
cd C:\Dev\rmbs-rwa-pipeline
git init -b main
git add .
git commit -m "Initial commit: RMBS RWA pipeline"
gh repo create rmbs-rwa-pipeline --public --source=. --remote=origin --push
```

### Or — plain git (create the empty repo on github.com first, no README)
```powershell
cd C:\Dev\rmbs-rwa-pipeline
git init -b main
git add .
git commit -m "Initial commit: RMBS RWA pipeline"
git remote add origin https://github.com/<your-username>/rmbs-rwa-pipeline.git
git push -u origin main
```

## B. Turn on GitHub Pages (publishes the live dashboard)
1. On github.com → your repo → **Settings ▸ Pages**.
2. **Source:** Deploy from a branch.
3. **Branch:** `main`  •  **Folder:** `/docs`  → **Save**.
4. Wait ~1 minute. Your site goes live at:
   ```
   https://<your-username>.github.io/rmbs-rwa-pipeline/
   ```
   - Landing page: `index.html`
   - Live dashboard: `.../rmbs-rwa-pipeline/RMBS_Dashboard_Preview.html`

> Or enable Pages via CLI:
> `gh api -X POST repos/<you>/rmbs-rwa-pipeline/pages -f source[branch]=main -f source[path]=/docs`

## Notes
- **Public vs private:** GitHub Pages is free on **public** repos. Keep it public for a CV link,
  or private if you prefer (Pages on private repos needs a paid plan).
- **No client data is published.** `.gitignore` excludes the raw tapes and the warehouse; only the
  aggregated, anonymised dashboard (`docs/`) and code are pushed.
- **After each change:** `git add . && git commit -m "..." && git push` — Pages redeploys automatically.
