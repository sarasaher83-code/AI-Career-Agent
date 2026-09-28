# Executive Career Intelligence System: Architecture and Build Plan

**Status:** PROPOSAL, waiting for approval before any code is written.
**Scope:** Phases 3–10 of the master development brief.

> This document contains no personal data. All candidate data (profile, CVs, applications,
> salary preferences) lives in the git-ignored `private/` folder on the candidate's own machine.

---

## 1. Design Principles

1. **Human-in-the-loop by construction.** The system never submits applications, posts, comments, likes,
   connects or messages. It produces *copy-ready drafts plus a link*. The candidate performs every external
   action herself, after approving it in the dashboard. Each approval is logged.
2. **Single source of truth.** Every generated document is built from `private/master_profile.json`.
   Generated text is checked automatically: any number, date, title, employer or qualification not in the
   master profile blocks the draft until it is fixed.
3. **Traceable scoring.** Every match score is broken down into components. Each component cites a quote from
   the vacancy and an evidence item from the profile. Missing information is shown as *unknown*
   and is never scored as zero.
4. **Legitimate sources only.** No scraping of LinkedIn or any site that forbids it. No CAPTCHA or login bypass.
   Rate limits and `robots.txt` are respected.
5. **Local and private.** The system runs on the candidate's computer. Secrets come from environment variables
   (`.env`, git-ignored). **No LinkedIn credentials or session cookies are ever stored or used.**
6. **Non-programmer operation.** One double-click launcher opens the dashboard in the browser. Everything else is
   buttons, filters and exports.

---

## 2. Technology Stack

| Layer | Choice | Reason |
|---|---|---|
| Language | Python 3.12 | Brief requirement; strong document and data libraries |
| Web framework | **FastAPI + Jinja2 templates + HTMX** | Server-rendered, responsive, fully custom styling for the executive look (white / off-white / greys / matte gold / black); no JavaScript build step |
| Database | SQLite (via SQLModel) | Single local file, zero administration, easy to back up |
| LLM | Claude API (official `anthropic` Python SDK), model `claude-opus-5` | Evidence extraction, explanations, tailored drafts. Structured outputs guarantee valid JSON |
| Documents | `python-docx` (CV / cover letter .docx), optional PDF export | ATS-friendly Word output built from a template |
| Exports | `pandas` + `openpyxl` | CSV and Excel exports from every table |
| Deduplication | `rapidfuzz` | Fuzzy match on normalised title + employer + location |
| Scheduling | APScheduler (in-app) plus a manual "Refresh" button | Daily job and digest refresh while the app is running |
| Tests | `pytest` with recorded fixtures (no live API calls in tests) | Each module is tested on its own |

---

## 3. Module Layout

```
app/
  config/          settings loader (.env), constants, spending caps
  security/        audit log, approval workflow, secret handling, PII guards
  profile/         master-profile loader, evidence index, "verified facts" whitelist
  ingestion/
    sources/
      email_alerts.py    job-alert emails (LinkedIn, Bayt, GulfTalent, Naukrigulf, Indeed) from a Gmail label
      ats_boards.py      public career-page APIs: Greenhouse, Lever, SmartRecruiters, Workable
      manual.py          paste a URL or job description into the dashboard
      aggregators.py     OPTIONAL, OFF by default (see section 4)
    normalize.py   common vacancy schema
    dedupe.py      duplicate detection and merging
  matching/
    rules.py       deterministic checks (location, seniority keywords, salary floor, nationality restrictions)
    evidence.py    Claude extracts requirements from the vacancy as structured JSON
    scorer.py      8-dimension weighted score with evidence links and an uncertainty band
  documents/
    cv_builder.py, cover_letter.py, recruiter_message.py, screening_answers.py
    fact_check.py  blocks any claim that isn't in the master profile
    library.py     versioned originals and tailored copies
  content/
    linkedin_optimizer.py, networking_digest.py, content_calendar.py
  dashboard/       routes, templates, static CSS (the 10 sections)
  exports/         CSV and Excel
private/           (git-ignored) master_profile.json, database, generated documents, logs
tests/
docs/
```

