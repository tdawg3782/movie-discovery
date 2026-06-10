<!-- orchestrator-native-plan: v1 -->

## Orchestrator execution contract — READ FIRST (how `/execute-plan` runs this slice)

- **Task ids:** literal labels `T1 T2 … T9`, used verbatim in `orchestrator_begin`/`orchestrator_report`.
- **Dependency levels** stated explicitly; sequential unless tasks are file-disjoint (then a parallel level is allowed). NEVER `isolated: true` for disjoint tasks.
- **ONE barrier commit for the whole slice** — no commit per task. Regression fixtures/snapshots regenerate into the working tree per task; everything lands at the barrier.
- **Plan-mandated fixture/snapshot regen is AUTHORIZED** (label it): adding `respx` to `[project.optional-dependencies].dev` in `backend/pyproject.toml` and the resulting `uv.lock` regen (T1) is plan-authorized.
- **Per-task `Verify` command** stated explicitly (scoped `cd backend && uv run pytest -q <files>`; the barrier uses `cd backend && uv run pytest` plus `cd frontend && npm run test`).
- **Closure is `/execute-plan` Step 9's job** — the docs task (T9) covers only project-specific docs (CHANGELOG, CLAUDE.md), never the closure snapshot/roadmap. Step 9 closure MUST also flip the resolved checkboxes in `docs/audits/2026-06-10-audit-3.md` (and the corresponding duplicates in `2026-06-10-audit.md` / `2026-06-10-audit-2.md`) to `[x]` — anchored prefix replace, preserve the long line bodies.
- **Recommended thinking:** `high` — H1×M7 is a real design with interacting constraints (DB-first credential precedence + persistent connection pools + import-time singletons + preserving existing test seams); a wrong factory design cascades through every router.

---

# Slice: External-client layer — settings split-brain, lifecycle, resilience

**Source:** `docs/audits/2026-06-10-audit-3.md`
**Findings resolved:** H1, H5, H6, H7, M1, M2, M6, M7, M9, TG2, TG3, TG4 (12 checkboxes)
**Deferred (explicitly NOT in this slice):** C1/M11 (auth — needs a product decision: shared API key vs Cloudflare Access; own slice), H8 (MediaCache read-through — own design), H9 (encryption-key lifecycle), M8 (cache-ordering semantics decision), H10/M4/M5/TG8 (frontend state slice), TG6 (full respx client-test suite — T1 seeds the pattern), L2/L4–L9.

## Design decisions (settled here, not at impl time)

**D1 — Shared client factory module `backend/src/app/modules/clients.py` (new):**
- `tmdb_client = TMDBClient(api_key="")` — ONE module-level singleton instance. `get_tmdb_client() -> TMDBClient` refreshes `tmdb_client.api_key = get_setting("tmdb_api_key") or ""` and returns the singleton. TMDB sends the key per-request (query param), so mutating the attribute takes effect immediately while the connection pool persists (M7). The instance never swaps → tests patch instance methods at one canonical path: `app.modules.clients.tmdb_client.<method>`.
- `async def get_radarr_client() -> RadarrClient` / `async def get_sonarr_client() -> SonarrClient`: resolve `url = get_setting("<svc>_url") or settings.<svc>_url` and `api_key = get_setting("<svc>_api_key") or ""`; return the cached instance when `(cached.url, cached.api_key)` matches; otherwise `await cached.close()` (if any), build a fresh client, cache, return. Arr clients bake `X-Api-Key` into the httpx pool headers at `_get_client()`, so a credential change MUST swap the pool; an unchanged-credential request reuses the persistent pool (M7). Accepted edge: a request in flight during a credential swap may fail once — credential changes are rare, `_get_client()` self-heals on `is_closed`.
- `async def close_all_clients() -> None`: closes the TMDB singleton + cached arr clients (called from lifespan shutdown).
- **Test-seam preservation (load-bearing):** `radarr/router.py` and `sonarr/router.py` replace their local factory bodies with `from app.modules.clients import get_radarr_client / get_sonarr_client` re-exports — the SAME function objects, so every existing `app.dependency_overrides[get_radarr_client]` site (test_radarr_router, test_sonarr_router, test_sonarr_seasons_endpoint, test_calendar_router, test_recommendations_router, test_library_activity, …) keeps working unchanged. Imports in calendar/library/recommendations routers (`from app.modules.radarr.router import get_radarr_client`) still resolve to the same object — leave them.

