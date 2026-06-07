<!-- orchestrator-native-plan: v1 -->

## Orchestrator execution contract — READ FIRST (how `/execute-plan` runs this slice)

- **Task ids:** literal labels `T1 T2 … TN`, used verbatim in `orchestrator_begin`/`orchestrator_report`.
- **Dependency levels** stated explicitly; sequential unless tasks are file-disjoint (then a parallel level is allowed). NEVER `isolated: true` for disjoint tasks.
- **ONE barrier commit for the whole slice** — no commit per task. Regression fixtures/snapshots regenerate into the working tree per task; everything lands at the barrier.
- **Plan-mandated fixture/snapshot regen is AUTHORIZED** (label it) so the reviewer permits it.
- **Per-task `Verify` command** stated explicitly (use `cd backend && pytest -q` scoped to the task; the barrier uses `cd backend && pytest`).
- **Closure is `/execute-plan` Step 9's job** — a docs task covers only project-specific docs, never the closure snapshot/roadmap.

### Slice-specific execution notes (overrides for this frontend-only slice)

- **This slice changes only `frontend/`. The backend is untouched**, so the per-task gate is a **frontend** command, not `pytest`. Backend `pytest` is still run once at the barrier to prove nothing regressed.
- **New test harness is plan-mandated and AUTHORIZED:** T1 adds Vitest (`vitest` devDependency + a `test` script) and a pure logic module with unit tests. This is the only way to give the slice real TDD verification — there is currently no frontend test runner.
- **Per-task Verify uses `cd frontend && npm run test` / `npm run build`.** First run needs `npm install` to fetch Vitest (done in T1).
- **Barrier gate:** `cd frontend && npm run test && npm run build` **and** `cd backend && pytest` (backend must stay green though untouched).
- **No fixture/snapshot regen** in this slice (no golden files).

---

# Slice: Paginated Discover with restored position (URL-as-state)

**Roadmap item:** Tier 1 #1 — "Paginated browsing with restored position" (`docs/superpowers/specs/2026-06-06-roadmap-design.md`).
**Planning scope:** Medium (frontend refactor of one view + one component, one new pure module + test harness, one new presentational component, 3 tasks, all sequential).
**Language/stack:** Frontend only — Vue 3 (`<script setup>`), Vue Router 4, Vite.

## Problem

The Discover feed appends pages into component state (`items = append ? [...items, ...newResults] : newResults`) via a "Load More" button (`loadNextPage`). All view state (`activeTab`, `currentPage`, `searchQuery`, `filters`) lives only in component refs, so any reload or back-navigation from a detail page resets to page 1 / trending / movies. Users lose their place — the #1 reported annoyance.

## Outcome

