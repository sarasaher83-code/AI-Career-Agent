# Security and Privacy

## Where your data lives
| Data | Location | Who can read it |
|---|---|---|
| Master profile, jobs, packs, posts, reports, recruiters | Career Desk artifact database (rule: read and write **owner only**) | You. Tested: an editor-level read returns nothing |
| Local app data (Windows option) | `private/` folder and `private/career.db` on your computer | You; excluded from git |
| Source code and run instructions | Public GitHub repository | Anyone. Contains **no** personal data |

## Safeguards
- **No credentials are stored anywhere.** LinkedIn passwords were never used or kept. The password shared in chat on 28 Sep 2026
  must be changed if that has not been done yet. Browser actions run in the Claude desktop app, where you sign in yourself.
- **Commit guard:** a pre-commit hook blocks `private/`, `.env`, database files and API-key patterns (`scripts/check_commit.py`).
- **Job links are cleaned:** tracking redirects are removed, and auto-login links (e.g. Naukrigulf's `mailerLogin` tokens) are refused.
  Raw emails are never stored.
- **Gmail is read-only:** the local reader opens the inbox read-only and fetches with BODY.PEEK. The cloud Job Scout only searches and reads alert emails.
- **Fact checker:** blocks financial data, numbers not in the profile, excluded phrases and credentials you do not hold,
  in every CV, cover letter, post and profile text.
- **Approval gate:** applications and posts require your explicit Approve tap per item. Automated applying and posting
  through the desktop app are your informed choices (29–30 Sep 2026), made despite LinkedIn's no-automation rule. Limits: 5 applications a day, one post per task,
  and an immediate stop at any sign-in, CAPTCHA or security check.
- **Audit trail:** each job's `history`, the `runs` log, and (local app) a hash-chained, append-only audit log.
- **Spreadsheet exports** neutralise formula injection from job titles.

## If you want to revoke access
- Pause or delete routines in claude.ai → Routines.
- Disconnect Gmail in claude.ai → Settings → Connectors.
- Delete the Career Desk artifact to erase its database entirely.