---

## 4. Job Sources (Phase 3)

| Source | How | Status | Cost |
|---|---|---|---|
| **Job-alert emails** | The candidate creates alerts on LinkedIn, Bayt, GulfTalent, Naukrigulf and Indeed that are delivered to Gmail. The system reads **only** that Gmail label, read-only (Gmail API or IMAP app password) | Default ON: the main source, and fully within each platform's rules | Free |
| **Public career-page APIs** | Greenhouse, Lever, SmartRecruiters and Workable publish public job-board endpoints. The system keeps a watch-list of target employers that use these | Default ON | Free |
| **Manual intake** | Paste a vacancy URL or text; the system extracts the fields | Default ON | Free |
| Adzuna API | Official job-search API; **GCC coverage not yet verified** (checked at build time via its countries endpoint) | Enabled only if it covers GCC | Free tier |
| Commercial aggregators (SerpApi Google Jobs, JSearch) | Paid APIs that **collect listings by scraping** search engines and job boards, including LinkedIn content | **Default OFF.** These conflict with the "no scraping" principle. Enabled only if the candidate explicitly chooses | SerpApi from ~$25/mo; JSearch free 200 requests, then paid |

**Note:** many GCC employers (giga-projects included) use Workday, SAP SuccessFactors or Oracle career sites, which
have no public job API. For those, the email-alert route and manual intake are the permitted paths.

**Each vacancy stores:** title, employer, location, published date, deadline, salary (if disclosed), description,
required experience, required qualifications, application URL, source, and an employer profile (from a curated
employer table). Duplicates are merged and all sources are kept.

---

## 5. Matching Model (Phase 4)

| # | Dimension | Weight | Method |
|---|---|---|---|
| 1 | Professional experience alignment | 20% | Claude maps each vacancy requirement to profile evidence IDs |
| 2 | Seniority alignment | 15% | Title tier (Phase 2 tiers) plus years-of-experience rules |
| 3 | Sector alignment | 15% | Developer / PMC / hospitality / public realm taxonomy |
| 4 | Geographical suitability | 10% | Preference list (KSA/UAE, then other GCC, then remote) |
| 5 | Leadership requirements | 10% | Team size and reporting-line evidence |
| 6 | Technical requirements | 10% | Skills list match (e.g., BIM / Revit flagged as a gap) |
| 7 | Qualifications | 10% | Degree, SCE, PMP and similar: met / not met / **unknown** |
| 8 | Career progression potential | 10% | Tier 2 bonus; Tier 3 flagged as a stretch |

- The output is a **percentage plus a confidence band**. Unknown requirements widen the band instead of lowering the score.
- **Hard flags** (shown, not hidden): "nationals only", salary below the floor, a required licence the candidate lacks.
- Weights can be changed in settings. The methodology and its limits are shown on every match page.

---

## 6. LinkedIn Networking Digest (Phase 7): Honest Constraints

LinkedIn offers no permitted API for reading other people's posts or the feed for personal use, and scraping is excluded.
The digest is therefore built from:
1. LinkedIn **notification and digest emails** in the candidate's Gmail (read-only label).
2. **Post URLs the candidate saves or pastes** during normal browsing (one-click "add to digest").
3. **Industry news RSS feeds** (Saudi and GCC real estate, giga-projects) to suggest discussion topics and people to follow.

For each item the system drafts the relevance, a suggested engagement and an optional comment. **The candidate posts
manually.** Nothing is automated on LinkedIn.

---

## 7. Security Design (Phase 10)

