<!-- orchestrator-native-plan: v1 -->

## Orchestrator execution contract — READ FIRST (how `/execute-plan` runs this slice)

- **Task ids:** literal labels `T1 T2 T3 T4 T5`, used verbatim in `orchestrator_begin`/`orchestrator_report`.
- **Dependency levels:**
  - **Level 1 (parallel — file-disjoint):** `T1` (TMDB client), `T2` (pure service), `T4` (frontend). No shared files.
  - **Level 2 (sequential):** `T3` (router) — imports `get_recommendations` from T1 and the pure functions from T2; also edits `main.py`.
  - **Level 3 (sequential, last):** `T5` (project docs) — describes the final shape.
  - NEVER `isolated: true` for the disjoint Level-1 tasks; they share a working tree.
- **ONE barrier commit for the whole slice** — no commit per task. All files land at the barrier.
- **Fixture/snapshot regen:** NONE in this slice (no snapshots, no golden files, no DB migration). If a test needs data it is constructed inline.
- **Per-task `Verify`** is stated on each task (scoped `pytest -q` / `npm run test`). The **barrier** runs the full gate: `cd backend && pytest && cd ../frontend && npm run test && npm run build`.
- **Closure is `/execute-plan` Step 9's job** — `T5` touches only CHANGELOG / README / CLAUDE.md. It does **NOT** flip the roadmap spec status or write the closure snapshot.

---

# Slice: Personalized discovery — Step 1 ("For You" aggregate recommendations)

**Roadmap item:** Tier 3 #7, Step 1 (flagship, multi-step). This slice ships Step 1 only.
**Planning scope:** medium-large (new backend module + TMDB method + in-process cache + new frontend view; 5 tasks).
**Version target:** 2.12.0.

## What ships

A new **"For You"** surface (`GET /api/for-you` → `/for-you` view) that recommends titles the
user does **not** already have. It seeds from the user's own data — watchlist items plus the
owned Radarr/Sonarr libraries — fetches TMDB recommendations for each seed, aggregates them
(frequency + vote + popularity ranking), and **excludes anything already watchlisted or owned**.
Results are cached in-process (single-user app) with a manual `refresh`. TMDB-only; no external
account; no DB change; no background scheduler.

## Acceptance (from roadmap)

- The recommended surface **excludes owned/watchlisted titles** (verified by router tests).
- It is driven by local data (watchlist + owned library) — empty data ⇒ empty surface, no TMDB calls.
- Visibly responds to local state: adding/owning a title changes seeds ⇒ changes output (cache keyed on seed signature; `refresh=true` bypasses).

## Design decisions (grounded in current code)

- **Seed + exclusion sources.** Watchlist (`WatchlistService.get_all()`, each row has `media_type`
  `"movie"|"show"` + `tmdb_id`) ∪ owned Radarr movies (`RadarrClient.get_all_movies()`, dicts carry
  `tmdbId`) ∪ owned Sonarr series (`SonarrClient.get_all_series()`). Domain key is a `(media_type, tmdb_id)`
  tuple with `media_type ∈ {"movie","show"}`. Radarr ⇒ `"movie"`, Sonarr ⇒ `"show"`.
- **`LibraryStatus` table is NOT used** — it is defined in `models.py` but never written or queried;
  owned state comes from live Radarr/Sonarr (matches `library`/`calendar` modules). Do not read/write it.
- **Sonarr `tmdbId` is best-effort.** Sonarr keys on `tvdbId` everywhere else in the codebase; a series
  object's `tmdbId` may be absent/0. Skip any series whose `tmdbId` is falsy. `Verify-at-impl`.
- **Arr resilience.** `get_all_movies` / `get_all_series` are wrapped best-effort (try/except ⇒ `[]`):
  if Radarr/Sonarr are down the surface still works from the watchlist alone. This is graceful
  degradation, not masking — the feature's primary seed (watchlist) is local and always available.
- **`show → tv` mapping.** `TMDBClient._validate_media_type` accepts only `"movie"|"tv"` and raises on
  `"show"`. The router converts `"show"→"tv"` before calling TMDB and tags returned results back as `"show"`.
- **Response reuses `MediaList`/`MediaResponse`** (`app/schemas.py`) so `MediaCard` renders unchanged.
  Recommendations are excluded-from-owned by construction ⇒ `library_status=None`. Returned as a single
  page (`page=1`, `total_pages=1`, `total_results=len(results)`).
