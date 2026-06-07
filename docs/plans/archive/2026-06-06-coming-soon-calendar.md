<!-- orchestrator-native-plan: v1 -->

## Orchestrator execution contract — READ FIRST (how `/execute-plan` runs this slice)

- **Task ids:** literal labels `T1 T2 T3 T4`, used verbatim in `orchestrator_begin`/`orchestrator_report`.
- **Dependency levels:** strictly sequential — `T1 → T2 → T3 → T4`. No parallel level: T2 calls T1's client methods, T3 consumes T2's JSON contract wholesale, T4 documents the finished shape. NEVER `isolated: true`.
- **ONE barrier commit for the whole slice** — no commit per task. Everything lands at the barrier.
- **Fixture/snapshot regen:** none in this slice (no snapshots, no golden fixtures). Nothing to authorize.
- **Per-task `Verify`** is stated on each task. The barrier runs the full gate: `cd backend && pytest` **and** `cd frontend && npm run test`.
- **Closure is `/execute-plan` Step 9's job** — CHANGELOG version bump, roadmap status flip, and README are NOT tasks here. T4 touches only `CLAUDE.md`'s project-structure map.

---

# Slice: Coming-Soon / Calendar view (Roadmap Tier 2 #5)

**Date:** 2026-06-06
**Topic:** coming-soon-calendar
**Planning scope:** Medium — one new backend module + two thin client methods + one new frontend view/service/util. ~4 tasks.

## Goal

An on-demand agenda screen that lists what's releasing soon for tracked things:
upcoming episodes of shows in Sonarr, movie release dates from Radarr, and release
dates for watchlist movies not yet in the library. **On-demand fetch on page open —
no background scheduler** (honors the roadmap constraint).

**Acceptance (from roadmap):** Opening the view lists episodes airing this week plus
upcoming watchlist movie release dates.

## Engineering-contract notes (from `CLAUDE.md`)

- **Module-per-feature** convention: new code goes in `backend/src/app/modules/calendar/`.
- **Client factory** convention: reuse `get_radarr_client` / `get_sonarr_client` imported from their
  routers (the `library` router already does this — mirror it).
- **Pure, unit-tested util** convention: agenda normalization/merge/sort logic lives in a pure module
  (`calendar/service.py` backend, `utils/calendarState.js` frontend), thin glue in router/view.
- **Media-type convention:** app uses `"show"` internally, `"tv"` for TMDB calls.
- **No new DB column** is introduced → **no migration needed** (avoids the v2.4.1 "no such column" trap entirely).
- Type hints on all functions; async/await for I/O; `<script setup>` Composition API; services auto-unwrap `response.data`.

## Shared contract — unified agenda entry (T2 emits, T3 consumes)

`GET /api/calendar?start=<YYYY-MM-DD>&end=<YYYY-MM-DD>` → `{ "items": [ <entry>, ... ] }`,
`items` sorted by `date` ascending. Each entry:

```json
{
  "date": "2026-06-10",
  "kind": "episode" | "movie",
  "source": "sonarr" | "radarr" | "watchlist",
  "title": "Show or Movie title",
  "subtitle": "S02E05 · Episode title",   // episodes only; null otherwise
  "tmdb_id": 123,                           // null when unavailable
  "in_library": true                        // sonarr/radarr = true; watchlist = false
}
```

`start`/`end` are optional; default window = today (UTC) through today + 7 days, formatted `YYYY-MM-DD`.

---

## T1 — Radarr & Sonarr `get_calendar` client methods

**Target files:**
- `backend/src/app/modules/radarr/client.py` — add `get_calendar`.
- `backend/src/app/modules/sonarr/client.py` — add `get_calendar`.
- `backend/tests/test_calendar_clients.py` — **new** test file.

**Change (APIs/patterns):**
- `RadarrClient.get_calendar(self, start: str, end: str) -> list[dict]:`
  → `return await self._get("/calendar", {"start": start, "end": end, "unmonitored": False})`
- `SonarrClient.get_calendar(self, start: str, end: str) -> list[dict]:`
  → `return await self._get("/calendar", {"start": start, "end": end, "includeSeries": True})`
- Both go through `BaseArrClient._get`, which already prefixes `/api/v3` and attaches `X-Api-Key`.
- Type hints required; keep them one-liners mirroring `get_queue`/`get_recent`.

**Tests (TDD — write first, watch fail, then implement):**
- `test_radarr_get_calendar`: `patch.object(client, "_get", AsyncMock())` returns a sample movie record list;
  assert the method passes through and `_get` was called with `"/calendar"` and the start/end/`unmonitored` params.
- `test_sonarr_get_calendar`: same shape, assert `"/calendar"` + start/end/`includeSeries` params and passthrough.
- Use the existing `RadarrClient(url=..., api_key="test_key")` / `SonarrClient(...)` fixtures pattern from
  `test_radarr_client.py` (mark async with `@pytest.mark.asyncio`; `asyncio_mode = "auto"` is set in `pyproject.toml`).

