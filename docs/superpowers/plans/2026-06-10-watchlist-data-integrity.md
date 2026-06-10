<!-- orchestrator-native-plan: v1 -->

## Orchestrator execution contract — READ FIRST (how `/execute-plan` runs this slice)

- **Task ids:** literal labels `T1 T2 T3 T4 T5`, used verbatim in `orchestrator_begin`/`orchestrator_report`.
- **Dependency levels:** sequential `T1 → T2 → T3 → T4 → T5`. T1 (`database.py` + its test) and T5 (frontend) are file-disjoint from the `watchlist/service.py` chain, but T2/T3/T4 all edit `watchlist/service.py` (and share `test_watchlist_batch.py`), and T5 consumes T2's delete contract — so run sequentially. NEVER `isolated: true`.
- **ONE barrier commit for the whole slice** — no commit per task. All edits land together at the barrier.
- **Plan-mandated test changes are AUTHORIZED** (label: *contract change*): T1 rewrites `_create_legacy_table` in `test_watchlist_migration.py`; T2 changes the `DELETE /api/watchlist/batch` request shape and updates `test_batch_delete`/`test_batch_delete_partial`. These are intended, not regressions.
- **Per-task `Verify` command** is stated on each task (scoped `cd backend && pytest -q tests/<file>`); the barrier runs the full gate `cd backend && pytest`.
- **Closure is `/execute-plan` Step 9's job** — no task here writes the closure snapshot/roadmap. A CHANGELOG line is the only doc touched (folded into T1's scope note below; not a separate task).
- **Recommended thinking:** `medium` — the main-thread driver sets this with Shift+Tab before `/omp-go`.

---

# Slice: Watchlist data integrity

Eliminates the **watchlist persistence/correctness cluster** from `docs/audits/2026-06-10-audit-3.md`: H2, H3, H4, M3, L1, L3, plus the test-coverage gaps that guard them (M10, TG5, TG7). One coherent theme — everything lives in `backend/src/app/modules/watchlist/`, `database.py`, `backend/src/app/modules/sonarr/client.py`, and one Vue view — so it groups cleanly and is fully TDD-able against the existing `test_watchlist_*` suite.

**Honors the engineering contract (`CLAUDE.md`):** additive, guarded, idempotent migrations only (T1 follows the existing `priority`/`tags` pattern verbatim); type hints + `HTTPException` + Pydantic on all backend code; "show" stays the internal media-type token ("tv" only at the TMDB boundary, untouched here).

### Out of scope (deferred to later slices — do NOT touch here)
- **H1** (settings env/DB split-brain) — touches every router's client construction; its own slice.
- **C1 / M11** (auth gate, SSRF/URL validation) — needs deployment decisions; separate security slice.
- **H5/H6/M2** (arr-resilience: `return_exceptions`, `ConnectError`, calendar `None` S/E) — error-handling slice.
- **H7/H8/M7/M8/M9** (For-You cache, watchlist N+1/MediaCache, client lifecycle) — perf/resilience slice.
- **H9/M6** (encryption-key lifecycle, `get_setting` leak) — config slice.
- **H10/M4/M5** (frontend fetch races / back-button) — frontend-race slice.
- **L2/L4/L5/L6/L7/L8/L9** (search totals, unique constraint, nginx headers, CORS, dead code, genre cache, similar 4xx) — cleanup slice. **Note:** L4 (DB `UNIQUE(tmdb_id, media_type)`) is intentionally deferred — it requires a dedup-before-index migration step and is rated Low/unreachable on the single-worker deploy; keeping T1 to pure additive-column ALTERs is the lowest-risk migration change.

---

## T1 — Migration column guards + hardened migration test (H3, M10)

**Target files:**
- `backend/src/app/database.py` — `_migrate_watchlist_columns()` (lines ~30-44).
- `backend/tests/test_watchlist_migration.py` — `_create_legacy_table` + assertions (*contract change*).

