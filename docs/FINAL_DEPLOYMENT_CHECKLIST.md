# InboxPilot AI — Final Deployment Checklist

Use this checklist before pushing to GitHub and deploying.

---

## Pre-Commit Checks

- [x] `python -m pytest` → 222 tests pass
- [x] `python -m pytest e2e/` → 18 Playwright smoke tests pass
- [x] `python scripts/sanity_check.py` → 9 checks pass
- [x] `python -c "import app; print('ok')"` → imports cleanly
- [x] `streamlit run app.py` → app starts at http://localhost:8501
- [x] Screenshots captured → `docs/screenshots/` has 7 .png files
- [x] README.md references real screenshots
- [x] `.env` file is NOT present (or is in .gitignore)
- [x] `data/inboxpilot.db` is in .gitignore (not committed)
- [x] No API keys in any source file
- [x] No absolute paths in source files
- [x] `.env.example` is present and committed

---

## GitHub Setup

- [ ] Create repository: `InboxPilot-AI`
- [ ] Set description: `AI-assisted email workflow automation prototype for professional service firms.`
- [ ] Add topics: `ai-automation streamlit python email-processing workflow-automation human-in-the-loop openai sqlite portfolio-project nlp playwright`
- [ ] Set visibility: Public (for portfolio) or Private
- [ ] Run:
  ```bash
  git init
  git add .
  git commit -m "Finalize InboxPilot AI portfolio prototype
  
  222 unit tests + 18 Playwright smoke tests passing.
  7 screenshots captured. Full documentation."
  git remote add origin https://github.com/YOUR_USERNAME/InboxPilot-AI.git
  git push -u origin main
  ```

---

## Streamlit Community Cloud Deployment (Optional)

- [ ] Push to GitHub first (required)
- [ ] Go to https://share.streamlit.io
- [ ] Click **New app**
- [ ] Select repository: `InboxPilot-AI`
- [ ] Branch: `main`
- [ ] Main file path: `app.py`
- [ ] Click **Deploy**
- [ ] (Optional) Add `OPENAI_API_KEY` in Settings → Secrets
- [ ] Confirm app loads and shows rule-based mode indicator
- [ ] Run Seed Demo Data + Process Unprocessed Emails on deployed app
- [ ] Copy live URL and add to README.md

---

## Post-Deployment

- [ ] Add live demo link to README.md:
  ```markdown
  **Live demo:** https://your-app.streamlit.app
  ```
- [ ] Record 2–3 minute demo video (follow `docs/DEMO_VIDEO_SCRIPT.md`)
- [ ] Add video link to README.md
- [ ] Share on LinkedIn / portfolio site

---

## Environment Variables

| Variable | Dev (local) | Production (Streamlit Cloud) |
|---|---|---|
| `OPENAI_API_KEY` | Set in `.env` (optional) | Set in Secrets (optional) |
| `APP_MODE` | Leave as `demo` | Leave as `demo` |

**No API key = rule-based mode. All features work.**
