# LinkedIn Profile API

A FastAPI service that extracts structured LinkedIn profile data by calling LinkedIn's internal **Voyager API** — the same REST.li endpoint the web app uses. No browser automation, no HTML scraping.

Interactive API docs are available at `/docs` when the server is running.

## Why Voyager?

LinkedIn's public pages are heavily obfuscated JavaScript bundles. The Voyager API returns normalized JSON with an `included[]` array of typed entities (`Profile`, `Position`, `Education`, etc.) that can be denormalized into a clean schema. This approach is faster, more reliable, and easier to maintain than headless browser scraping — **as long as Voyager still exposes the entities you need**.

## LinkedIn SDUI migration (flagship-web)

LinkedIn’s web app is moving profile surfaces from Voyager REST/`decorationId` JSON to **SDUI** (Server-Driven UI) over **React Server Components**.

Observed in DevTools when opening a profile or skills details:

| UI | Request | Response shape |
|----|---------|----------------|
| Profile | `GET /flagship-web/in/{slug}/` | RSC Flight stream (not Voyager `included[]`) |
| Skills details | `GET /flagship-web/in/{slug}/details/skills/` | Same — SDUI layout tree |

Markers in those payloads:

- Screen IDs like `com.linkedin.sdui.flagshipnav.profile.Profile` and `...ProfileSkillDetails`
- Proto types under `proto.sdui.*` (layout, state, actions)
- Pagination via SDUI actions such as `proto.sdui.actions.requests.PaginationRequest` / `ServerRequest` (not Voyager `start`/`count` on `/profileSkills`)
- RSC Flight framing (`1:"$Sreact.fragment"`, `I["…module…",[],"ComponentName"]`)

**Why this matters for this API**

- Voyager `FullProfileWithEntities-*` still works for a large slice of profile data (identity, positions, education, first page of skills, etc.).
- Skills beyond the first ~20 used to be a separate Voyager collection call. That path is effectively dead (`/identity/dash/profileSkills` → 400; legacy `/identity/profiles/.../skills` → 410). The web UI now loads the full skills list through **flagship-web SDUI**, not Voyager.
- SDUI responses are UI trees (components + actions), not a stable entity bag. Parsing them for structured data is brittle compared to Voyager `$type` entities.

This service stays on Voyager while those endpoints remain useful. Expect gradual drift: more profile sections may vanish from Voyager and exist only under `/flagship-web/...`.

## Architecture

```
Client → POST/GET /api/profile → URL normalizer → cache check
  → Voyager client (httpx + retry) → parser (denormalize included[])
  → ProfileResponse JSON
```

| Layer | Responsibility |
|-------|----------------|
| `url_normalizer` | Extract vanity slug from URLs or plain slugs |
| `voyager_client` | Authenticated httpx call with cookies, CSRF, retry |
| `profile_parser` | Walk `included[]`, bucket by `$type`, resolve URNs |
| `profile_service` | Orchestrate normalize → cache → fetch → parse |
| `routes` | REST endpoints + rate limiting |

## Setup

### Prerequisites

- Python 3.12+
- Valid LinkedIn session cookies (`li_at`, `JSESSIONID`)

### Obtain session cookies