**Verify-at-impl:**
- Confirm Radarr `/api/v3/calendar` and Sonarr `/api/v3/calendar` accept `start`/`end` (ISO date) and that
  Sonarr accepts `includeSeries=true`. If a param name differs, fix the dict but keep the passthrough shape.

- **Verify (run as the task gate):** `cd backend && pytest -q tests/test_calendar_clients.py`

---

## T2 — Calendar aggregation: pure normalizer + endpoint (new `calendar` module)

**Depends on:** T1.

**Target files:**
- `backend/src/app/modules/calendar/__init__.py` — **new**; export `router`.
- `backend/src/app/modules/calendar/service.py` — **new**; pure normalization/merge/sort functions (no I/O).
- `backend/src/app/modules/calendar/router.py` — **new**; the aggregating endpoint.
- `backend/src/app/main.py` — register the new router.
- `backend/tests/test_calendar_service.py` — **new**; pure-function unit tests.
- `backend/tests/test_calendar_router.py` — **new**; endpoint test with mocked deps.

**Change (APIs/patterns):**

`service.py` — pure, fully unit-testable (crafted dicts in, normalized list out):
- `default_window(today: date) -> tuple[str, str]` → `(today, today+7d)` as `YYYY-MM-DD`.
- `normalize_sonarr(records: list[dict]) -> list[dict]`: per episode build an entry —
  `date` from `airDateUtc` (fallback `airDate`), date-portion only; `title` from `series.title`
  (fallback `seriesTitle`); `subtitle` = `f"S{seasonNumber:02d}E{episodeNumber:02d} · {title}"`;
  `kind="episode"`, `source="sonarr"`, `in_library=True`, `tmdb_id` from `series.tmdbId` when present.
- `normalize_radarr(records: list[dict], start: str) -> list[dict]`: per movie pick the soonest release
  date `>= start` among `digitalRelease` / `physicalRelease` / `inCinemas`; skip records with no such date;
  `kind="movie"`, `source="radarr"`, `in_library=True`, `tmdb_id` from `tmdbId`.
- `normalize_watchlist_movies(movies: list[dict], start: str, end: str) -> list[dict]`: input is pre-resolved
  `{tmdb_id, title, release_date}`; keep those with `start <= release_date <= end`; `kind="movie"`,
  `source="watchlist"`, `in_library=False`.
- `build_agenda(sonarr, radarr, watchlist, start, end) -> list[dict]`: concat the three normalized lists,
  drop entries with a falsy `date`, sort ascending by `(date, title)`.

`router.py` — thin glue (mirror `library/router.py`):
- `router = APIRouter(prefix="/api/calendar", tags=["calendar"])`.
- Module-level `tmdb_client = TMDBClient(api_key=settings.tmdb_api_key)` (mirror `discovery/router.py`,
  so tests can `patch("app.modules.calendar.router.tmdb_client.get_details", ...)`).
- Reuse `from app.modules.watchlist.router import get_service` for DB-backed watchlist access (override-able in tests).
- `GET ""` handler `get_calendar(start: str | None = Query(None), end: str | None = Query(None), radarr=Depends(get_radarr_client), sonarr=Depends(get_sonarr_client), service=Depends(get_service))`:
  1. Resolve window via `default_window(datetime.now(timezone.utc).date())` when params omitted.
  2. `radarr_records, sonarr_records = await asyncio.gather(radarr.get_calendar(start,end), sonarr.get_calendar(start,end))`.
  3. Gather TMDB `get_details(tmdb_id, "movie")` for watchlist rows with `media_type == "movie"` and
     `status != "available"`; build `{tmdb_id, title, release_date}` dicts (skip failures, like `_enrich_watchlist_item` does).
  4. Return `{"items": build_agenda(...)}`.
- Register in `main.py`: `from app.modules.calendar import router as calendar_router` + `app.include_router(calendar_router)`.

**Tests (TDD — write first):**
- `test_calendar_service.py` (no mocks, pure):
  - sonarr normalization builds `S02E05 · …` subtitle, prefers `series.title`, extracts the date portion.
  - radarr normalization picks the soonest in-window date and **skips** a record whose only date is before `start`.
  - watchlist normalization keeps an in-window release and **drops** an out-of-window one.
  - `build_agenda` merges all three and returns them **sorted ascending by date**; drops entries with empty date.
  - `default_window` returns today and today+7 as `YYYY-MM-DD`.
- `test_calendar_router.py` (mirror `test_radarr_router.py` + `test_discovery_router.py`):
  - Override `get_radarr_client`/`get_sonarr_client` with `AsyncMock(spec=...)` and `get_service` with a fake
    returning `[]`; assert `200` and `{"items": []}` when everything is empty.
  - With mocked arr `get_calendar` returning one episode + one movie record (no watchlist), assert the two
    entries appear, correctly typed/sourced, and date-sorted.
  - With a fake watchlist movie + `patch` on `tmdb_client.get_details` returning a future `release_date`,
    assert a `source="watchlist"`, `in_library=False` entry appears.

