# InboxPilot AI — Deployment Guide

---

## 1. Local Deployment

### Prerequisites

- Python 3.10+ (tested on 3.12)
- pip

### Setup

```bash
git clone https://github.com/BlerimHaxhiu/InboxPilot-AI.git
cd inboxpilot-ai

python -m venv .venv

# Windows
.venv\Scripts\activate
# macOS/Linux
source .venv/bin/activate

pip install -r requirements.txt
```

### Environment Variables

The app works fully without any environment variables (rule-based mode is the default).

To enable optional AI-enhanced analysis:

```bash
# Windows
copy .env.example .env

# macOS/Linux
cp .env.example .env
```

Edit `.env` and set `OPENAI_API_KEY=sk-...`

Never commit `.env` — it is already in `.gitignore`.

### Running the App

```bash
streamlit run app.py
# Opens at http://localhost:8501
```

### Running Tests

```bash
python -m pytest              # 222 tests
python -m pytest --tb=short   # with short traceback
python -m pytest -v           # verbose
```

### Sanity Check

```bash
python scripts/sanity_check.py
```

Verifies the full pipeline end-to-end without Streamlit or an API key.

---

## 2. Playwright Setup

Browser-based smoke tests verify the app loads and all pages render.

```bash
# Install browser engine (one-time setup)
python -m playwright install chromium

# Start Streamlit on port 8502
streamlit run app.py --server.port 8502 --server.headless true

# Run 18 smoke tests + capture 7 screenshots
python -m pytest e2e/ -v --timeout=60

# OR use the combined runner (starts/stops Streamlit automatically)
python e2e/run_smoke_test.py
```

Screenshots are saved to `docs/screenshots/`. No API key required.

For Render/Railway deployment, use the start command:

```
streamlit run app.py --server.port $PORT --server.address 0.0.0.0
```

---

## 3. GitHub Upload Checklist

Before pushing to GitHub:

- [ ] Confirm `.env` is NOT present (or is in `.gitignore`)
- [ ] Confirm `data/inboxpilot.db` is NOT committed (already in `.gitignore`)
- [ ] Confirm no API keys appear anywhere in source files
- [ ] Confirm `data/demo_emails.json` IS committed (it is the demo dataset)
- [ ] Confirm `.env.example` IS committed (template with empty key)
- [ ] Run `python -m pytest` — all 222 tests must pass before commit
- [ ] Run `python scripts/sanity_check.py` — all 9 checks must pass
- [ ] Capture screenshots per `docs/SCREENSHOTS_CHECKLIST.md` and add to `docs/screenshots/`
- [ ] Update README.md screenshot section with actual image links

### Repository Structure to Commit

```
.
├── app.py
├── requirements.txt
├── .env.example
├── .gitignore
├── README.md
├── scripts/
│   └── sanity_check.py
├── src/
│   ├── __init__.py
│   ├── ai_validation.py
│   ├── classifier.py
│   ├── config.py
│   ├── database.py
│   ├── demo_data.py
│   ├── draft_generator.py
│   ├── models.py
│   ├── openai_client.py
│   ├── processor.py
│   ├── review_workflow.py
│   ├── safety.py
│   └── task_extractor.py
├── data/
│   └── demo_emails.json
├── docs/
│   ├── ARCHITECTURE.md
│   ├── DEMO_GUIDE.md
│   ├── DEMO_VIDEO_SCRIPT.md
│   ├── DEPLOYMENT.md
│   ├── FINAL_PROJECT_AUDIT.md
│   ├── FINAL_PORTFOLIO_REPORT.md
│   ├── PHASE_2_BUILD_REPORT.md  ← dev history
│   ├── PHASE_3_BUILD_REPORT.md
│   ├── PHASE_4_BUILD_REPORT.md
│   ├── PHASE_5_BUILD_REPORT.md
│   ├── PHASE_6_BUILD_REPORT.md
│   ├── PHASE_7_BUILD_REPORT.md
│   ├── PORTFOLIO_VALUE.md
│   ├── SAFETY_AND_LIMITATIONS.md
│   ├── SCREENSHOTS_CHECKLIST.md
│   └── screenshots/
│       ├── .gitkeep
│       └── *.png  ← add after capture
└── tests/
    ├── __init__.py
    ├── test_ai_validation.py
    ├── test_classifier.py
    ├── test_database.py
    ├── test_draft_generator.py
    ├── test_openai_client.py
    ├── test_processor.py
    ├── test_review_workflow.py
    ├── test_safety.py
    ├── test_task_board.py
    └── test_task_extractor.py
```