1. Log in to [linkedin.com](https://www.linkedin.com) in Chrome/Firefox.
2. Open DevTools → **Application** → **Cookies** → `https://www.linkedin.com`.
3. Copy:
   - `li_at` — long-lived auth token
   - `JSESSIONID` — session ID (also used as CSRF token)
4. Copy your browser **User-Agent** string from DevTools → Network → any request → Request Headers.

> **Security:** Never commit cookies. They grant full access to your LinkedIn account.

### Local development

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
# Edit .env with your LI_AT, JSESSIONID, USER_AGENT

uvicorn app.main:app --reload --port 8000
```

Visit [http://localhost:8000/docs](http://localhost:8000/docs) for Swagger UI.

### Docker

```bash
docker build -t linkedin-profile-api .
docker run -p 8000:8000 \
  -e LI_AT=your_cookie \
  -e JSESSIONID=your_session \
  -e USER_AGENT="Mozilla/5.0 ..." \
  linkedin-profile-api
```

## API Reference

### `GET /health`

Health check.

```bash
curl http://localhost:8000/health
# {"status":"ok"}
```

### `GET /api/profile?url=`

Fetch a profile by LinkedIn URL or vanity slug.

```bash
curl "http://localhost:8000/api/profile?url=https://www.linkedin.com/in/john-doe/"
```

### `POST /api/profile`

Same as GET, with JSON body.

```bash
curl -X POST http://localhost:8000/api/profile \
  -H "Content-Type: application/json" \
  -d '{"url": "john-doe"}'
```

### Response schema

Returns a `ProfileResponse` with:

- **Identity:** `first_name`, `last_name`, `headline`, `summary`, `public_identifier`, `profile_url`, `urn`
- **Media:** `profile_picture_url`, `cover_picture_url`
- **Location:** `location` (city, state, country, display)
- **Experience:** `positions[]` (title, company, dates, description)
- **Education:** `educations[]`
- **Skills:** `skills[]`
- **Certifications:** `certifications[]`
- **Languages:** `languages[]`
- **Metadata:** `fetched_at`

### Accepted URL formats

| Input | Extracted slug |
|-------|----------------|
| `https://www.linkedin.com/in/john-doe/` | `john-doe` |
| `http://linkedin.com/in/john-doe?foo=bar` | `john-doe` |
| `linkedin.com/in/john-doe` | `john-doe` |
| `john-doe` | `john-doe` |

### Error codes

| HTTP | `error` | When |
|------|---------|------|
| 400 | `invalid_url` | Malformed or non-LinkedIn input |
| 401 | `unauthorized` | Session cookies expired/invalid |
| 403 | `forbidden` | LinkedIn denied access |
| 404 | `not_found` | Profile does not exist |
| 429 | `rate_limit_exceeded` | LinkedIn or API rate limit hit |
| 502 | `upstream_error` | LinkedIn 5xx or network failure |

All errors return: `{"error": "...", "detail": "...", "status": N}`

## Voyager API details

**Endpoint:**

```
GET /voyager/api/identity/dash/profiles
  ?q=memberIdentity
  &memberIdentity={vanity_slug}
  &decorationId=com.linkedin.voyager.dash.deco.identity.profile.FullProfileWithEntities-91
```

**Required headers:**

| Header | Value |
|--------|-------|
| `Cookie` | `li_at=...; JSESSIONID="..."` |
| `csrf-token` | Raw JSESSIONID value (without quotes) |
| `x-restli-protocol-version` | `2.0.0` |
| `Accept` | `application/vnd.linkedin.normalized+json+2.1` |
| `User-Agent` | Realistic browser UA |

**Response structure:** Top-level `data` references profile URNs; `included[]` holds denormalized entities keyed by `$type`. The parser buckets entities and resolves cross-references (e.g. profile picture URN → `PhotoFilterPicture` → `rootUrl` + largest artifact segment).

## Configuration

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `LI_AT` | Yes | — | LinkedIn auth cookie |
| `JSESSIONID` | Yes | — | Session / CSRF cookie |
| `USER_AGENT` | Yes | — | Browser user-agent string |
| `CACHE_TTL_SECONDS` | No | `3600` | In-memory cache TTL per slug |
| `RATE_LIMIT` | No | `30/minute` | Per-IP limit on `/api/profile` |
| `LOG_LEVEL` | No | `INFO` | Logging level |

## Design trade-offs

- **Cookie auth is fragile** — sessions expire; you must refresh cookies manually.
- **Single-account throughput** — one LinkedIn session serves all requests; caching and rate limiting protect it.
- **Schema drift** — LinkedIn may change `$type` names or decoration IDs; the parser uses suffix matching to be resilient.
- **Retry policy** — transient 5xx and network errors retry up to 3× with exponential backoff; 401/403/404 are not retried.
- **In-memory cache** — fast for single-instance deploys; swap `InMemoryTTLCache` for Redis in multi-instance setups.

## Known limitations

- Session cookies expire (typically days to weeks).
- LinkedIn may return 429 under heavy use or bot detection.
- Only works for profiles visible to the authenticated account.
- LinkedIn Terms of Service may restrict automated access — use responsibly.
- `decorationId` values can change; update `app/config.py` if profiles return empty data.
- **Skills truncation:** Voyager injects only the first skills page (~20). `skills_total` reports the full count when present. Remaining skills live on the SDUI skills screen (`/flagship-web/in/{slug}/details/skills/`); Voyager follow-up pagination is no longer available.
- **SDUI drift:** Profile and skills details in the web app increasingly use `/flagship-web/...` SDUI/RSC instead of Voyager. See [LinkedIn SDUI migration](#linkedin-sdui-migration-flagship-web).

## Testing

```bash
pip install -r requirements.txt
pytest -v
```

Tests cover:

- URL normalizer (all input variants + rejections)
- Parser against `tests/fixtures/voyager_sample.json`
- API integration with `respx` mocks (200, 401, 404, 429)
- ASGI endpoint tests via `httpx.ASGITransport`

## Web UI

A small static demo lives in `web/` — paste a LinkedIn URL, call `GET /api/profile`, and render the response as a profile card (header, about, experience, education, skills, certifications, languages, featured media).

No build step. No secrets in the browser. The UI is read-only and talks to your hosted FastAPI backend over HTTPS (CORS is already open on the API).

### Local usage

1. Start the API: `uvicorn app.main:app --reload --port 8000`
2. Open `web/index.html` in a browser, **or** serve it:

```bash
cd web && python -m http.server 5173
# then visit http://localhost:5173/?api=http://localhost:8000
```

API base resolution (first match wins):

1. `?api=` query param (also saved to `localStorage`)
2. `localStorage` key `linkedin_profile_api_base`
3. Default in `web/app.js` (`DEFAULT_API_BASE` — set this to your Render URL)

### Deploy UI on Vercel

1. Push the repo to GitHub.
2. In [Vercel](https://vercel.com), **Import** the repo.
3. Set **Root Directory** to `web`.
4. Framework preset: **Other** (no build command, no output directory).
5. Deploy.

Or via CLI:

```bash
npx vercel --cwd web
```

After deploy, open `https://<project>.vercel.app/?api=https://<your-service>.onrender.com` once so the UI remembers your API base — or edit `DEFAULT_API_BASE` in `web/app.js` before deploying.

## Deployment (Render)

This repo includes a `render.yaml` blueprint and `Dockerfile`. The **API** stays on Render; the **UI** is the separate Vercel static site above.

### Deploy via Render Dashboard

1. Push this repo to GitHub.
2. In [Render](https://render.com), create a **New Blueprint** and connect the repo.
3. Set secret environment variables in the dashboard:
   - `LI_AT`
   - `JSESSIONID`
   - `USER_AGENT`
4. Deploy. Render provides HTTPS automatically.
5. Verify: `https://<your-service>.onrender.com/health` and `/docs`.

### Deploy via Render CLI

```bash
# Install: https://render.com/docs/cli
render login
render blueprint launch  # from repo root with render.yaml
```

Set secrets in the Render dashboard after the service is created.

## Project structure

```
app/
├── main.py              # FastAPI app, exception handlers, CORS
├── config.py            # pydantic-settings
├── api/routes.py        # /api/profile, rate limiting
├── core/
│   ├── url_normalizer.py
│   ├── voyager_client.py
│   └── errors.py
├── parsers/profile_parser.py
├── models/
│   ├── requests.py
│   └── profile.py
└── services/
    ├── cache.py
    └── profile_service.py
web/                     # Static demo UI (Vercel)
├── index.html
├── app.js
└── vercel.json
tests/
├── fixtures/voyager_sample.json
├── test_url_normalizer.py
├── test_parser.py
└── test_api.py
```

## License

MIT — use at your own risk regarding LinkedIn ToS compliance.
