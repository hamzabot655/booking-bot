# Secret Rotation Checklist

All of these values were committed to git history and/or shared in chat, so they must be
treated as **compromised** and rotated at the provider. Removing them from the working tree
(already done) is not enough. Do these in order; each is an owner action (requires provider login).

> After rotating, set the NEW value only in the proper place (env var / GitHub Actions secret /
> Railway variable) — never back in a tracked file.

| # | Secret | Where to revoke/rotate | Where the new value goes |
|---|--------|------------------------|--------------------------|
| 1 | **GitHub classic tokens** (`ghp_…`) — two of them (one was embedded in the git remote) | github.com → Settings → Developer settings → Personal access tokens → Revoke both; create one fine-scoped token | Local git credential only; not stored in repo |
| 2 | **Vercel token** (`vcp_…`) | vercel.com → Settings → Tokens → Revoke; create new | GitHub secret `VERCEL_TOKEN` |
| 3 | **Railway API token** | railway.app → Account → Tokens → Revoke; create new | GitHub secret `RAILWAY_API_TOKEN` |
| 4 | **Postgres password** | Railway → Postgres service → rotate credentials | Railway var `DATABASE_URL` (+ GitHub secret `DATABASE_URL_EXTERNAL` for backups) |
| 5 | **ScrapingBee API key** | scrapingbee.com → Account → reset key | Railway var `SCRAPINGBEE_API_KEY` |
| 6 | **Admin `AUTH_PASSWORD`** | Generate a new one: `python scripts/rotate_secrets.py --apply` | Railway var `AUTH_PASSWORD` **and** GitHub secret `AUTH_PASSWORD` (smoke test) — keep them equal |
| 7 | **Goethe account password** | login.goethe.de → change password | Wherever student creds are stored (Google Sheet / DB), re-encrypted |

## Setting GitHub secrets (after rotation)
```bash
gh secret set VERCEL_TOKEN        --repo hamzabot655/booking-bot --body "<new>"
gh secret set RAILWAY_API_TOKEN   --repo hamzabot655/booking-bot --body "<new>"
gh secret set AUTH_PASSWORD       --repo hamzabot655/booking-bot --body "<new>"
gh secret set DATABASE_URL_EXTERNAL --repo hamzabot655/booking-bot --body "<railway public postgres url>"
```

## Setting Railway variables (after rotation)
```bash
railway variables set AUTH_PASSWORD=<new>
railway variables set SCRAPINGBEE_API_KEY=<new>
# DATABASE_URL is managed by the Railway Postgres plugin; rotate via the plugin UI
```

## Optional: purge from git history
The current tree is clean, but the secrets still exist in past commits. To scrub them:
```bash
pip install git-filter-repo
git filter-repo --replace-text <(printf '%s\n' 'OLD_SECRET==>REDACTED')   # repeat per secret
git push --force origin main
```
Destructive — rewrites every commit SHA and requires a force-push. Rotation (above) is the
real fix; history scrub is only defense-in-depth. Decide before running.
