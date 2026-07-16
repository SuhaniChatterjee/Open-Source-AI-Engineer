# Deployment

Frontend on **Vercel**, API + worker + Postgres + Redis on **Render**, vectors on
**Qdrant Cloud**. Both platforms connect to this GitHub repo, so **every push to
`main` redeploys automatically**.

> **The app refuses to boot in production with insecure defaults.** If a required
> secret is missing, the API exits and logs exactly what to fix. That's intended —
> see `apps/api/app/core/startup_checks.py`. Read [Security](#security-why-the-gate-exists).

---

## 0. Generate your secrets first

Run these locally and keep the output handy:

```bash
# ENCRYPTION_KEY — encrypts stored provider/GitHub tokens at rest
python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"

# GITHUB_WEBHOOK_SECRET — any long random string
python3 -c "import secrets; print(secrets.token_hex(32))"
```

`SESSION_SECRET` is generated for you by Render (`generateValue: true`).

---

## 1. GitHub OAuth App (required — it's the only way to sign in)

<https://github.com/settings/developers> → **New OAuth App**

| Field | Value |
|---|---|
| Application name | OpenSource AI Engineer |
| Homepage URL | `https://<your-app>.vercel.app` |
| Authorization callback URL | `https://<your-app>.vercel.app/auth/callback` |

Save the **Client ID** and generate a **Client Secret**.

> You won't know the Vercel URL until step 2 — use a placeholder, then come back
> and correct it. The callback URL must match exactly.

---

## 2. Frontend → Vercel

1. <https://vercel.com/new> → import `SuhaniChatterjee/Open-Source-AI-Engineer`.
2. **Root Directory: `apps/web`** ← easy to miss; the build fails without it.
3. Environment variable:
   | Key | Value |
   |---|---|
   | `NEXT_PUBLIC_API_BASE` | `https://osae-api.onrender.com/api/v1` |
4. Deploy. Note the resulting URL.

Vercel auto-deploys on every push to `main` and builds a preview per PR.

---

## 3. Backend → Render (Blueprint)

1. <https://dashboard.render.com/blueprints> → **New Blueprint Instance** → pick this repo.
   Render reads [`render.yaml`](render.yaml) and creates: **osae-api** (web),
   **osae-worker** (Celery), **osae-postgres**, **osae-redis**.
2. Fill in the secrets it prompts for (everything marked `sync: false`):

| Key | Value |
|---|---|
| `ENCRYPTION_KEY` | the Fernet key from step 0 |
| `FRONTEND_URL` | `https://<your-app>.vercel.app` |
| `CORS_ORIGINS` | `https://<your-app>.vercel.app` |
| `GITHUB_CLIENT_ID` / `GITHUB_CLIENT_SECRET` | from step 1 |
| `QDRANT_URL` / `QDRANT_API_KEY` | from step 4 |
| `GITHUB_TOKEN` | *(optional)* a read-only PAT — raises GitHub search limits from 60/hr to 5000/hr |
| `GITHUB_WEBHOOK_SECRET`, `GITHUB_APP_*` | *(optional)* only for the GitHub App |

3. Deploy. Migrations run automatically on boot (`alembic upgrade head`).

**Free-tier notes**
- Render has **no free worker tier**. To stay strictly free, delete the
  `osae-worker` service and set `TASK_BACKEND=inline` on the API — jobs then run
  in the web process (fine for low traffic, slower under load).
- The free web service **sleeps after inactivity**; the first request takes ~50s.
- Free Postgres expires after 90 days — back up or upgrade before then.

---

## 4. Vectors → Qdrant Cloud

<https://cloud.qdrant.io> → free 1GB cluster → copy the **URL** and **API key**
into Render (`QDRANT_URL`, `QDRANT_API_KEY`).

> Skipping this "works" but silently falls back to an **embedded on-disk store on
> an ephemeral disk** — your index is wiped on every redeploy. Use the server.

---

## 5. Wire the loop back to GitHub

Once the Vercel URL is final:
1. Correct the OAuth App's callback URL (step 1).
2. Confirm `FRONTEND_URL` and `CORS_ORIGINS` on Render match it exactly.
3. Sign in at your Vercel URL → **Continue with GitHub**.

### Optional: GitHub App (webhooks)
<https://github.com/settings/apps> → New GitHub App. Webhook URL:
`https://osae-api.onrender.com/api/v1/webhooks/github`, with the secret from
step 0. Set `GITHUB_APP_ID`, `GITHUB_APP_SLUG`, `GITHUB_APP_PRIVATE_KEY`,
`GITHUB_WEBHOOK_SECRET` on Render. Pushes then auto-reindex and issue edits sync.

---

## The auto-deploy loop

```
git push origin main
      │
      ├─► GitHub Actions ── tests + typecheck + migration-drift check
      ├─► Vercel ────────── builds & deploys apps/web
      └─► Render ────────── rebuilds API + worker, runs migrations, health-checks
```

---

## Security: why the gate exists

Production **will not start** unless all of these hold. Each one is a real hole:

| Setting | Why |
|---|---|
| `ALLOW_DEV_LOGIN=false` | Dev-login signs you in as **any username with no password**. Public = instant account takeover. |
| `SESSION_SECRET` ≠ default | The default is a public string in this repo — anyone could forge session cookies. |
| `ENCRYPTION_KEY` set | Otherwise it's derived from `SESSION_SECRET`; stored GitHub/OpenAI tokens would be decryptable by anyone reading the repo. |
| `SESSION_COOKIE_SECURE=true` | Cookies must not travel over plain HTTP. |
| `DATABASE_URL` not SQLite | Hosting disks are ephemeral — your data would vanish. |
| GitHub OAuth set | With dev-login off, it's the only way in. |
| `CORS_ORIGINS` not localhost | The deployed frontend couldn't call the API. |

`SESSION_COOKIE_SAMESITE=none` is required because Vercel and Render are
different sites — with `lax` the browser silently drops the session cookie on
every API call, and login appears to do nothing.

---

## Troubleshooting

| Symptom | Cause |
|---|---|
| API exits on boot with "Refusing to start" | Working as designed — the log lists each missing/unsafe value. |
| Login redirects then lands signed-out | `SESSION_COOKIE_SAMESITE` isn't `none`, or `CORS_ORIGINS` ≠ your Vercel origin. |
| `redirect_uri_mismatch` | OAuth callback URL ≠ `<FRONTEND_URL>/auth/callback`. |
| CORS errors in console | `CORS_ORIGINS` missing your exact Vercel origin (scheme + host, no trailing slash). |
| Vercel build fails immediately | Root Directory isn't `apps/web`. |
| Index empty after redeploy | Qdrant Cloud not configured — it fell back to ephemeral on-disk. |
| First request takes ~50s | Render free tier cold start. |
