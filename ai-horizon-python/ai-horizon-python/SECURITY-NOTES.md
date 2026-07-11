# Security Notes

Last reviewed: 2026-07-11

## Secrets audit (2026-07-11)

- `.env` is **untracked** and **gitignored** (`.gitignore` line: `.env`). Verified with
  `git check-ignore` and `git ls-files`.
- A full history scan (every commit, all refs) found **no `.env` file was ever committed**.
  Only `.env.example` (placeholders) has ever been tracked.
- A hardcoded Supabase project URL was removed from `RAILWAY_DEPLOY.md` (the project
  itself is no longer used since the Railway PostgreSQL migration).

## Keys that should be rotated

The local `.env` holds live secrets in **plaintext inside a OneDrive-synced folder**
(`...\OneDrive\Desktop\Nestler\...`). That means the secret values are replicated to
Microsoft's cloud and to every machine that syncs this OneDrive account — a much larger
exposure surface than a local-only dotfile. Treat all of the following as potentially
exposed and rotate them:

| Secret | Where to rotate | Why |
|---|---|---|
| `GEMINI_API_KEY` (and `_2`, `_3`) | Google AI Studio / Cloud console (each key is in a different GCP project) | Plaintext in OneDrive-synced `.env` |
| `YOUTUBE_API_KEY` | Google Cloud console | Same exposure |
| `DUMPLING_API_KEY` | dumpling.ai dashboard | Same exposure |
| `ADMIN_API_KEY` | Generate a new random string; update Railway variable | Same exposure; gates admin endpoints |
| Railway Postgres password | Railway dashboard (reset database credentials), then update `DATABASE_URL` / `RAILWAY_DATABASE_URL` everywhere | Connection strings with the password are in the `.env` |

After rotating, update the values in Railway's Variables tab and in the local `.env`.

## Recommendations

1. **Keep runtime secrets only in Railway environment variables.** The deployed app reads
   everything from the environment; it does not need a `.env` file in production. The local
   `.env` should exist only for local development, ideally outside any cloud-synced folder
   (or move the repo out of OneDrive).
2. Never commit `.env`; use `.env.example` (placeholders only) to document required keys.
3. Never paste secret values into docs, commits, issues, or chat logs.
4. If the repo ever needs to be shared/forked, re-run a history scan for secrets first
   (e.g. `gitleaks detect` or `trufflehog git`).
5. Consider enabling GitHub secret scanning + push protection on the `Bighabz/AI-Horizon`
   repo (Settings -> Code security).