**D2 — Global httpx exception handlers in `main.py` (H6):** `@app.exception_handler` for `httpx.TimeoutException` → 504, `httpx.RequestError` → 503 (`"<detail: upstream service unreachable>"`), `httpx.HTTPStatusError` → 502. Starlette resolves handlers by walking `type(exc).__mro__`, so the more-specific TimeoutException handler wins over RequestError; existing per-endpoint handlers (which run first) stay as-is. TMDB errors are already wrapped in `TMDBClientError` and never escape as raw httpx errors, so these handlers only catch arr failures. Generic messages only — no `str(e)` leakage.

**D3 — Degraded-source aggregation (H5):** `calendar` and `library` routers gather with `return_exceptions=True`; a failed source substitutes `[]` / `{"records": []}` and appends its name to a `degraded: list[str]` key on the response (always present, `[]` when healthy — additive, non-breaking). `CalendarView.vue` / `LibraryView.vue` render a small inline warning banner when `degraded` is non-empty (no frontend tests required; views are untested glue per project convention).

**D4 — H7 scope:** recommendations router logs a warning and sets a local `degraded` flag when either arr fetch fails; the cache is written ONLY when `rec_results` is non-empty AND not degraded. No response-schema change (`MediaList` is shared with discovery — do not add fields to it).

---

## Dependency levels

| Level | Tasks | Rationale |
|---|---|---|
| 1 | T1, T2, T3 (parallel) | file-disjoint: clients/arr wiring vs config.py vs calendar/service.py |
| 2 | T4, T5 (parallel) | both need T1's `clients.py` / post-T1 `main.py`; mutually disjoint |
| 3 | T6, T7, T8 (parallel) | each touches a router file T4 rewrites; mutually disjoint |
| 4 | T9 | docs after all code lands |

---

## T1 — Client factory module + arr DB-first credentials + lifecycle (H1 arr-half, M7, TG2)

- **Target files:** `backend/src/app/modules/clients.py` (NEW), `backend/src/app/main.py` (lifespan only), `backend/src/app/modules/radarr/router.py`, `backend/src/app/modules/sonarr/router.py`, `backend/src/app/modules/watchlist/service.py` (`process_batch`), `backend/pyproject.toml` (+`respx` dev dep, AUTHORIZED), `backend/tests/test_client_factory.py` (NEW).
- **Change:**
  1. Create `clients.py` per **D1** (TMDB singleton + `get_tmdb_client`, credential-keyed cached `get_radarr_client`/`get_sonarr_client`, `close_all_clients`). Type hints on all functions.
  2. `radarr/router.py` / `sonarr/router.py`: delete the local env-only factory bodies; `from app.modules.clients import get_radarr_client` (resp. sonarr) — re-export, same names, so all `Depends(...)` references and test `dependency_overrides` keep working. Remove the now-unused `from app.config import settings` import if dead.
  3. `main.py` lifespan: after `yield`, `await close_all_clients()`.
  4. `watchlist/service.py` `process_batch`: replace `RadarrClient(settings.radarr_url, settings.radarr_api_key)` / `SonarrClient(...)` with `client = await get_radarr_client()` / `await get_sonarr_client()` (import from `app.modules.clients`). This kills the smoking-gun split (env client two lines above `get_setting()` root-folder reads).
  5. Add `respx>=0.21` to dev deps; `uv lock`/`uv sync` regen is plan-authorized.
