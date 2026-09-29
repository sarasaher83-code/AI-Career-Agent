# Test Report

## Stage S0: Foundation (28 Sep 2026)

**Automated tests:** 24 passed, 0 failed (`pytest`, Python 3.11; target runtime Python 3.12 on Windows).
Tests use a fictional profile (`tests/fixtures/sample_profile.json`). No personal data is in the repository.

| Area | What is verified |
|---|---|
| Profile loader | Evidence index built with citable IDs (roles, highlights, employer facts, projects, education, certifications, skills, metrics); private sections (salary, contact, excluded figures) are never treated as evidence; clear errors for a missing file, invalid JSON or missing sections |
| Fact checker | Verified text passes; invented numbers, currency amounts, "million/billion", investment metrics with figures, excluded phrases and credentials that aren't held are **blocked**; investment terms without figures give a **warning**; standard names such as "Vision 2030" and "ISO 19650" are allowed |
| Audit log | Hash chain verifies; secrets are redacted before storage; the database rejects UPDATE and DELETE; tampering with the file directly is detected |
| Approval workflow | draft → approved → completed lifecycle; illegal transitions rejected; drafts that fail the fact check cannot be approved; every transition is audited |
| Settings | Defaults (model `claude-opus-5`, aggregators off); `.env` loading; secrets masked in the UI |
| Commit guard | Blocks `private/`, `.env`, database files and API-key patterns; allows `.env.example` and test fixtures |
| Dashboard | Overview, all 10 section pages, Fact Checker and Audit Log render; missing profile reported gracefully; private preferences never rendered |

**Manual checks:**
- Browser rendering in Chromium at 1366 px (desktop) and 390 px (phone): no horizontal scrolling on any page.
  A phone-width overflow in the navigation was found and fixed during this stage.
- The fact checker was run against the candidate's two existing CVs (outside the repository). It correctly flagged the
  unsupported "1,000,000 sqm", "831 units / 164,124 sqm" and "175,000+ sqm" figures, the "Technical Office Director"
  title and the "Certified in…" wording. It also found employer facts and one project area (7,099 sqm NSA) that were
  missing from the master profile; these were added.

**Known limitations:**
- The fact checker verifies numbers, credentials, financial content and excluded phrases. It does not yet check every
  job title or employer name in free text; that check is added with document generation in S4.
- Phone numbers and URLs in contact lines are flagged as unverified numbers. Generated documents will place contact details
  outside the checked text.

---

## Stage S1: Job Discovery (29 Sep 2026)

**Automated tests:** 55 passed, 0 failed (31 new in S1).

| Area | What is verified |
|---|---|
| Link safety | Tracker redirects are unwrapped offline; query strings dropped; **auto-login links (Naukrigulf `mailerLogin`/`conmailer` tokens) are refused**; words such as "authority" in normal job URLs are not blocked |
| Normalisation | Locations (English and Arabic, GCC cities without a country), experience ranges, relative and short posting dates (including year rollover), title and employer keys |
| Naukrigulf parser | All 15 job cards read from a sanitised real alert email, including cards with a nested company link; no token or tracker survives; account-notice emails ignored |
| De-duplication | Same source + id → "seen again"; cross-source near-identical title / employer / city → merged, with missing fields filled; different city or title not merged; anonymous ("Confidential") employers merged only when title and experience are identical |
| Gmail reader | Uses a fake IMAP server: mailbox opened **read-only**, messages fetched with **BODY.PEEK** (not marked as read), sender-restricted search, logout always called, clear message for a wrong app password |
| Career-page feeds | Greenhouse, Lever, SmartRecruiters and Workable adapters on recorded responses; one failing board does not stop the others; invalid board names rejected |
| Dashboard | .eml upload → 15 vacancies; filters (country, status, source, text); status changes; detail page; manual entry with duplicate detection and login-link refusal; CSV (UTF-8 with BOM for Arabic) and Excel export; **spreadsheet formula injection neutralised** |

**Real-data run (candidate's Gmail, read-only via the session's Gmail connector, with consent):**
6 daily Naukrigulf alert emails (23–29 Sep 2026) → 90 job cards → **29 unique vacancies** (59 repeats recognised, 2 re-posts merged).
All 90 cards were read; none were skipped. Both merges were checked by hand and are correct (same employer, title and city under a new job id).
The raw emails were not kept; only the extracted fields and clean public links are stored in `private/career.db`.

**Observations:**
- Naukrigulf recommendations are poorly targeted: 22 of 29 are in the UAE, only 2 in Saudi Arabia, and most are general
  Project Manager roles. The alert-setup guide (`docs/JOB_ALERTS_SETUP.md`) explains how to retarget them.
- No LinkedIn, Bayt, GulfTalent or Indeed job-alert emails exist in the mailbox yet (only account notices), so those
  readers are not built yet. Each will be built from a real sample.

**Known limitations:**
- Career-page feeds could not be tested live: the development environment blocks outbound access to those APIs.
  The adapters follow each provider's published response format and are tested on recorded responses; they will be
  verified live on the candidate's computer or once the environment allows those hosts.
- Alert emails carry only the listing summary (no full description). For full scoring in S2, the description can be
  pasted via manual entry; the vacancy is merged automatically.
