# Application Builder (runs at the end of every Job Scout run)

For every `jobs/*` document with `status: "approved"` and no `pack_ready: true`:

1. Save `config/profile` to `$TMP/profile.json` (a temp directory outside the checkout).
2. Read the job's title, employer, reasons, gaps, flags and advert quotes. If the job page can be opened with WebFetch,
   read the full description; otherwise work from the saved fields.
3. Write `$TMP/<code>.json` in the format documented at the top of `cloud/app_builder.py`:
   - `headline`: "Head of Design Management Operations & Technical Office | Real Estate Development | …" (never "Director").
   - `summary`: 3–4 sentences, only facts and numbers that are in the profile (20+ years, 5+ years heading DMO /
     technical office, 43 projects, 165,000+ sqm, 400+ units, two 15,000 sqm DGDA parks, teams of 4 and 12).
   - `competencies`: 8–10 items chosen **exactly** from `skills.core`, most relevant first.
   - `highlights`: for each role index, the highlight indices most relevant to this job, best first (keep 6–8 for the
     current role, 2–3 for older roles).
   - `projects`: the 4–7 most relevant project indices. Never include financial figures; Nojoud Lodge is "pipeline".
   - `letter`: 3–4 short paragraphs. The first names the role and her current position; the second maps her record to the
     advert's main requirements; the third states location honestly ("I lead MENA's Riyadh and Jeddah portfolio remotely from
     Egypt with bi-annual site visits, and I am ready to relocate … as soon as visa and residency procedures are completed.");
     the last is a plain closing. No flattery, no clichés, no claims outside the profile.
4. Run `python -m cloud.app_builder $TMP/profile.json $TMP/<code>.json $TMP/out`.
   If it prints `BLOCKED`, fix the named problems and run it again. Never bypass the check.
5. Run `python -m cloud.pack_to_json <code> $TMP/out $TMP/<code>.json $TMP/<code>-pack.json`, then write it with
   ArtifactData `set` to `packs/<code>` (use `file_path`).
6. `update` the job (pin `if_version`) with `pack_ready: true`, `apply_method` if newly known, and a history entry
   `{at, event: "pack_ready", note: "CV + cover letter built"}`.
7. **Interview prep:** when a job reaches `status: "applied"` and its pack has no file whose kind starts with
   "Interview prep", build a role-specific prep with `python -m cloud.interview_prep` (format in that file's docstring;
   start from the sections of the general design-management prep: introduction, what the role will test, likely questions
   with answers from verified highlights, honest gap answers, practical answers, questions to ask). Add only the PDF to
   the pack (keep the pack under 250,000 bytes) and update the pack with `if_version`.
8. Delete the temp directory. Add "N packs built" to the run summary.