**Change:**
- In `_migrate_watchlist_columns()`, add two guarded ALTERs **before** the existing `priority`/`tags` ones, matching the exact existing idempotent pattern (`if "<col>" not in existing: stmts.append(...)`):
  - `ALTER TABLE watchlist ADD COLUMN selected_seasons TEXT`
  - `ALTER TABLE watchlist ADD COLUMN is_season_update BOOLEAN NOT NULL DEFAULT 0`
- Keep the existing `priority`/`tags` guards and the `if stmts: with bind.begin()` apply block unchanged. Do not switch to generic model-derivation (explicit ALTERs are the proven, lowest-risk form — `CHANGELOG.md:159-162` is the v2.4.1 precedent).
- Add a one-line CHANGELOG entry under a `Fixed` heading noting the migration now backfills `selected_seasons`/`is_season_update` on legacy/restored DBs.

**Tests (TDD — write first, watch them fail on current `database.py`):**
- Rewrite `_create_legacy_table` to the **true original** schema only: `id, tmdb_id, media_type, added_at, notes, status` (remove `selected_seasons` AND `is_season_update`, which it currently pre-seeds — that is the M10 masking bug).
- Strengthen `test_migration_adds_columns_to_legacy_table`: after `_migrate_watchlist_columns(engine)`, assert **every** column name in `Base.metadata.tables["watchlist"].columns` is present in the migrated table (future-proof, generic), and specifically that `selected_seasons`, `is_season_update`, `priority`, `tags` exist; the inserted legacy row still reads back with the new columns defaulted (`is_season_update == 0/False`, `selected_seasons is None`).
- Keep `test_migration_is_idempotent` (second run must not raise; each new column appears exactly once) and `test_fresh_create_all_has_new_columns`.