### Files NOT to Commit

| File / Path | Reason |
|---|---|
| `.env` | Contains API key |
| `data/inboxpilot.db` | Runtime artifact — regenerate from demo data |
| `__pycache__/`, `*.pyc` | Python bytecode |
| `.venv/`, `venv/`, `env/` | Virtual environment |
| `.pytest_cache/` | Test cache |
| `.claude/` | Claude Code editor settings |

---

## 3. Streamlit Community Cloud (Free Hosting)

Deploy for free at [streamlit.io/cloud](https://streamlit.io/cloud).

### Steps

1. Push the repository to GitHub (public or private)
2. Log in at streamlit.io/cloud
3. Click **New app**
4. Select: repository, branch (`main`), entry point (`app.py`)
5. Click **Deploy**

Streamlit installs from `requirements.txt` automatically.

### Secrets (optional)

To enable OpenAI-enhanced mode on Community Cloud:

1. In your app's **Settings → Secrets**, add:
   ```toml
   OPENAI_API_KEY = "sk-..."
   ```
2. The app reads `OPENAI_API_KEY` from environment — no code change needed

**No API key = rule-based mode.** The app is fully functional without a key.

### SQLite on Community Cloud

The SQLite database (`data/inboxpilot.db`) is **ephemeral** on Streamlit Community Cloud — it resets on every deployment and on any app restart.

This is expected for a demo. Visitors will:
1. See an empty dashboard
2. Click **Seed Demo Data**
3. Click **Process Unprocessed Emails**

This two-click setup is intentional and takes under 5 seconds.

---

## 4. SQLite — What It Means for Deployment

| Scenario | SQLite | Better Option |
|---|---|---|
| Local demo | ✅ Perfect | — |
| Portfolio showcase | ✅ Fine | — |
| Single-reviewer production | ✅ Adequate | — |
| Multi-user concurrent writes | ❌ Not designed for this | PostgreSQL |
| Persistent hosted database | ❌ Ephemeral on Streamlit Cloud | Supabase / PlanetScale |

SQLite is the correct choice for a portfolio prototype. It requires no server, no credentials, and no configuration — the database is created automatically on first run.

---

## 5. Production Future

If this project were to move toward a real production deployment, the recommended upgrades are:

| Area | Current (Demo) | Production Upgrade |
|---|---|---|
| Database | SQLite (local file) | PostgreSQL |
| Authentication | None | OAuth2 / SSO (firm staff only) |
| Inbox source | JSON demo data | Gmail / Outlook API via OAuth |
| Multi-user | Single shared DB | Role-based access per reviewer |
| Background processing | On-click | Celery worker + Redis queue |
| Monitoring | None | Sentry / Grafana |
| Deployment | Streamlit Community Cloud | Docker + cloud hosting |

These are deliberate Phase 7+ scope items and are documented in `docs/FINAL_PORTFOLIO_REPORT.md`.

---

## 6. Environment Variable Reference

| Variable | Required | Default | Description |
|---|---|---|---|
| `OPENAI_API_KEY` | No | (empty) | Enables AI-enhanced analysis via GPT-4o-mini |
| `APP_MODE` | No | `demo` | Application mode; leave as `demo` |

Both variables are loaded from `.env` at the project root via `python-dotenv`, with fallback to system environment variables. Neither is hardcoded anywhere in the source.