- **Tests (TDD — write first, red, then implement):** in `test_client_factory.py`:
  - DB-saved `radarr_url`/`radarr_api_key` (seeded via `SettingsService` against the test DB) → `await get_radarr_client()` returns a client with the DB values (not env).
  - Credential change → factory returns a NEW instance and the old one is closed; unchanged credentials → SAME instance (persistent pool, M7).
  - respx integration (TG2): seed DB `radarr_url=http://db-radarr:7878`, mock the route with respx, drive `process_batch` (or a direct client `_get`) and assert the outbound request hit the DB-saved host — proving settings → wire.
  - `get_tmdb_client()` refreshes `api_key` from a DB-saved `tmdb_api_key` and returns the same singleton instance both calls.
- **Verify-at-impl:** confirm `TMDBClient._get` reads `self.api_key` at call time (lines 63–84, elided in pre-flight) — D1's mutate-in-place TMDB design depends on it; if the key were baked into a pool header, fall back to the swap-and-close pattern for TMDB too. Confirm how tests construct the settings DB (see `conftest.py` / `test_settings_service.py`) and reuse that fixture pattern.
- **Verify (run as the task gate):** `cd backend && uv run pytest -q tests/test_client_factory.py tests/test_radarr_router.py tests/test_sonarr_router.py tests/test_watchlist_batch.py tests/test_library_activity.py`

## T2 — `get_setting` hardening (M6, TG2 precedence half)

- **Target files:** `backend/src/app/config.py`, `backend/tests/test_config_settings.py`.
- **Change:** rewrite `get_setting`: `db = SessionLocal()` inside `try`, `db.close()` in `finally`; narrow the except to `(SQLAlchemyError, InvalidToken)` (`from sqlalchemy.exc import SQLAlchemyError`, `from cryptography.fernet import InvalidToken`); on catch, `logging.getLogger(__name__).warning("get_setting(%s) DB lookup failed: %s", key, exc)` then fall back to env. Keep return semantics identical (DB value if truthy, else env value if truthy, else None).
- **Tests (TDD):** replace the tautological assertion in `test_config_settings.py` with: (a) precedence — seed a Settings row via `SettingsService` + monkeypatch the env attr → DB value wins; (b) DB error path — patch `SettingsService.get_raw_value` to raise `InvalidToken` → env fallback returned AND a warning logged (`caplog`); (c) session always closed — patch `SessionLocal` to a tracking fake, assert `close()` called on the raising path.
- **Verify (run as the task gate):** `cd backend && uv run pytest -q tests/test_config_settings.py tests/test_settings_service.py`

## T3 — Calendar normalizer null-guard (M2, TG3)

- **Target files:** `backend/src/app/modules/calendar/service.py` (`normalize_sonarr`), `backend/tests/test_calendar_service.py`.
- **Change:** guard the subtitle: when both `seasonNumber`/`episodeNumber` are ints → `f"S{sn:02d}E{en:02d}"`, appending `f" · {episode_title}"` only when truthy; otherwise `subtitle = episode_title or None`. Record is kept (degraded), never raises.
- **Tests (TDD):** record missing `seasonNumber` (and one missing `episodeNumber`, one missing both + no title) → entry emitted, correct degraded subtitle, no exception; existing happy-path tests untouched.
- **Verify (run as the task gate):** `cd backend && uv run pytest -q tests/test_calendar_service.py`

## T4 — TMDB call sites → shared DB-aware client (H1 TMDB-half)

- **Target files:** `backend/src/app/modules/discovery/router.py`, `calendar/router.py`, `recommendations/router.py`, `watchlist/router.py`; test files whose patch paths move: `tests/test_discovery_router.py`, `test_filtered_discovery.py`, `test_genre_endpoints.py`, `test_movie_detail_endpoint.py`, `test_show_detail_endpoint.py`, `test_person_endpoint.py`, `test_collection_endpoint.py`, `test_calendar_router.py`, `test_recommendations_router.py` (+ any `tests/test_watch_providers.py` hits).
- **Change:**
  1. Delete the three module-level `tmdb_client = TMDBClient(api_key=settings.tmdb_api_key)` singletons (discovery, calendar, recommendations) and the per-call `TMDBClient(api_key=settings.tmdb_api_key)` constructions in `watchlist/router.py` (3 sites: get-watchlist, add, update-details).
  2. Endpoints obtain the client via `tmdb: TMDBClient = Depends(get_tmdb_client)` (preferred; matches the arr pattern) — `from app.modules.clients import get_tmdb_client`. Where an endpoint signature change is disproportionate (helper functions), calling `get_tmdb_client()` inline is acceptable; either way every request goes through the key-refreshing factory.
  3. Mechanical test update: patch targets `app.modules.<discovery|calendar|recommendations>.router.tmdb_client.<method>` → `app.modules.clients.tmdb_client.<method>` (same AsyncMock style — the singleton instance is shared, so instance-method patches behave identically). Do NOT touch the `app.modules.discovery.router.get_setting` patches (streaming_region — different seam, stays).
  4. Remove now-dead `settings` imports from the three routers.