- Secrets only in `.env` (git-ignored): `ANTHROPIC_API_KEY`, optional Gmail credentials, optional aggregator keys.
- **Forbidden by design:** LinkedIn passwords, session cookies, browser automation against LinkedIn.
- **Audit log:** an append-only table records every system action (source fetch, LLM call with token count,
  document generated, approval granted or rejected, export).
- **Approval workflow:** every draft moves from `draft` → `approved` → `marked as sent by candidate`. The system has
  no code path that sends anything externally.
- **Spending cap:** a monthly Claude API budget in settings; calls stop when it's reached.
- **Data minimisation:** only vacancy text and the master profile are sent to the Claude API. Salary preferences
  and contact details are never included in prompts unless a document needs them.
- **Repository:** this repository is public. Personal data never leaves `private/`, and a pre-commit check blocks it.

---

## 8. Estimated Operating Costs

Claude pricing (September 2026, first-party API): **claude-opus-5 costs $5 per million input tokens and $25 per million output tokens.**

| Workload (per month, assumed volume) | Tokens (approx.) | Cost |
|---|---|---|
| Matching: 300 new vacancies after rule pre-filter; ~9k input, ~1.5k output each (includes thinking) | 2.7M in / 0.45M out | ~$25 |
| Application packs: 15 shortlisted (CV + letter + message + screening answers) | 0.25M in / 0.15M out | ~$5 |
| Networking digest: daily, ~30 items | 0.5M in / 0.1M out | ~$5 |
| Content calendar: ~12 posts + LinkedIn optimisation refreshes | 0.1M in / 0.05M out | ~$2 |
| **Total** | | **≈ $35–45 / month** |

- Using the Batch API for overnight matching (50% discount) and prompt caching of the profile could bring this to **≈ $20–30 / month**.
- Other costs: hosting $0 (local); Gmail and public ATS APIs free; Adzuna free tier.
- **Optional:** a commercial aggregator adds ~$25+/month (default OFF).
- Actual cost depends mostly on how many vacancies arrive. The dashboard shows spend to date.

---

## 9. Build Stages (each built and tested separately, with approval between stages)

| Stage | Deliverable | Test |
|---|---|---|
| **S0 Foundation** | Project skeleton, settings, audit log, database, profile loader + fact whitelist, one-click launcher | Unit tests; fact-check rejects invented claims |
| **S1 Job discovery** | Manual intake, email-alert parser, public ATS sources, normalisation, deduplication | Fixture emails and JSON; duplicate-merge tests |
| **S2 Matching** | Rules, Claude evidence extraction, scorer, explanation view | Golden set of 10 real vacancies, reviewed by the candidate |
| **S3 Dashboard v1** | Overview, Job Discovery, Job Matching, Application Pipeline; filters; CSV/Excel export | Browser test at phone and desktop widths |
| **S4 Applications** | Tailored CV, cover letter, recruiter message, screening Q&A, missing-info list, versioned library, approval flow | Fact-check on every output; the candidate reviews samples |
| **S5 LinkedIn optimisation** | Headlines, About, experience, skills, featured, banner brief, corrections list | Consistency check against the master profile |
| **S6 Visibility and content** | Networking digest, content calendar with approval | Sample week reviewed |
| **S7 Recruiters and analytics** | Recruiter directory, performance analytics | Export tests |
| **S8 Handover** | Installation, operating, configuration and security guides; test report; roadmap | Fresh-install dry run |

---

## 10. What the Candidate Needs to Provide

1. **Computer:** Windows or Mac (decides the installer and launcher).
2. **Anthropic API key** from console.anthropic.com with billing enabled. It is entered once in `.env` and never shared in chat.
3. **Job alerts:** set up alerts on LinkedIn, Bayt, GulfTalent, Naukrigulf and Indeed that go to Gmail (a step-by-step guide will be provided).
4. **Gmail access method:** a Gmail app password (simplest; needs 2-step verification) or a Google Cloud OAuth app (more setup).
5. **Decision:** keep commercial aggregators OFF (recommended) or enable them.
