# Cloud Career Desk

The candidate chose (29 Sep 2026) to run the system in Claude's cloud instead of installing it: scheduled runs
plus a private dashboard page on claude.ai. The Windows app (S0/S1) stays available as an offline archive and export tool.

## Pieces

| Piece | Where | What it does |
|---|---|---|
| **Career Desk** page | Private claude.ai artifact (`cloud/dashboard.html`, URL in `cloud/DESK_URL`) | Today's top-5 shortlist with match breakdown, Approve / Skip, pipeline, engagement drafts, weekly numbers form, growth report, run log |
| Desk storage | The artifact's database, rule **read and write: owner only** | `config/profile` (locked master profile), `jobs/J###`, `engagement/<date>`, `metrics/<date>`, `reports/<date>`, `runs/<time>` |
| **Job Scout** | Routine, daily around 9 AM Cairo | Follows `cloud/agents/JOB_SCOUT.md`: reads job alerts read-only, cleans links, de-duplicates, filters to GCC + remote, scores with the 8-part model, writes the top 5 and the engagement drafts |
| **Growth Report** | Routine, Mondays around 7 PM Cairo | Follows `cloud/agents/GROWTH_REPORT.md`: week-on-week numbers, pipeline, 3 actions; first run adds the fact-checked profile makeover |
| **Apply step** | Claude desktop app on the candidate's PC | The desk's "Copy apply instructions" gives a ready task: Easy Apply only, max 5 a day, verified facts only, skip any job with a question the profile can't answer, stop at CAPTCHA / login / external site, never message or connect |

| **Posting step** | Claude desktop app on the candidate's PC | Content tab → "Copy posting instructions" for the next approved post: paste the text exactly, visibility Anyone, post once, report the link; stop at sign-in, CAPTCHA or security checks; no other LinkedIn activity |

## Decisions that changed the original brief
- **Automatic Easy Apply** was chosen by the candidate (option 3), after the LinkedIn-rules risk was explained.
  Approval stays explicit: nothing is applied to until she taps **Approve** on that job.
- **Posting her own approved posts** through the desktop app was requested by the candidate on 30 Sep 2026, after the LinkedIn-rules risk was explained. Each post needs her Approve tap and is run one at a time by her.
- Commenting, liking, connecting and messaging remain manual.

## Privacy
- No personal data is in this repository. The page source is public; the data lives only in the owner-only database.
- The scheduled runs read the profile from the desk database into a temporary directory and never commit.