- **Verify-at-impl:** grep for any remaining `TMDBClient(` construction outside `clients.py` and tests — there must be none in `src/`.
- **Verify (run as the task gate):** `cd backend && uv run pytest -q tests/test_discovery_router.py tests/test_filtered_discovery.py tests/test_genre_endpoints.py tests/test_movie_detail_endpoint.py tests/test_show_detail_endpoint.py tests/test_person_endpoint.py tests/test_collection_endpoint.py tests/test_calendar_router.py tests/test_recommendations_router.py tests/test_watchlist_router.py tests/test_watch_providers.py`

## T5 — Global httpx exception handlers (H6)

- **Target files:** `backend/src/app/main.py`, `backend/tests/test_radarr_router.py`, `backend/tests/test_sonarr_router.py`.
- **Change:** per **D2** — three `@app.exception_handler` registrations returning `JSONResponse` with generic details ("Radarr/Sonarr"-agnostic: `"Upstream service unreachable"` / `"Upstream service timed out"` / `"Upstream service error"`). Keep existing per-endpoint handlers. Optionally widen the existing endpoint `except` clauses from `TimeoutException` to also catch `httpx.ConnectError` → 503 with the service name — only if trivial; the global net is the requirement.
- **Tests (TDD):** with `TestClient(app, raise_server_exceptions=False)`, override the arr client dep with a mock whose `get_queue`/`get_recent`/`get_series_details`/`get_status` raise `httpx.ConnectError("refused")` → assert 503 (not 500) for `/api/radarr/queue`, `/api/radarr/recent`, `/api/sonarr/queue`, `/api/sonarr/recent`, `/api/sonarr/series/1/seasons`, `/api/radarr/status/1`; one `httpx.TimeoutException` case on an unguarded endpoint → 504.
- **Verify-at-impl:** confirm Starlette's handler lookup walks `__mro__` (TimeoutException beats RequestError) — if not, register only `RequestError` and branch inside the handler.
- **Verify (run as the task gate):** `cd backend && uv run pytest -q tests/test_radarr_router.py tests/test_sonarr_router.py tests/test_sonarr_seasons_endpoint.py tests/test_radarr_queue.py tests/test_radarr_recent.py tests/test_sonarr_queue.py tests/test_sonarr_recent.py`

## T6 — Degraded-source aggregation for calendar + library, watchlist-status filter (H5, M1, TG4)

- **Target files:** `backend/src/app/modules/calendar/router.py`, `backend/src/app/modules/library/router.py`, `frontend/src/views/CalendarView.vue`, `frontend/src/views/LibraryView.vue`, `backend/tests/test_calendar_router.py`, `backend/tests/test_library_activity.py`.
- **Change:**
  1. Per **D3**: `asyncio.gather(..., return_exceptions=True)` in `/api/calendar`, `/api/library/activity`, `/api/library/queue`; per failed source substitute `[]` / `{"records": []}`, log a warning, append `"radarr"`/`"sonarr"` to `degraded`; responses gain `"degraded": [...]` (always present).
  2. M1: change the watchlist filter `item.status != "available"` → `item.status not in ("added", "downloading")` so processed movies stop double-appearing.
  3. Frontend: in both views, when `response.degraded?.length`, render a small inline warning (`<sonarr/radarr> unreachable — showing partial results`) above the list; no other view changes.