- Numbered page navigation (Prev / "Page X of Y" / Next) replaces "Load More"; each page **replaces** results instead of appending.
- `activeTab`, `currentPage`, `searchQuery`, and active `filters` are mirrored into the URL query string. A reload or a back-button from a detail page restores the exact tab, page, search, and filters (results AND the FilterPanel's visible chips/controls).
- The fiddly serialization/clamping logic is a pure, unit-tested module.

## Non-goals (this slice)

- Server-side library filtering (the `inLibrary`/`notInLibrary` per-page unevenness stays; backlog item).
- Pixel-level scroll restoration (logical page position only; router `scrollBehavior` is an optional impl nicety, not required).
- Any backend change (TMDB already returns `total_pages`; trending/search/discover endpoints already pass it through).

## Affected files (verified to exist unless marked NEW)

- `frontend/src/views/DiscoverView.vue` — append logic at lines ~246-248, `loadNextPage` ~261-269, "Load More" template ~59-61, `onMounted`/`watch(activeTab)` ~325-331, `handleFilterChange` ~207-221.
- `frontend/src/components/FilterPanel.vue` — owns `selectedGenres` + `filters` reactive; emits `filter-change` (payload shape at lines ~260-271); `onMounted` loads genres ~151-153.
- `frontend/src/services/discover.js` — `getTrendingMovies/Shows(page)`, `search(query, page)`, `discoverMovies/Shows(options)` already thread `page`; **no change expected** (Verify-at-impl).
- `frontend/src/router/index.js` — `createWebHistory`, `/` → `DiscoverView`; **no change expected**.
- `frontend/src/utils/discoverState.js` — **NEW** pure module.
- `frontend/src/utils/discoverState.test.js` — **NEW** Vitest unit tests.
- `frontend/src/components/PaginationControls.vue` — **NEW** presentational Prev/Next/indicator component (reusable for the later Watchlist slice).
- `frontend/package.json` — add `vitest` devDep + `"test": "vitest run"` script.
- `README.md`, `CHANGELOG.md` — docs (T3).

---

## T1 — Pure URL-state module + Vitest harness (TDD, foundational)

**Depends on:** nothing (dependency level 0).

**Target files:**
- `frontend/package.json` — add `"vitest": "^2.0.0"` (or current 1.x/2.x) to `devDependencies`; add `"test": "vitest run"` to `scripts`.
- `frontend/src/utils/discoverState.js` — NEW.
- `frontend/src/utils/discoverState.test.js` — NEW.

**Change (APIs/patterns):** Implement three pure functions, no DOM/Vue imports (runs in Vitest's default `node` env):

- `parseDiscoverState(query)` — `query` is a Vue Router `route.query` plain object (string values). Returns the canonical view state:
  ```
  { tab: 'movies'|'shows', page: number>=1, search: string,
    filters: { genre, yearGte, yearLte, ratingGte, certification, sortBy, inLibrary, notInLibrary } }
  ```
  Coercion: `page` → int, default `1`; `tab` → `'movies'`/`'shows'`, default `'movies'`; `search` → string, default `''`; numeric filters (`yearGte`,`yearLte`,`ratingGte`) → number or `null`; booleans (`inLibrary`,`notInLibrary`) → `true` only when string `'true'`; `sortBy` default `'popularity.desc'`; `genre`/`certification` → string or `null`. (Genre stays a comma string, matching `DiscoverView`'s existing `filters.genre` contract.)
- `serializeDiscoverState(state)` — inverse; returns a plain query object for `router.push({ query })`. **Omits defaults/empties** so clean state yields `{}` (no `page=1`, no `tab=movies`, no `sortBy=popularity.desc`, no `false` booleans, no `null`/empty filters).
- `clampPage(page, totalPages)` — returns `Math.min(Math.max(page, 1), Math.max(totalPages, 1))`.

**Tests (write FIRST, red → green):** in `discoverState.test.js`:
- `parseDiscoverState({})` → full default state.
- `parseDiscoverState({ page: '5', tab: 'shows', q: 'matrix' OR search:'matrix', genre:'28,12', ratingGte:'8', inLibrary:'true' })` coerces types correctly (decide the search query key — see Verify-at-impl).
- `serializeDiscoverState(defaultState)` → `{}`.
- `serializeDiscoverState` of a populated state includes only the non-default keys.
- Round-trip: `serializeDiscoverState(parseDiscoverState(q))` is stable for a populated `q`.
- `clampPage(0,10)===1`, `clampPage(99,10)===10`, `clampPage(3,10)===3`, `clampPage(1,0)===1`.

**Verify-at-impl:**
- Pick ONE query key for search and use it consistently across T1/T2 (recommend `q` to match the API param, but it's purely the URL key). Document it in the module.
- Confirm `npm install` can fetch `vitest` (registry access); if a specific major is unavailable, pin to the installed one. No `jsdom` needed (pure functions).
- Confirm no existing `frontend/src/utils/` name clash.

- **Verify (run as the task gate):** `cd frontend && npm install && npm run test`

---

## T2 — Wire pagination + URL-state into DiscoverView & FilterPanel

**Depends on:** T1 (imports `discoverState.js`) — dependency level 1.

**Target files:**
- `frontend/src/views/DiscoverView.vue`
- `frontend/src/components/FilterPanel.vue`
- `frontend/src/components/PaginationControls.vue` — NEW.

**Change (APIs/patterns):**

1. **`PaginationControls.vue` (NEW):** props `currentPage:Number`, `totalPages:Number`; renders `Prev` (disabled when `currentPage<=1`), `Page {{currentPage}} of {{totalPages}}`, `Next` (disabled when `currentPage>=totalPages`); emits `change` with the target page. Hidden when `totalPages<=1`.

2. **`DiscoverView.vue`:**
   - Import `useRoute`, `useRouter` from `vue-router`; import `parseDiscoverState`, `serializeDiscoverState`, `clampPage` from `@/utils/discoverState`; import `PaginationControls`.
   - **Drop the append path:** `fetchContent`/`performSearch` always replace (`items.value = newResults`); remove `append` params and `loadNextPage`.
   - **`goToPage(page)`:** `page = clampPage(page, totalPages.value)`; set `currentPage`; commit state to URL; fetch (search vs content) for that page.
   - **`commitState()`:** build query via `serializeDiscoverState({ tab: activeTab, page: currentPage, search: searchQuery, filters })` and `router.push({ query })`. Call after page change, tab change, search submit, clear, and `handleFilterChange`.
   - **`onMounted`:** `const s = parseDiscoverState(route.query)` → seed `activeTab`, `currentPage`, `searchQuery`, `filters`, derive `isSearching` (search non-empty) and `isFiltering` (any active filter); then fetch the restored page (search vs content) **without append**. This replaces the bare `fetchTrending()` mount.
   - **Template:** replace the `load-more` block (lines ~59-61) with `<PaginationControls :current-page="currentPage" :total-pages="totalPages" @change="goToPage" />`.
   - **Tab switch:** keep "switch resets to page 1" but route through `commitState()` so the URL updates (and respect `isFiltering` consistently with existing behavior).

3. **`FilterPanel.vue` hydration:** add prop `initialFilters` (object) and `initialGenres` (Array of genre id numbers). In `onMounted`, before/after `loadGenres()`, seed the local `filters` reactive from `initialFilters` and `selectedGenres` from `initialGenres`. `DiscoverView` passes `:initial-filters="filters"` and `:initial-genres="filters.genre ? filters.genre.split(',').map(Number) : []"`. This makes the panel's chips/controls reflect restored filters, not just the results.

**Tests:** Component-level behavior is covered indirectly — all branch-prone logic (serialize/parse/clamp) lives in the T1 module and is unit-tested there. T2's gate is a successful production build (compiles + bundles) plus the T1 suite staying green. (No component test runner / jsdom is being introduced in this slice.)

**Verify-at-impl:**
- `router.push` on each page change adds history entries (back steps page-by-page) — confirm that's acceptable; switch to `router.replace` for intra-page nav if back-button-per-page feels wrong. Back-from-detail restoration works either way.
- Guard against a query-write → re-fetch loop: commit state explicitly in handlers; do NOT add a broad `watch(() => route.query)` that re-triggers fetch.
- Confirm `discover.js` needs no change (it already threads `page`); if `search` needs the page on restore, reuse `performSearch(page)`.
- Optional: add router `scrollBehavior` for pixel scroll restore — nice-to-have, not required for acceptance.

- **Verify (run as the task gate):** `cd frontend && npm run test && npm run build`

---

## T3 — Docs: pagination usage + changelog

**Depends on:** T2 (documents shipped behavior) — dependency level 2.

**Target files:**
- `README.md` — in "Discovering Content", note page navigation and that tab/page/search/filters are preserved in the URL (reload/back returns to the same place).
- `CHANGELOG.md` — add a new top entry (next version, e.g. `2.7.0`) under `### Added`/`### Changed`: paginated Discover with URL-restored position; replaces Load-More; adds Vitest + a unit-tested URL-state module.

**Change:** Documentation only. Keep entries terse, factual, matching existing CHANGELOG style.

**Verify-at-impl:** None beyond style consistency.

- **Verify (run as the task gate):** `cd frontend && npm run build`

---

## Execution summary

- **Order / levels:** T1 (level 0) → T2 (level 1) → T3 (level 2). All sequential; no parallel level (T2 imports T1; T3 documents T2). No `isolated`.
- **Barrier (whole-slice gate before the single commit):** `cd frontend && npm run test && npm run build` **and** `cd backend && pytest`.
- **One commit** at the barrier covering all of T1–T3.

## Acceptance (slice-level)

- Reloading while on page 5 of "Action movies" returns to page 5 of Action movies (results + filter chips).
- Back from a detail page restores tab, page, search, and filters.
- "Load More" is gone; Prev/Next/"Page X of Y" works and clamps at bounds.
- `cd frontend && npm run test` passes (URL-state module); `npm run build` succeeds; `cd backend && pytest` stays green.