**Verify-at-impl:**
- Confirm exact record field names against a real/sample *arr response: Sonarr `airDateUtc`/`airDate`,
  `series.title`/`seriesTitle`, `series.tmdbId`, `seasonNumber`/`episodeNumber`; Radarr
  `inCinemas`/`digitalRelease`/`physicalRelease`/`tmdbId`. Keep the normalizer defensive (`.get` with fallbacks).
- Confirm `settings.tmdb_api_key`, `settings.radarr_url/api_key`, `settings.sonarr_url/api_key` exist (already
  used by existing routers — they do) and that `get_service` is importable from `app.modules.watchlist.router`.

- **Verify (run as the task gate):** `cd backend && pytest -q tests/test_calendar_service.py tests/test_calendar_router.py`

---

## T3 — Frontend: calendar service, view, route, nav, pure state util

**Depends on:** T2 (consumes the agenda-entry contract above).

**Target files:**
- `frontend/src/services/calendar.js` — **new**.
- `frontend/src/utils/calendarState.js` — **new**; pure grouping/formatting helpers.
- `frontend/src/utils/calendarState.test.js` — **new**; Vitest unit tests.
- `frontend/src/views/CalendarView.vue` — **new**; agenda screen.
- `frontend/src/router/index.js` — add the `/calendar` route.
- `frontend/src/App.vue` — add the nav `<router-link>`.

**Change (APIs/patterns):**
- `calendar.js` (mirror `services/library.js`, services auto-unwrap `response.data`):
  `export const calendarService = { getCalendar: (start, end) => api.get('/calendar', { params: { start, end } }) }`
  (omit undefined params; axios drops them).
- `calendarState.js` — pure functions (mirror `discoverState.js`/`watchlistState.js` style):
  - `groupByDate(items)` → ordered array of `{ date, label, entries }` preserving the backend's ascending order
    (entries already sorted; group consecutively by `date`).
  - `formatDayLabel(dateStr)` → human label (e.g. `Wed, Jun 10`); pure, locale-stable enough to assert.
- `CalendarView.vue` (`<script setup>`, mirror `LibraryView.vue`): `onMounted` → `calendarService.getCalendar()`;
  render `groupByDate(items)` as date sections; each entry shows title, subtitle (episodes), a source/“in library”
  badge; empty + loading states. Use the `@/` alias (resolves to `src`, per `vite.config.js`).
- `router/index.js`: import `CalendarView`, add `{ path: '/calendar', name: 'calendar', component: CalendarView }`.
- `App.vue`: add `<router-link to="/calendar">Coming Soon</router-link>` in the `<nav>` (place after Library).

**Tests (TDD — write first):**
- `calendarState.test.js` (Vitest, mirror `watchlistState.test.js` import style):
  - `groupByDate` buckets entries sharing a `date` and preserves date order; returns `[]` for `[]`/null-safe input.
  - `groupByDate` keeps two different dates as two groups in ascending order.
  - `formatDayLabel` formats a known ISO date to its expected label and is null-safe (`''` for empty).

**Verify-at-impl:**
- Confirm Vitest auto-discovers `src/utils/*.test.js` (default glob; existing `discoverState.test.js`/
  `watchlistState.test.js` already live there) and that the `@/` alias resolves under Vitest (uses `vite.config.js`).

- **Verify (run as the task gate):** `cd frontend && npm run test`

---

## T4 — Docs: update `CLAUDE.md` project-structure map

**Depends on:** T2, T3 (documents the finished shape).

**Target files:**
- `CLAUDE.md` — project-structure + key-files map only. **No CHANGELOG / roadmap / README** (those are closure, Step 9).

**Change:**
- Under `backend/src/app/modules/` add: `calendar/   # Coming-Soon agenda: Radarr/Sonarr calendars + watchlist release dates`.
- Under `frontend/src/views/` add `CalendarView`; under `services/` add `calendar.js`; under `utils/` add
  `calendarState.js (agenda grouping/formatting; unit-tested)`.
- Optionally add a Key-Files row for `backend/src/app/modules/calendar/service.py` (pure agenda normalizer).

**Verify-at-impl:** none (docs only).

- **Verify (run as the task gate):** `cd backend && pytest -q tests/test_calendar_clients.py tests/test_calendar_service.py tests/test_calendar_router.py`

---

## Barrier (whole-slice gate, run by `/execute-plan`)

- `cd backend && pytest`
- `cd frontend && npm run test`

Then one barrier commit for T1–T4. Closure (CHANGELOG 2.11.0, roadmap #5 → SHIPPED, README) is Step 9.
