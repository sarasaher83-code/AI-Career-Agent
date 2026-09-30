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
| [docs/USER_GUIDE.md](docs/USER_GUIDE.md) | **Start here:** how to use the Career Desk day to day |
| [docs/SECURITY.md](docs/SECURITY.md) | Where data lives, safeguards, how to revoke access |
| [docs/ROADMAP.md](docs/ROADMAP.md) | What is blocked on you, and next improvements |
| [docs/CLOUD_DESK.md](docs/CLOUD_DESK.md) | The cloud setup in use: private Career Desk page, daily Job Scout and weekly Growth Report runs, apply step |
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | Design principles, modules, job sources, matching model, security, costs, build stages |
| [docs/SETUP_WINDOWS.md](docs/SETUP_WINDOWS.md) | Step-by-step installation and API-key setup |
| [docs/JOB_ALERTS_SETUP.md](docs/JOB_ALERTS_SETUP.md) | Creating job alerts on LinkedIn, Bayt, GulfTalent, Naukrigulf and Indeed |
| [docs/TEST_REPORT.md](docs/TEST_REPORT.md) | Test results per build stage |

## Build status

| Part | Status |
|---|---|
| Phase 1–2: verified master profile, career positioning | ✅ Approved by candidate |
| Job discovery: alert emails, web search, career pages, de-duplication | ✅ Live (daily Job Scout) |
| Transparent 8-part matching with evidence | ✅ Live |
| Application packs: tailored CV and cover letter, Word + PDF, fact-checked | ✅ Live |
| Apply step: Easy Apply via the Claude desktop app, max 5 a day, per-job approval | ✅ Live |
| LinkedIn profile makeover (EN + AR) and corrections list | ✅ Delivered |
| Content calendar: 3 posts a week, approval, desktop-app posting | ✅ Live |
| Engagement drafts, recruiter directory, analytics, growth report | ✅ Live |
| Local Windows app (S0–S1): offline archive, exports | ✅ Available |

## For developers

```bash
pip install -r requirements-dev.txt
git config core.hooksPath .githooks   # blocks commits of private data or secrets
pytest
python run.py                         # http://127.0.0.1:8000
```
