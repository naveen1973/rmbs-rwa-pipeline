# Dev Setup — moving to VS Code

A one-time setup to work on this repo in VS Code with Claude Code alongside.

## 1. Install the tools
- **VS Code** — https://code.visualstudio.com/
- **Python 3.11+** — https://www.python.org/downloads/ (tick "Add Python to PATH")
- **Git** — https://git-scm.com/download/win

## 2. Move the repo out of OneDrive
Git and OneDrive fight over the same files, so keep the code local:
- Copy the `rmbs-rwa-pipeline` folder to e.g. `C:\Users\Naveen\Documents\rmbs-rwa-pipeline`
- Leave the **deal data** (the `Issuers\` folder) in OneDrive — it's the source, not code.

## 3. Open it in VS Code
- VS Code → **File ▸ Open Folder** → select `Documents\rmbs-rwa-pipeline`

## 4. Install VS Code extensions
Click the Extensions icon (left bar) and add:
- **Python** (Microsoft)
- **Claude Code** (Anthropic) — gives you me inside the terminal/editor
- *(optional)* **Rainbow CSV**, **SQLTools**

## 5. Create the Python environment
Open the terminal (**Terminal ▸ New Terminal**) and run:
```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1        # if blocked: Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
pip install -r requirements.txt
```
Then bottom-right "Select Interpreter" → pick `.venv`.

## 6. Start version control
```powershell
git init -b main
git add .
git commit -m "Initial commit: RMBS RWA pipeline scaffold"
```
Create an empty repo on github.com (no README), then:
```powershell
git remote add origin https://github.com/<you>/rmbs-rwa-pipeline.git
git push -u origin main
```

## 7. Point the pipeline at your data
In `config/deals.yml`, set each deal's `folder` to its full path under your OneDrive
`Issuers\` directory (or copy a working sample into `data/raw/`). Then:
```powershell
python -m src.ingest.prep_rmbs --deal AVON2
```

## 8. Keep working with Claude
Open the Claude Code panel/terminal and say *"read WIP.md and TASKS.md and let's continue."*
It has the full project plan and picks up where we left off.

---
**Continuity:** `WIP.md` (running log) + `TASKS.md` (checklist) are the project's memory —
keep them updated each session and any AI assistant can resume instantly.