- **Tests (TDD, TG4):** for calendar: `mock_sonarr.get_calendar.side_effect = httpx.ConnectError(...)` + healthy radarr → 200, radarr+watchlist items present, `degraded == ["sonarr"]`; the reverse; both library endpoints likewise (one down → 200 + healthy half + degraded flag). M1: a watchlist row with `status="added"` no longer yields a watchlist agenda entry; `status="pending"` still does.
- **Verify (run as the task gate):** `cd backend && uv run pytest -q tests/test_calendar_router.py tests/test_library_activity.py`

## T7 — For You: never cache degraded/empty results (H7)

- **Target files:** `backend/src/app/modules/recommendations/router.py`, `backend/tests/test_recommendations_router.py`.
- **Change:** per **D4** — track `degraded = False`; in each arr `except` block set it and `logger.warning(...)` (kill the silent `pass`); after aggregation, write `_cache` only when `rec_results` is non-empty and `not degraded`. Response content unchanged.
- **Tests (TDD):** (a) all TMDB recommendation calls fail → empty result returned but NOT cached (next request with working TMDB returns results — no 6h blackout); (b) radarr raises → result still served, cache NOT written, warning logged; (c) healthy path still caches (existing cache test keeps passing).
- **Verify (run as the task gate):** `cd backend && uv run pytest -q tests/test_recommendations_router.py tests/test_recommendations_service.py`

## T8 — Watchlist enrichment: fall back only on 404 (M9)

- **Target files:** `backend/src/app/modules/watchlist/router.py` (`_enrich_watchlist_item` + its three calling endpoints), `backend/tests/test_watchlist_router.py`.
- **Change:** `_enrich_watchlist_item` narrows its blanket `except Exception`: the placeholder (`TMDB:{id}`) path applies only when the title is genuinely missing (details `None`/404 per the `_get_or_none` contract); `TMDBClientError`/network errors propagate. The three endpoints (`GET /api/watchlist`, `POST /api/watchlist`, `PATCH /{item_id}/details`) wrap enrichment in `try/except TMDBClientError` → `HTTPException(502, "TMDB unavailable")` so an outage is an explicit error, not a list of garbage rows.
- **Verify-at-impl:** check `TMDBClient.get_details` semantics (raise vs return-None on 404 — lines 64+ elided in pre-flight) and shape the guard accordingly; keep the 404→placeholder behavior pinned by any existing test.
- **Tests (TDD):** (a) `get_details` 404/None → row enriched as placeholder, 200 (existing behavior pinned); (b) `get_details` raises `TMDBNetworkError` → endpoint returns 502, not a `TMDB:{id}` list.
- **Verify (run as the task gate):** `cd backend && uv run pytest -q tests/test_watchlist_router.py tests/test_watchlist_status.py`

## T9 — Project docs

- **Target files:** `CHANGELOG.md`, `CLAUDE.md`.
- **Change:** CHANGELOG `[2.13.0]` entry — Fixed: settings split-brain (UI-saved keys/URLs now reach every client, DB-first), one-arr-down no longer 500s calendar/library (degraded flag + partial results), arr-unreachable now 503/504 instead of raw 500, calendar survives malformed Sonarr records, processed movies no longer double-listed, For You stops caching degraded/empty results, watchlist surfaces TMDB outages as 502 instead of placeholder rows, `get_setting` no longer leaks sessions/swallows errors; Changed: shared persistent clients with lifespan shutdown (`modules/clients.py`). CLAUDE.md: update the **Client factories** Architecture Patterns row (factories live in `modules/clients.py`, DB-first credentials via `get_setting()`, persistent pools closed on shutdown) and add a Key Files row for `clients.py`. NO closure snapshot/roadmap work (Step 9's job; Step 9 also flips the audit checkboxes).
- **Verify (run as the task gate):** `cd backend && uv run pytest -q tests/test_client_factory.py` (sanity only; docs task)

---

## Barrier (after T9, before the single slice commit)

- `cd backend && uv run pytest` — full suite green (was 231 passing pre-slice; expect strictly more).
- `cd frontend && npm run test` — Vitest utils suite green (views changed are untested glue; utils must not regress).
- ONE commit for the whole slice.
