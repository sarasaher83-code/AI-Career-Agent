# AI-Career-Agent

AI-powered executive job search and LinkedIn personal-branding assistant. It runs locally on your own computer.

- **Prepares, never acts:** it drafts applications and LinkedIn content, and you approve and perform every external action yourself.
- **Verified facts only:** every draft is checked against a locked master profile before it can be approved.
- **Private by design:** personal data stays in the git-ignored `private/` folder, and LinkedIn credentials are never used.

## Quick start (Windows)

See **[docs/SETUP_WINDOWS.md](docs/SETUP_WINDOWS.md)**. In short: install Python, add `private/master_profile.json`,
put your Claude API key in `.env`, then double-click `start.bat`.

## Documentation

| Document | Contents |
|---|---|
| [docs/CLOUD_DESK.md](docs/CLOUD_DESK.md) | The cloud setup in use: private Career Desk page, daily Job Scout and weekly Growth Report runs, apply step |
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | Design principles, modules, job sources, matching model, security, costs, build stages |
| [docs/SETUP_WINDOWS.md](docs/SETUP_WINDOWS.md) | Step-by-step installation and API-key setup |
| [docs/JOB_ALERTS_SETUP.md](docs/JOB_ALERTS_SETUP.md) | Creating job alerts on LinkedIn, Bayt, GulfTalent, Naukrigulf and Indeed |
| [docs/TEST_REPORT.md](docs/TEST_REPORT.md) | Test results per build stage |

## Build status

| Stage | Scope | Status |
|---|---|---|
| S0 | Foundation: settings, audit log, approval workflow, profile loader, fact checker, dashboard shell, launcher | ✅ Complete |
| S1 | Job discovery: Gmail alert import (read-only), .eml upload, public career-page feeds, manual entry, de-duplication, filters, CSV/Excel export | ✅ Complete |
| S2 | Transparent job matching | Next |
| S3–S8 | Dashboard, applications, LinkedIn, content, analytics, handover | Planned |

## For developers

```bash
pip install -r requirements-dev.txt
git config core.hooksPath .githooks   # blocks commits of private data or secrets
pytest
python run.py                         # http://127.0.0.1:8000
```