- **Verify (run as the task gate):** `cd backend && pytest -q tests/test_watchlist_migration.py`
- **Verify-at-impl:** confirm `selected_seasons`/`is_season_update` are genuinely absent from the rewritten legacy `CREATE TABLE` (otherwise the test still can't fail red first).

---

## T2 — media_type-scoped watchlist keying (H2 backend, TG7)

**Target files:**
- `backend/src/app/modules/watchlist/service.py` — `get_by_tmdb_id` (:57-59), `update_seasons` (:61-70), `delete_batch` (:97-105), `process_batch` (:133, :152).
- `backend/src/app/modules/watchlist/schemas.py` — `BatchDeleteRequest` (:20-23) (*contract change*).
- `backend/src/app/modules/watchlist/router.py` — delete route (:140-146), seasons PATCH route (:149-160).
- `backend/tests/test_watchlist_batch.py` — update `test_batch_delete`/`test_batch_delete_partial` to the new request shape; add a cross-media-type independence test.

**Change (clean cutover — TMDB movie & TV ids are separate namespaces; `add()` already dedupes on `(tmdb_id, media_type)`, so movie N and show N legitimately coexist):**
- `get_by_tmdb_id(self, tmdb_id: int, media_type: str)` → filter on **both** `tmdb_id` AND `media_type`.
- `update_seasons(self, tmdb_id: int, media_type: str, selected_seasons: list[int] | None)` → pass `media_type` into `get_by_tmdb_id`.
- `process_batch` → pass the method's `media_type` arg into both `get_by_tmdb_id(...)` calls (:133 read, :152 status="added" write).
- `delete_batch(self, items: list[tuple[int, str]])` → filter with `sqlalchemy.tuple_(Watchlist.tmdb_id, Watchlist.media_type).in_(items)` (import `tuple_` from `sqlalchemy`). Returns count deleted.
- `schemas.py`: replace `BatchDeleteRequest.ids: list[int]` with a `BatchDeleteItem(BaseModel)` (`tmdb_id: int`, `media_type: Literal["movie", "show"]`) and `BatchDeleteRequest.items: list[BatchDeleteItem]`.
- Router delete route: build `[(i.tmdb_id, i.media_type) for i in request.items]` and pass to `delete_batch`; keep `{"deleted": count}`.
- Router seasons PATCH: seasons are TV-only → call `service.update_seasons(tmdb_id, "show", data.selected_seasons)` (URL/body unchanged → no frontend change for seasons).

**Tests (TDD):**
- Update the two existing batch-delete tests to POST a movie + a show then `DELETE /api/watchlist/batch` with `{"items": [{"tmdb_id": ..., "media_type": "movie"}, ...]}`.
- **New (TG7):** insert a movie and a show that **share a `tmdb_id`** (e.g. both 603); `DELETE /api/watchlist/batch` with only the movie pair → assert the show row survives (`total == 1`, remaining row is the show). Add a sibling service-level test that `update_seasons(603, "show", [2])` updates only the show row and leaves the movie row's `selected_seasons` untouched.

- **Verify (run as the task gate):** `cd backend && pytest -q tests/test_watchlist_batch.py tests/test_watchlist_service.py`
- **Verify-at-impl:** run `lsp references` on `get_by_tmdb_id` and `delete_batch` before editing to catch every caller (expected: `update_seasons`, `process_batch` ×2 for the former; router delete route for the latter) so no callsite is missed.

---

## T3 — `add()` merge-on-re-add + 200-for-duplicate + list-guarded season parse (H4, L3, L1)

**Target files:**
- `backend/src/app/modules/watchlist/service.py` — `add()` (:18-47).
- `backend/src/app/modules/watchlist/router.py` — POST `add_to_watchlist` (:113-127), `_parse_seasons` (:33-40).
- `backend/tests/test_watchlist_service.py` and/or `backend/tests/test_watchlist_router.py` — new cases.

**Change:**
- **H4:** in `add()`, when the `(tmdb_id, media_type)` row already exists AND the request carries season intent (`selected_seasons is not None` OR `is_season_update`), update the existing row instead of returning it untouched: set `is_season_update` from the request, **union** the incoming `selected_seasons` into the stored list (`None` incoming = "all seasons" → store `None`), and reset `status="pending"`; commit + refresh. When no season intent is supplied, leave the existing row unchanged.
- **L3 + created-signal:** make `add()` return `(item, created: bool)` (`created=False` for the existing/merged path). Update the POST handler to accept `response: Response` (FastAPI) and set `response.status_code = 200` when `created is False`, else keep 201 (the decorator's default). Update any other `add()` caller to unpack the tuple.
- **L1:** in `_parse_seasons`, guard the decoded value like `_parse_tags` already does — `result = json.loads(raw); return result if isinstance(result, list) else None`. Apply the same `isinstance(..., list)` guard to the `json.loads(item.selected_seasons)` in `process_batch` (`service.py:136`) so a non-list stored value can't reach `season_num in <int>`.

**Tests (TDD):**
- Re-adding an existing show with new `selected_seasons` (`is_season_update=True`) updates the row (seasons unioned, `is_season_update True`, `status` back to `"pending"`) and the POST returns **200** (not 201).
- A first-time add returns **201** and persists the row.
- `_parse_seasons('"5"')` / `_parse_seasons('5')` → `None` (not the int `5`); a valid `'[1,2]'` → `[1, 2]`.

- **Verify (run as the task gate):** `cd backend && pytest -q tests/test_watchlist_service.py tests/test_watchlist_router.py`
- **Verify-at-impl:** `lsp references` on `WatchlistService.add` to update every caller for the new `(item, created)` return (router POST is the known one; check tests).

---

## T4 — "all seasons" None-safety in season update (M3, TG5)

**Target files:**
- `backend/src/app/modules/sonarr/client.py` — `update_season_monitoring` (:176-197).
- `backend/src/app/modules/watchlist/service.py` — `process_one` (:128-145) only if a guard is cleaner there.
- `backend/tests/test_watchlist_batch.py` (season-update service tests, ~:228-255) and/or `backend/tests/test_watchlist_season_update.py`.

**Change:**
- Widen `update_season_monitoring(self, tmdb_id: int, seasons_to_add: list[int] | None)`. When `seasons_to_add is None` (the documented "all seasons" case, reachable when a season-update row has NULL `selected_seasons`), monitor **all non-special** seasons — set `season["monitored"] = True` for every season with `seasonNumber != 0` (skip specials) — instead of evaluating `season.get("seasonNumber") in None`, which raises `TypeError: argument of type 'NoneType' is not iterable` and surfaces as a cryptic per-item batch failure. Otherwise behavior is unchanged (`in seasons_to_add`).

**Tests (TDD):**
- **TG5:** a `process_batch([id], "show")` over a row with `is_season_update=True` and `selected_seasons=None` (mock the Sonarr client like the existing `test_batch_process_season_update`) → `update_season_monitoring` is called with `None` and does **not** raise; the item lands in `processed`, not `failed`. A unit test on `update_season_monitoring(id, None)` against a stub series with seasons `[{seasonNumber:0},{seasonNumber:1},{seasonNumber:2}]` asserts seasons 1 and 2 become `monitored=True` and season 0 stays unmonitored.
- Keep the existing `[4, 5]` season-update test green.

- **Verify (run as the task gate):** `cd backend && pytest -q tests/test_watchlist_batch.py tests/test_watchlist_season_update.py`
- **Verify-at-impl:** check how `lookup_series`/`get_series_by_tvdb_id` are mocked in the existing season-update test so the new None test follows the same stubbing shape.

---

## T5 — Frontend watchlist selection keying + batch-delete payload (H2 frontend)

**Target files:**
- `frontend/src/views/WatchlistView.vue` — `isSelected` (:431-433), `toggleSelect` (:435-442), `toggleSelectAll` (:444-458), `allSelected` (:414-417), `confirmBatchDelete` (:505-517).
- `frontend/src/services/watchlist.js` — `deleteItems` (:50-51).

**Change (must match T2's `{items: [{tmdb_id, media_type}]}` delete contract):**
- Key selection by the `(media_type, tmdb_id)` pair, not bare `tmdb_id`. Introduce a helper key `` `${item.media_type}:${item.tmdb_id}` `` and use it in `isSelected(item)`, `toggleSelect` (findIndex compares both fields), `toggleSelectAll` (the Set membership keys), and `allSelected` (`every(i => isSelected(i))`). `selectedItems` already stores `{ tmdb_id, media_type }`, so the underlying store shape is unchanged.
- `confirmBatchDelete`: send the full pairs — `watchlistService.deleteItems(selectedItems.value.map(s => ({ tmdb_id: s.tmdb_id, media_type: s.media_type })))`.
- `watchlist.js`: `deleteItems(items) => api.delete('/watchlist/batch', { data: { items } })` (update the JSDoc to `items: Array<{tmdb_id, media_type}>`).
- `isSelected` is referenced in the template by `tmdb_id` — update those call sites to pass the item (verify template usages).

**Tests:** no view-level test harness exists (Vitest covers only `utils/*`); this is a mechanical edit validated by T2's backend cross-type delete test + a compile check. (Do **not** scaffold a new Vitest/view-test framework in this slice.)

- **Verify (run as the task gate):** `cd frontend && npm run build`
- **Verify-at-impl:** `search` for all `isSelected(` / `deleteItems(` / `toggleSelect` usages (template + script, plus any other component) so every call site matches the new signatures; if `npm run build` fails on missing deps, run `npm install` (or `npm ci`) first.

---

## Barrier (whole-slice gate, run once after T5)

- **Backend full gate:** `cd backend && pytest`  *(matches `CLAUDE.md` "run tests before committing backend changes")*
- **Frontend:** `cd frontend && npm run build` (compile) and `cd frontend && npm run test` (utils suite stays green).
- Then ONE commit for the slice.
