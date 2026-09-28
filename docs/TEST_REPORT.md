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
