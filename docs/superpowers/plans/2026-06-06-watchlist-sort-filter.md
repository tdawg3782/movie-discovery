<!-- orchestrator-native-plan: v1 -->

## Orchestrator execution contract — READ FIRST (how `/execute-plan` runs this slice)

- **Task ids:** literal labels `T1 T2 T3`, used verbatim in `orchestrator_begin`/`orchestrator_report`.
- **Dependency levels:** strictly sequential — `T1 → T2 → T3`. No parallel level. T2 imports T1's module wholesale (the parse/serialize/apply API is the contract); T3 documents the finished behavior. NEVER `isolated: true`.
- **ONE barrier commit for the whole slice** — no commit per task. All three tasks land together at the barrier.
- **No fixture/snapshot regen** in this slice (no golden files; pure unit tests are hand-written). Nothing to authorize.
- **Per-task `Verify`** is stated on each task as `- **Verify (run as the task gate):** <exact command>`.
- **Slice is frontend-only — deliberate deviation from the python default gate.** No backend file is touched, so `pytest` is not the gate here; the meaningful gates are Vitest (`npm run test`) and the Vite build (`npm run build`, which compiles the `.vue` SFC and resolves imports — the only automated check for `WatchlistView.vue` since the repo has no component-test harness). Backend tests are unaffected and out of scope.
- **Barrier gate (whole slice):** `cd frontend && npm run test && npm run build`.
- **Closure is `/execute-plan` Step 9's job** — marking Feature 2 SHIPPED in the roadmap spec and any state/snapshot is closure, NOT part of T3. T3 covers only project docs (CHANGELOG, CLAUDE.md).

---

# Slice: Watchlist sort & filter (Roadmap Tier 1 — Feature #2)

