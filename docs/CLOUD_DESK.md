# Cloud Career Desk

The candidate chose (29 Sep 2026) to run the system in Claude's cloud instead of installing it: scheduled runs
plus a private dashboard page on claude.ai. The Windows app (S0/S1) stays available as an offline archive and export tool.

## Pieces

| Piece | Where | What it does |
|---|---|---|
| **Career Desk** page | Private claude.ai artifact (`cloud/dashboard.html`, URL in `cloud/DESK_URL`) | Today's top-5 shortlist with match breakdown, Approve / Skip, pipeline, engagement drafts, weekly numbers form, growth report, run log |
| Desk storage | The artifact's database, rule **read and write: owner only** | `config/profile` (locked master profile), `finds/LI-<id>`, `jobs/J###`, `engagement/<date>`, `metrics/<date>`, `reports/<date>`, `runs/<time>` |
| **Easy Apply search** | Claude desktop app on the candidate's PC, daily 8:30 AM Cairo | From "Copy daily Easy Apply search task" (Today tab): searches LinkedIn Jobs with the Easy Apply and past-week filters for the target titles in KSA/UAE, then other GCC and remote; adds up to 15 jobs a day through the desk's "Add a LinkedIn Easy Apply job" form (`finds/LI-<id>`); reads only, never applies or interacts |
| **Job Scout** | Routine, daily 9:20 AM Cairo | Follows `cloud/agents/JOB_SCOUT.md`: **LinkedIn Easy Apply jobs only**. Scores the desktop finds from their full description (plus LinkedIn alert emails and search snippets that say Easy Apply), drops everything else, writes the top 5 and the engagement drafts |
| **Growth Report** | Routine, Mondays around 7 PM Cairo | Follows `cloud/agents/GROWTH_REPORT.md`: week-on-week numbers, pipeline, 3 actions; first run adds the fact-checked profile makeover |
| **Apply step** | Claude desktop app on the candidate's PC | A daily scheduled task (10:00 AM Cairo) from "Copy daily auto-apply task", or "Copy apply instructions" for an immediate run: every approved job (Easy Apply, public forms with the tailored CV, signed-in portals; never creates accounts or types passwords), max 5 a day, marks each job on the desk, verified facts only, skip any job with a question the profile can't answer, stop at CAPTCHA / login / external site, never message or connect |
| **Profile update step** | Claude desktop app on the candidate's PC | Growth tab → makeover section 0: one task that applies the fact-checked makeover to her LinkedIn profile, with network notifications off, no deletions except those listed, and entries needing her confirmation left untouched |
| **Portfolio** | Public website (separate repository, GitHub Pages) | Linked from LinkedIn; the CV header, cover letter signature and application-form facts include `identity.portfolio`. Growth tab → "Copy LinkedIn portfolio task" adds it to Contact info and Featured through the desktop app |
| **Posting step** | Claude desktop app on the candidate's PC | Content tab → "Copy posting instructions" for the next approved post: paste the text exactly, visibility Anyone, post once, report the link; stop at sign-in, CAPTCHA or security checks; no other LinkedIn activity |

## Decisions that changed the original brief
- **Automatic Easy Apply** was chosen by the candidate (option 3), after the LinkedIn-rules risk was explained.
  Approval stays explicit: nothing is applied to until she taps **Approve** on that job.
- **Posting her own approved posts** through the desktop app was requested by the candidate on 30 Sep 2026, after the LinkedIn-rules risk was explained. Each post needs her Approve tap and is run one at a time by her.
- **Profile edits through the desktop app** were requested by the candidate on 30 Sep 2026.
- **LinkedIn Easy Apply only:** on 1 Oct 2026 the candidate asked Job Scout to keep only Easy Apply jobs. Other boards are no
  longer searched; jobs already on the desk keep their status.
- Commenting, liking, connecting and messaging remain manual.

## Privacy
- No personal data is in this repository. The page source is public; the data lives only in the owner-only database.
- The scheduled runs read the profile from the desk database into a temporary directory and never commit.