- **Caching = in-process TTL** (no DB). Single module-level dict in the router keyed on the seed
  signature (`frozenset` of seed keys); TTL `RECS_CACHE_TTL = 6*3600`s. `refresh=true` bypasses the read.
  A `reset_cache()` helper exists for test isolation. No scheduler.
- **Constants:** `SEED_LIMIT = 20` (caps TMDB fan-out), `RESULT_LIMIT = 40` (caps returned items).

---

## T1 — TMDB client: `get_recommendations`

**Target files**
- `backend/src/app/modules/discovery/tmdb_client.py`
- `backend/tests/test_tmdb_client.py`

**Change**
- Add method mirroring `get_similar` (lines 113-116):
  ```python
  async def get_recommendations(self, tmdb_id: int, media_type: str) -> dict[str, Any]:
      """Get TMDB recommendations for a movie or show."""
      validated_type = self._validate_media_type(media_type)
      return await self._get(f"/{validated_type}/{tmdb_id}/recommendations")
  ```
  Place it directly after `get_similar`.

**Tests (TDD, mirror the `get_similar` tests)**
- `test_get_recommendations_movie`: patches `_get`, asserts called once with `/movie/123/recommendations`.
- `test_get_recommendations_tv`: asserts `/tv/456/recommendations`.
- `test_get_recommendations_invalid_media_type`: `await get_recommendations(123, "invalid")` raises
  `ValueError` matching `"media_type must be 'movie' or 'tv'"`.

**Verify-at-impl:** none.
- **Verify (run as the task gate):** `cd backend && pytest -q tests/test_tmdb_client.py`

---

## T2 — Pure recommendations service

**Target files** (new)
- `backend/src/app/modules/recommendations/__init__.py` — `from .router import router` / `__all__ = ["router"]`
  (mirror `calendar/__init__.py`). **Defer the `router` import until T3 exists** — for T2, create
  `__init__.py` with just the module docstring so `test_recommendations_service.py` can import
  `app.modules.recommendations.service` without T3. (T3 adds the `router` re-export.)
- `backend/src/app/modules/recommendations/service.py` — pure, no I/O (mirror `calendar/service.py`).
- `backend/tests/test_recommendations_service.py` — no mocks.

**Change — pure functions in `service.py`** (operate only on tuples/dicts, never ORM or clients):

```python
SEED_LIMIT = 20
RESULT_LIMIT = 40

Key = tuple[str, int]  # (media_type in {"movie","show"}, tmdb_id)

def select_seeds(watchlist_keys: list[Key], owned_keys: list[Key], limit: int = SEED_LIMIT) -> list[Key]:
    """Watchlist keys first, then owned; dedupe preserving order; cap at limit."""

def exclusion_set(watchlist_keys: list[Key], owned_keys: list[Key]) -> set[Key]:
    """Union of watchlisted + owned keys (everything the surface must never show)."""

def _normalize(item: dict, media_type: str) -> dict:
    """TMDB result -> MediaResponse-shaped dict: tmdb_id, media_type, title (title or name),
    overview, poster_path, release_date (release_date or first_air_date), vote_average,
    library_status=None."""

def aggregate(rec_results: list[tuple[str, list[dict]]], exclude: set[Key],
              limit: int = RESULT_LIMIT) -> list[dict]:
    """rec_results: list of (media_type, tmdb_results_list).
    Accumulate per (media_type, id): frequency count; keep first-seen metadata.
    Drop any key in `exclude`. Sort by (frequency desc, vote_average desc, popularity desc).
    Return up to `limit` normalized dicts."""
```
- Frequency = number of distinct seed result-lists that recommended a key. `popularity` read from the
  raw TMDB item (`item.get("popularity", 0)`); falsy `vote_average` sorts as 0.0.

**Tests (no mocks, mirror `test_calendar_service.py` style)**
- `select_seeds` dedupes, caps at limit, orders watchlist-before-owned.
- `exclusion_set` is the union.
- `aggregate` ranks a key recommended by 2 lists above one recommended once.
- `aggregate` tie-break: equal frequency ⇒ higher `vote_average` first; then higher `popularity`.
- `aggregate` excludes keys in `exclude` (owned/watchlisted absent from output).
- `aggregate` treats `("movie", 100)` and `("show", 100)` as distinct keys.
- `aggregate` caps output at `limit`.
- `_normalize` (or via `aggregate`): title falls back `name`, release falls back `first_air_date`,
  `library_status` is `None`.