**Date:** 2026-06-06
**Spec:** `docs/superpowers/specs/2026-06-06-roadmap-design.md` (Tier 1 → #2)
**Scope class:** Small/Medium (planning-scope signal only). Frontend-only; data already enriched by the backend.
**Predecessor:** Feature #1 (paginated Discover) shipped v2.7.0; established the `utils/*State.js` URL-as-state pattern this slice mirrors.

## Goal

Give the watchlist usable controls over the data it already carries: **sort** (date added, title, rating, release date) and **filter** (media type + status). Persist the chosen sort/filter in the URL query so the choice survives a reload and the browser Back button — consistent with Feature #1's Discover state.

## Acceptance (from spec)

- Can sort by **rating descending** and filter to **shows-only**; the choice **survives a reload**.
- Media-type tabs (All / Movies / TV Shows) keep working and become state-driven.
- Status filter (All / Pending / In Library / Downloading) works.
- Items missing a sort key (no rating, no release date) sort **last** in both directions (never silently float to the top).

## Design decisions

- **Where the logic lives:** all filter/sort/state mapping goes in a new pure module `frontend/src/utils/watchlistState.js` (no Vue, no DOM), fully unit-tested with Vitest — exactly mirroring `utils/discoverState.js`. `WatchlistView.vue` becomes thin glue. Rationale: the repo has **no** component-test harness (no jsdom / `@vue/test-utils`), so the only way to unit-test behavior is to keep it in a pure module. (Confirmed: `frontend/package.json` devDeps = vite/vitest/@vitejs-plugin-vue only.)
- **URL vocabulary:** keep the existing tab vocabulary `all` / `movies` / `shows` for media type (matches the current `filter` ref and tab labels); the apply function maps `movies→movie`, `shows→show` against `item.media_type`.
- **Defaults chosen to be no-ops:** `mediaType='all'`, `status='all'`, `sortBy='added'`, `sortDir='desc'`. `serializeWatchlistState` omits defaults so a pristine watchlist URL stays clean (`{}`), and the default order equals the backend's existing `added_at DESC` order — zero visual disruption on first load. (Confirmed: `WatchlistService.get_all()` does `order_by(Watchlist.added_at.desc())`.)
- **History hygiene:** use `router.replace({ query })` (not `push`) when committing watchlist control changes, so toggling sort/filter does not spam the Back stack on a single page. (Discover used `push` because page/tab navigation is meaningful history there; watchlist controls are view preferences.)
- **Nulls-last invariant:** `vote_average` and `release_date` can be `null`/empty (the enrichment fallback path omits them). Comparators push missing keys to the end regardless of direction. Sort is stable for equal keys (preserve incoming order).

## Confirmed facts (pre-flight)

- Enriched item fields (from `backend/src/app/modules/watchlist/router.py::_enrich_watchlist_item` + `backend/src/app/schemas.py::WatchlistItem`): `id`, `tmdb_id`, `media_type` (`movie`|`show`), `title`, `release_date` (`str "YYYY-MM-DD"`|null), `vote_average` (`float`|null), `added_at` (ISO datetime str), `notes`, `status` (`pending`|`added`|`downloading`), `selected_seasons`, `total_seasons`.
- `frontend/src/views/WatchlistView.vue` currently: local `filter` ref (`all`/`movies`/`shows`), `filteredItems`/`movieCount`/`showCount` computeds (lines ~240, 269–285), media-type tabs in template (lines 18–38). No `useRoute`/`useRouter` import today.
- `frontend/src/router/index.js`: watchlist at `path: '/watchlist'`, `name: 'watchlist'`.
- Vitest present and runnable (`frontend/node_modules/vitest`, `npm run test` → `vitest run`).

---

## T1 — Pure `watchlistState.js` module + Vitest tests (TDD)

**Target files:**
- NEW `frontend/src/utils/watchlistState.js`
- NEW `frontend/src/utils/watchlistState.test.js`

**Change (API contract — implement exactly so T2 can consume it):**

```js
// frontend/src/utils/watchlistState.js
// Pure URL <-> Watchlist view state + list transform. No Vue, no DOM.

export function parseWatchlistState(query) {
  // returns canonical state with safe fallbacks for missing/invalid values:
  // {
  //   mediaType: 'all' | 'movies' | 'shows',          // from query.type, default 'all'
  //   status:    'all' | 'pending' | 'added' | 'downloading', // from query.status, default 'all'
  //   sortBy:    'added' | 'title' | 'rating' | 'release',     // from query.sort, default 'added'
  //   sortDir:   'asc' | 'desc',                       // from query.dir,  default 'desc'
  // }
}

export function serializeWatchlistState(state) {
  // inverse of parse; OMITS every key whose value equals the default
  // (so default state -> {}). Keys: type, status, sort, dir.
}

export function applyWatchlistView(items, state) {
  // returns a NEW array (no mutation of input):
  //   1. filter by mediaType ('movies'->'movie', 'shows'->'show'; 'all' keeps everything)
  //   2. filter by status ('all' keeps everything; else item.status === status)
  //   3. sort by sortBy/sortDir:
  //        - 'added'   -> compare added_at as Date (newest first when desc)
  //        - 'title'   -> case-insensitive localeCompare (A->Z when asc)
  //        - 'rating'  -> numeric vote_average (highest first when desc)
  //        - 'release' -> release_date string compare (newest first when desc)
  //   nulls/empties for the active sort key always sort LAST (both directions).
  //   sort is stable for equal keys (preserve input order).
}
```

**Tests (`watchlistState.test.js`) — mirror the structure of `discoverState.test.js`:**
- `parseWatchlistState({})` → full default state object.
- `parseWatchlistState` coerces a populated query (`{type:'shows',status:'pending',sort:'rating',dir:'asc'}`) and falls back to defaults on garbage values (`{type:'x',sort:'nope',dir:'sideways'}` → all defaults).
- `serializeWatchlistState(parse({}))` → `{}` (all defaults omitted).
- `serializeWatchlistState` emits only non-default keys as strings; round-trip `serialize(parse(q)) === q` for a fully-populated query.
- `applyWatchlistView`:
  - media-type filter keeps only `movie`/`show` for `movies`/`shows`; `all` keeps both.
  - status filter keeps only matching `status`; `all` keeps all.
  - sort by `rating` desc orders highest `vote_average` first; an item with `vote_average: null` lands last.
  - sort by `release` desc orders newest `release_date` first; an item with `release_date: ''`/null lands last.
  - sort by `title` asc is case-insensitive A→Z.
  - sort by `added` desc is newest `added_at` first.
  - input array is not mutated (assert original order/reference preserved).
  - stability: two items with equal sort keys keep their input order.

**Verify-at-impl:** none — all inputs are fixtures defined in the test; field names confirmed in pre-flight.

- **Verify (run as the task gate):** `cd frontend && npx vitest run src/utils/watchlistState.test.js`

---

## T2 — Wire sort/filter controls into `WatchlistView.vue`

**Target files:**
- `frontend/src/views/WatchlistView.vue` (template controls + `<script setup>` state)

**Depends on:** T1 (imports `parseWatchlistState`, `serializeWatchlistState`, `applyWatchlistView` from `@/utils/watchlistState`).

**Change (script):**
- Import `useRoute`, `useRouter` from `vue-router` and the three functions from `@/utils/watchlistState`.
- `const route = useRoute(); const router = useRouter(); const initial = parseWatchlistState(route.query)`.
- Replace the local `filter` ref with reactive controls seeded from `initial`: `mediaType` (replaces `filter`), `status`, `sortBy`, `sortDir`.
- Add `commitState()` that calls `router.replace({ query: serializeWatchlistState({ mediaType, status, sortBy, sortDir }) })`; call it whenever a control changes (use `watch` on the four refs, or call in each control handler — match whichever is cleaner; `watch` preferred to mirror reactivity).
- Replace the `filteredItems` computed body with `computed(() => applyWatchlistView(items.value, { mediaType: mediaType.value, status: status.value, sortBy: sortBy.value, sortDir: sortDir.value }))`.
- Keep `movieCount` / `showCount` computeds unchanged (still counts over `items.value`).
- Selection logic (`selectedItems`, `allSelected`, `toggleSelectAll`) already keys off `filteredItems` — leave intact; it transparently follows the new filtered+sorted set.

**Change (template):**
- Convert the three media-type tab buttons (lines 18–38) to set `mediaType` instead of `filter` (`'all'|'movies'|'shows'`), keeping the count labels.
- Add a controls row beside/under the tabs:
  - **Status** select: All / Pending / In Library (`added`) / Downloading (`downloading`).
  - **Sort by** select: Date added (`added`) / Title (`title`) / Rating (`rating`) / Release date (`release`).
  - **Direction** toggle button (asc/desc), e.g. `▲`/`▼`, bound to `sortDir`.
- Reuse existing `.filter-tabs` styling idiom; add minimal scoped styles for the new selects/toggle consistent with the view's existing control look (do not restyle the page).

**Verify-at-impl:**
- Confirm the current `filter` ref has no other references beyond the tabs/computeds before renaming (grep `filter` within the SFC). Rename all hits to `mediaType`.
- Confirm `status` values used by the select match the backend's literal status strings (`pending`/`added`/`downloading`) — already confirmed in pre-flight, but re-check `formatStatus` labels for display text reuse.

- **Verify (run as the task gate):** `cd frontend && npm run build && npm run test`
  - `build` compiles the SFC and resolves the `@/utils/watchlistState` import (the only automated check for the `.vue` change); `test` confirms T1's module still passes.

---

## T3 — Docs (CHANGELOG + CLAUDE.md)

**Target files:**
- `CHANGELOG.md`
- `CLAUDE.md`

**Depends on:** T2 (documents finished behavior).

**Change:**
- `CHANGELOG.md`: add a new top entry `## [2.8.0] - 2026-06-06` with an `### Added` bullet group describing watchlist sort (date added / title / rating / release date) + filter (media type + status), URL-persisted via a new pure, unit-tested `watchlistState` module (`parseWatchlistState` / `serializeWatchlistState` / `applyWatchlistView`). Match the wording style of the v2.7.0 entry.
- `CLAUDE.md`: extend the `frontend/src/` → `utils/` line (currently `discoverState.js (URL-as-state for Discover; unit-tested)`) to also list `watchlistState.js (URL-as-state + sort/filter for Watchlist; unit-tested)`.

**Non-goals for T3:** do NOT edit the roadmap spec (`…/specs/2026-06-06-roadmap-design.md`) to mark Feature 2 SHIPPED, and do NOT touch any state/snapshot doc — that is `/execute-plan` Step 9 closure.

- **Verify (run as the task gate):** `cd frontend && npm run test` (trivial sanity; docs-only change does not affect tests).

---

## Barrier (after T1–T3 all report done)

- **Gate:** `cd frontend && npm run test && npm run build`
- Backend is untouched this slice; no `pytest` run required.
- One commit for the whole slice.
