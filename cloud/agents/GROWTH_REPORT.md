# Growth Report: weekly run (Mondays 7 PM Cairo)

Read and write the Career Desk database (URL in `cloud/DESK_URL`) with the `ArtifactData` tool.

## Inputs
- `metrics` collection: the LinkedIn numbers the candidate saved (profile viewers, post impressions, search appearances, followers).
- `jobs` collection: this week's pipeline (shortlisted, approved, applied, needs you, skipped).
- `engagement` collection: this week's drafts.
- `config/profile`: the locked master profile.
- `reports` collection: previous reports (to see whether last week's actions were done).

## Write `reports/<YYYY-MM-DD>`
```json
{"date":"YYYY-MM-DD","summary":"3–4 plain sentences: numbers week on week, pipeline, what worked",
 "actions":["three specific actions for next week"],
 "makeover": {"headline_options":["…"],"about_en":"…","about_ar":"…","experience_current_role":"…","skills_top_15":["…"],
              "featured":["…"],"banner_brief":"…"}}
```
- Compare with the previous week only when both weeks have numbers; otherwise say which numbers are missing.
- A profile makeover was already delivered on 2026-09-30 (`reports/2026-09-30`). Do **not** rewrite it weekly.
  Include a new `makeover` only if `config/profile` changed since the last makeover, or the candidate asked for one;
  otherwise report which of its section-1 corrections she still appears not to have made (if known) in `actions`.
- When a makeover is written, include `makeover`. It must match the CV exactly:
  name *Sara Saher El-Khoreby*; title *Head of Design Management Operations & Technical Office*; employer
  *MENA Development & Real Estate Investment*; dates, degrees and certifications as in the profile; "completed" (not
  "certified") for courses; no "Director" title, no MBA wording, no financial figures, no forbidden phrases.
  Also list the corrections her current LinkedIn profile needs (dates, missing Connect Architects role, languages, email).
- Run the repository fact checker on every text field before writing:
  `python -m cloud.fact_check_cli <file-with-text>` using the profile saved to a temp file (never inside the repo).
  Rewrite anything it blocks.
- Log `runs/<ISO time>` with `{type:"growth", at, summary}`.
