# ⚖️ Verdict — Shop the truth.

Verdict is an AI-powered Shopping Intelligence Platform: search products across multiple
Indian retailers, compare prices, get AI insights, and manage wishlists, search history,
and budgets — backed by Groq's Llama 3. One FastAPI backend serves both the JSON API and
a single-file frontend (`frontend/index.html`), no build step, no separate frontend server.

**This drop adds real authentication and has been verified end-to-end** — see "How this
was verified" below before you take my word for any of it.

---

## What's new in this drop

### One-command launcher (new)
`start.py` — see "Running it" below. It bootstraps `.env` (including a real random
`JWT_SECRET`, not the placeholder), detects whether MySQL is reachable, and falls back to
a bundled SQLite dev database when it isn't, so the whole app runs with just
`pip install -r requirements.txt && python start.py` — no MySQL setup required to try it
out. Verified live: registered a real user, logged in as the demo account, ran a product
search, and added/read a wishlist item — all through the actual running HTTP server, not
just the test suite — and confirmed data survives a server restart (it's a real SQLite
file, not in-memory) and that `.env`/`JWT_SECRET` aren't regenerated on every run.

While building it I found and fixed a bug in my own code before it shipped: mysql-connector's
`connection_timeout` argument requires an `int`, and I'd passed a `float` — every MySQL
reachability check was throwing `TypeError` and reporting "MySQL not reachable" for the
wrong reason. Functionally harmless (it still fell back to SQLite correctly either way),
but the error message was misleading. Fixed and re-verified the message is accurate now.

### Critical fix: the app didn't actually boot on a clean install
`requirements.txt` pinned `groq==0.9.0` but left `httpx` unpinned. `pip install -r
requirements.txt` today resolves `httpx` to `0.28.x`, which removed the `proxies` kwarg
that groq 0.9.0's internal client wrapper still passes — every service module that
imports Groq at module load time (`advisor_service`, `budget_service`,
`comparison_service`, `insight_service`) crashed with `TypeError: Client.__init__() got
an unexpected keyword argument 'proxies'` **on import**, which means `backend/main.py`
itself failed to start. This wasn't a corner case — it reproduced on a completely fresh
`python -m venv` + `pip install -r requirements.txt`, which is exactly how anyone
deploying this for the first time would hit it.

Fixed by pinning `httpx==0.27.2` (the last version before `proxies` was removed).
I only caught this because I re-ran verification in an actual clean virtual environment
instead of trusting the sandbox I'd already been installing packages into — worth doing
the same before you deploy.

### Authentication (new)
- `POST /api/v1/auth/register`, `POST /api/v1/auth/login`, `GET /api/v1/auth/me`.
- Passwords hashed with bcrypt (`passlib`); sessions are JWTs (`pyjwt`), 7-day expiry by
  default, signed with `JWT_SECRET`.
- **Every other `/api/v1/...` route now requires a valid token.** Endpoints that take a
  `user_id` in the path (`/user/wishlist/{user_id}`, `/user/history/{user_id}`,
  `/user/budget/history/{user_id}`) check that it matches the token's owner and return
  `403` otherwise — a user can no longer read or delete another user's data just by
  changing a number in the URL, which was possible before.
- Endpoints that take `user_id` in the *body* (`/products/search`, `/user/wishlist/add`,
  `/user/budget/plan`) now silently overwrite it with the authenticated user's real id —
  the field is kept for backward compatibility but a client can't spoof it.
- The demo account (`demo@verdict.ai` / `verdict123`) still works — its password is now a
  real bcrypt hash in `schema.sql` instead of a bare row with no password at all.
- The frontend gates the whole app behind a login/sign-up screen, stores the JWT in
  `localStorage`, attaches it to every request, and bounces back to login on a 401
  (e.g. expired session) instead of silently failing.

### Bug fixes carried over from the last review
- `comparison_service.py`: `compare_products()` had a ternary expression inside an
  f-string format spec, which is invalid Python and raised `ValueError` on every call —
  `/advisor/compare` was unreachable before this. Fixed; there's now a test asserting it
  doesn't crash.
- Budget plan responses use `item` / `allocated` / `percentage` / `suggestion` — the
  frontend now reads the correct fields (an earlier pass of mine had this wrong).