**Verify-at-impl:** none.
- **Verify (run as the task gate):** `cd backend && pytest -q tests/test_recommendations_service.py`

---

## T3 — Recommendations router + wiring (depends on T1, T2)

**Target files**
- `backend/src/app/modules/recommendations/router.py` (new)
- `backend/src/app/modules/recommendations/__init__.py` (add `from .router import router`, `__all__`)
- `backend/src/app/main.py` (import + `app.include_router(recommendations_router)`)
- `backend/tests/test_recommendations_router.py` (new)

**Change — `router.py`** (mirror `calendar/router.py` imports + DI):
- `router = APIRouter(prefix="/api/for-you", tags=["recommendations"])`
- `tmdb_client = TMDBClient(api_key=settings.tmdb_api_key)` (module-level, like calendar).
- Module-level cache: `_cache: dict = {}`; `RECS_CACHE_TTL = 6 * 3600`; `reset_cache()` clears it.
- Endpoint:
  ```python
  @router.get("", response_model=MediaList)
  async def get_for_you(
      refresh: bool = Query(False),
      radarr: RadarrClient = Depends(get_radarr_client),
      sonarr: SonarrClient = Depends(get_sonarr_client),
      wl: WatchlistService = Depends(get_service),
  ):
  ```
  Steps:
  1. `watchlist_keys = [(i.media_type, i.tmdb_id) for i in wl.get_all()]`.
  2. Best-effort owned: `radarr.get_all_movies()` ⇒ `("movie", m["tmdbId"])` for truthy `tmdbId`;
     `sonarr.get_all_series()` ⇒ `("show", s["tmdbId"])` for **truthy** `tmdbId` (skip missing/0).
     Each wrapped in try/except ⇒ `[]` on failure.
  3. `seeds = service.select_seeds(watchlist_keys, owned_keys)`;
     `exclude = service.exclusion_set(watchlist_keys, owned_keys)`.
  4. If not `seeds`: return empty `MediaList(results=[], page=1, total_pages=1, total_results=0)`
     **without** calling TMDB.
  5. `sig = frozenset(seeds)`; if not `refresh` and `_cache.get("sig")==sig` and not expired ⇒ return cached `MediaList`.
  6. Fan out: for each seed `(mt, tid)`, call `tmdb_client.get_recommendations(tid, "tv" if mt=="show" else "movie")`
     via `asyncio.gather(..., return_exceptions=True)`; for each non-exception result build
     `(mt, data.get("results", []))`, dropping entries that raised.
  7. `ranked = service.aggregate(rec_results, exclude)`; build `MediaList(results=[MediaResponse(**r) for r in ranked], page=1, total_pages=1, total_results=len(ranked))`.
  8. Store `{"sig": sig, "value": media_list, "at": time.monotonic()}` in `_cache`; return.
- `main.py`: `from app.modules.recommendations import router as recommendations_router` and
  `app.include_router(recommendations_router)` after `calendar_router`.

**Tests (TestClient + `dependency_overrides` + `patch`, mirror `test_calendar_router.py`)**
- Fixtures: `mock_radarr`/`mock_sonarr` = `AsyncMock(spec=...)`; `FakeWatchlistService` exposing `get_all()`;
  override `get_radarr_client`/`get_sonarr_client`/`get_service`. **Call `reset_cache()` in setup & teardown.**
- `test_empty_local_data_returns_empty_and_no_tmdb_calls`: empty watchlist, `get_all_movies`/`get_all_series`
  return `[]`; patch `...router.tmdb_client.get_recommendations` (AsyncMock) ⇒ assert response
  `results == []` **and** `get_recommendations.assert_not_called()`.
- `test_watchlist_seed_returns_recs_excluding_seed`: one watchlist movie (id 5); patched
  `get_recommendations` returns results incl. id 5 and id 9 ⇒ output contains 9, never 5.
- `test_owned_movie_excluded_even_if_recommended`: watchlist movie id 5 seeds; `get_all_movies` owns id 9;
  recs include 9 ⇒ 9 absent from output.