- `main.py` serves `frontend/index.html` at `/` and falls back to it for unknown paths
  (so client-side navigation doesn't 404 on refresh), while `/api/v1/...`, `/docs`,
  `/health` keep working normally — verified explicitly, see tests below.

### `backend/utils/config.py` / `logger.py`
These weren't in what you shared, so they're minimal stand-ins (see the note at the top
of `config.py`). If you already have real versions, keep yours — nothing else depends on
their internals beyond `settings.<ATTR>` and `get_logger(name)`.

---

## How this was verified

I didn't just eyeball this — `tests/test_integration.py` boots the **actual FastAPI app**
(`backend.main.app`) behind Starlette's `TestClient` and drives it through the real
routing/dependency-injection/Pydantic-validation stack. The only thing swapped out is the
database: `tests/fake_db.py` is an in-memory stand-in for MySQL (no server needed to run
the suite), patched into the four service modules that talk to it.

Run it yourself (a fresh virtualenv is worth the extra step — see above for why):
```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt   # httpx==0.27.2 is already pinned in here — don't
                                    # separately `pip install httpx` with no version, or
                                    # you'll pull 0.28+ and reintroduce the crash above
python3 tests/test_integration.py
```

**45/45 checks pass** (verified in a from-scratch `python -m venv` with the exact pinned
versions in `requirements.txt` — not just the sandbox I'd already been building in),
including:
- Every protected route rejects requests with no token, a garbage token, and an expired
  token (401), and rejects access to another user's wishlist/history/budget data (403).
- Register → duplicate-email rejected → login with wrong password rejected → login
  succeeds → `/auth/me` reflects the logged-in user.
- Product search respects filters end-to-end (e.g. `max_price` actually excludes pricier
  results, not just accepted-and-ignored).
- `/advisor/compare` returns 200 with a summary instead of crashing (the bug above).
- Advisor chat and budget planning both work correctly **without a live Groq key** — the
  suite runs with no network access, so these calls exercise the rule-based fallback paths
  your code already had, confirming those fallbacks are actually reachable and correct.
- Wishlist/history add → get → delete → clear, and budget plan → history, round-trip
  correctly through the real Pydantic models.
- Expired JWTs are rejected the same as malformed ones (not just "no token at all").
- A client sending someone else's `user_id` in the request body (e.g. wishlist add) gets
  silently overridden — the item lands under the *authenticated* user, not the spoofed id.
- Pydantic validation errors (422s) come back as a list of `{loc, msg, type}` objects, not
  a string — the frontend's `formatApiError()` turns that into a readable message instead
  of dumping raw JSON into the login/signup error box (this was broken before; fixed and
  the shape is now asserted in the test).
- `GET /` serves the SPA; unknown paths fall back to it for client-side routing;
  `/docs` still serves FastAPI's own Swagger UI rather than being swallowed by that
  fallback.

This is a genuine regression test, not a demo script — keep it around and re-run it after
any backend change.

---

## Running it

### The easy way — one command, zero setup

```bash
pip install -r requirements.txt
python start.py
```

That's it. `start.py`:
- Creates `.env` from `.env.example` if it doesn't exist yet, and generates a real random
  `JWT_SECRET` for you (no more copy-pasting a secret by hand).
- Checks whether MySQL (as configured in `.env`) is actually reachable. If it isn't —
  which is the normal case the first time you run this, before you've set up a database —
  it transparently falls back to a local SQLite file (`verdict_dev.db`) so the whole app
  still runs, including the demo login. **This fallback is for local dev only**; point
  `DB_*` at a real MySQL server in `.env` and it'll use that instead once it's reachable.
- Starts the one process that serves both the API and the frontend (`backend/main.py`
  mounts `frontend/index.html`), and opens it in your browser.

Useful flags:
```bash
python start.py --install       # also `pip install -r requirements.txt` first
python start.py --port 9000     # default is 8000, or $PORT if set
python start.py --no-browser    # don't auto-open a tab
python start.py --force-sqlite  # skip the MySQL check even if one's configured
python start.py --reload        # auto-restart on code changes, for active dev
```

Open **http://localhost:8000/** — log in with the demo account (`demo@verdict.ai` /
`verdict123`) or sign up. API docs at `/docs`.

### The manual way — real MySQL, no launcher magic

```bash
pip install -r requirements.txt
cp .env.example .env
# fill in DB_* and GROQ_API_KEY, and set a real JWT_SECRET:
python3 -c "import secrets; print(secrets.token_hex(32))"

mysql -u root -p < schema.sql
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

If the frontend is ever served from a different origin than the API, open it once with
`?api=https://your-api-host` — the override is remembered in `localStorage`.

---

## Deployment on Render

Still one service — see `render.yaml`. Add `JWT_SECRET` as a real secret (not the dev
default) alongside the existing DB/Groq env vars.

---

## Project structure

```
verdict/
├── backend/
│   ├── api/          # auth_routes (new), product/insight/advisor/user_routes
│   ├── services/      # auth_service (new), product/insight/advisor/comparison/wishlist/history/budget
│   ├── database/
│   │   ├── database.py           # real (MySQL) implementation
│   │   └── sqlite_fallback.py    # dev-only fallback used by start.py when MySQL isn't reachable
│   ├── models/models.py
│   ├── utils/config.py, security.py, logger.py
│   └── main.py
├── frontend/
│   └── index.html     # the entire SPA — no build step, no framework
├── tests/
│   ├── fake_db.py            # in-memory DB stand-in used only by the test suite
│   └── test_integration.py   # 45 end-to-end checks against the real app
├── start.py            # one-command launcher — see "Running it" above
├── schema.sql
├── requirements.txt
├── .env.example
├── render.yaml
└── README.md
```

## API Endpoints

| Method | Endpoint | Auth | Notes |
|---|---|---|---|
| POST | `/api/v1/auth/register` | — | Create account, returns a token |
| POST | `/api/v1/auth/login` | — | Returns a token |
| GET | `/api/v1/auth/me` | ✓ | Current user |
| POST | `/api/v1/products/search` | ✓ | `user_id` in body is ignored in favor of the token |
| POST | `/api/v1/insights/generate` | ✓ | |
| POST | `/api/v1/advisor/chat` | ✓ | |
| POST | `/api/v1/advisor/compare` | ✓ | Needs 2–3 products (422 if fewer, enforced by Pydantic) |
| GET/POST/DELETE | `/api/v1/user/wishlist/...` | ✓ | 403 if `{user_id}` isn't yours |
| GET/DELETE | `/api/v1/user/history/...` | ✓ | 403 if `{user_id}` isn't yours |
| POST/GET | `/api/v1/user/budget/...` | ✓ | 403 if `{user_id}` isn't yours |

## Ideas for next iterations

- Refresh tokens / shorter-lived access tokens if you want tighter session control than a
  flat 7-day JWT.
- Rate-limit `/auth/login` and `/auth/register` (not currently limited).
- Price-drop alerts: compare a wishlist item's saved price against a fresh cached price
  for the same product/retailer.
- Pagination once result sets grow past ~30 items.