- `test_arr_down_still_returns_watchlist_recs`: `get_all_movies`/`get_all_series` raise; watchlist seed
  present ⇒ still returns recs (best-effort path).
- `test_cache_hit_skips_tmdb_and_refresh_bypasses`: first call invokes `get_recommendations`; second call
  (same seeds) does not (assert call count stable); `?refresh=true` invokes again.

**Verify-at-impl:** confirm a real Sonarr `/series` object exposes a usable `tmdbId`; if not, shows are
seeded from watchlist only (code already skips falsy `tmdbId`, so behavior is correct either way).
- **Verify (run as the task gate):** `cd backend && pytest -q tests/test_recommendations_router.py`

---

## T4 — Frontend "For You" surface (parallel with T1/T2)

**Target files**
- `frontend/src/services/forYou.js` (new)
- `frontend/src/utils/forYouState.js` (new)
- `frontend/src/utils/forYouState.test.js` (new)
- `frontend/src/views/ForYouView.vue` (new)
- `frontend/src/router/index.js` (add route)
- `frontend/src/App.vue` (add nav link)

**Change**
- `forYou.js` (mirror `calendar.js`):
  ```js
  import api from './api'
  export const forYouService = {
    getRecommendations: (refresh = false) => api.get('/for-you', { params: refresh ? { refresh: true } : {} }),
  }
  ```
- `forYouState.js` — the one piece of real branching logic, kept pure for testing:
  ```js
  // Where a recommendation card's "add" action should go: movies add straight to the
  // watchlist; shows must pick seasons, so route to the detail page instead.
  export function addTargetFor(media) {
    if (media.media_type === 'movie') return { kind: 'watchlist' }
    return { kind: 'detail', path: `/tv/${media.tmdb_id}` }
  }
  ```
- `forYouState.test.js` (Vitest): movie ⇒ `{kind:'watchlist'}`; show ⇒ `{kind:'detail', path:'/tv/<id>'}`.
- `ForYouView.vue` (mirror `CalendarView.vue` shell): `onMounted` ⇒ `forYouService.getRecommendations()`,
  store `data.results`. States: loading / error / empty (`"Add movies and shows to your watchlist or
  library to start getting recommendations."`) / `media-grid` of `<MediaCard :media>` keyed
  `` `${tmdb_id}-${media_type}` `` with `@add="handleAdd"`. `handleAdd(media)` uses `addTargetFor`:
  `watchlist` ⇒ `await watchlistService.add(media.tmdb_id, 'movie')` then mark added; `detail` ⇒
  `router.push(target.path)`. Reuse existing `MediaCard`/`watchlistService`; do **not** duplicate the
  season modal.
- `router/index.js`: import `ForYouView`; add `{ path: '/for-you', name: 'for-you', component: ForYouView }`.
- `App.vue`: add `<router-link to="/for-you">For You</router-link>` in the nav (before Coming Soon).

**Verify-at-impl:** none.
- **Verify (run as the task gate):** `cd frontend && npm run test`  *(runs all Vitest incl. `forYouState.test.js`; `npm run build` is exercised at the barrier)*

---

## T5 — Project docs (depends on all; last)

**Target files**
- `CHANGELOG.md` — new `## [2.12.0] - 2026-06-06` "Added" section describing the For You surface
  (TMDB-only, watchlist + owned-library seeds, excludes owned/watchlisted, in-process cache + refresh,
  no DB change / no migration, no scheduler). Note Step 2 (like/not-interested signals) and Step 3
  ("Because you added X") remain future steps.
- `README.md` — add "For You" to the feature list / nav description.
- `CLAUDE.md` — Project Structure: add `recommendations/` backend module, `ForYouView`,
  `forYou.js` service, `forYouState.js` util, and the `/for-you` nav entry. Add a Key Files row for
  `recommendations/service.py`.

**Do NOT** edit `docs/superpowers/specs/2026-06-06-roadmap-design.md` (status flip is Step 9 closure).

- **Verify (run as the task gate):** `cd backend && pytest && cd ../frontend && npm run test && npm run build`  *(final task ⇒ doubles as the full-slice barrier gate; docs have no unit test)*

---

## Barrier (whole-slice gate, after all tasks; ONE commit)

```
cd backend && pytest
cd frontend && npm run test && npm run build
```
All backend + frontend tests green and the production bundle builds. No fixture/snapshot regen in this slice.
