<!-- orchestrator-native-plan: v1 -->

## Orchestrator execution contract — READ FIRST (how `/execute-plan` runs this slice)

- **Task ids:** literal labels `T1 T2 T3 T4`, used verbatim in `orchestrator_begin`/`orchestrator_report`.
- **Dependency levels** stated explicitly; sequential unless tasks are file-disjoint (then a parallel level is allowed). NEVER `isolated: true` for disjoint tasks.
- **ONE barrier commit for the whole slice** — no commit per task. Regression fixtures/snapshots regenerate into the working tree per task; everything lands at the barrier.
- **Plan-mandated fixture/snapshot regen is AUTHORIZED** (label it) so the reviewer permits it. _(This slice has no fixture/snapshot regen — pure new behavior with unit tests.)_
- **Per-task `Verify` command** stated explicitly (use `cd backend && pytest -q` scoped to the task; the barrier uses `cd backend && pytest`).
- **Closure is `/execute-plan` Step 9's job** — a docs task covers only project-specific docs, never the closure snapshot/roadmap.

---

# Slice: Configurable default quality profile (Radarr + Sonarr)

**Scope class:** medium (planning-scope signal only) — 3 backend tasks (full TDD) + 1 frontend wiring task.

## Problem

`RadarrClient.add_movie` and `SonarrClient.add_series` both default `quality_profile_id` to **the first profile returned by the `*arr` API** when none is supplied (`backend/src/app/modules/radarr/client.py:43-47`, `sonarr/client.py:47-51`). The watchlist batch flow `WatchlistService.process_batch` (`watchlist/service.py:99-119`) passes `root_folder_path` from settings but **never passes a quality profile**, so every batch-added movie/show silently lands on whatever profile happens to be first (often "Any"/"SD" instead of "HD-1080p"). Root folder is already user-configurable in Settings; quality profile is the missing twin.

## Solution

Mirror the established `radarr_root_folder` / `sonarr_root_folder` settings pattern exactly:

1. Add `radarr_quality_profile_id` / `sonarr_quality_profile_id` to the settings schemas + service (stored as plain strings, clearable).
2. Add `GET /api/radarr/quality-profiles` and `GET /api/sonarr/quality-profiles` so the UI can populate dropdowns (clients already expose `get_quality_profiles()`).
3. Wire the saved profile id through `process_batch` into `add_movie` / `add_series`.
4. Add quality-profile `<select>` dropdowns to `SettingsView.vue`.

**Why it's clean:** clients already accept `quality_profile_id`; `AddMediaRequest` already carries it; `get_setting()` (`config.py:40`) reads DB-first so saved values flow into `process_batch`; the `*_root_folder` feature is a precise structural precedent for every backend touch point.

## Non-goals (YAGNI)

- Per-item quality profile override in the watchlist UI (settings-level default only).
- Quality profile for the direct `POST /api/radarr/add` / `/api/sonarr/add` endpoints beyond what `AddMediaRequest.quality_profile_id` already supports.
- Caching the profile list.

---

## Dependency levels

- **Level 1 (parallel — file-disjoint):** `T1` (settings module), `T2` (radarr+sonarr routers), `T3` (watchlist service). No shared files; each owns distinct source + test files. `isolated: false`.
- **Level 2:** `T4` (frontend) — logically depends on `T1` (response fields) + `T2` (profile-list endpoints). File-disjoint from backend but sequenced after Level 1 because it consumes their API surface.

---

## T1 — Settings support for default quality profile

**Target files**
- `backend/src/app/modules/settings/schemas.py` — `SettingsUpdate`, `SettingsResponse`
- `backend/src/app/modules/settings/service.py` — `get_settings()`, `CLEARABLE_KEYS`
- Tests: `backend/tests/test_settings_schemas.py`, `backend/tests/test_settings_service.py`

**Change (mirror `*_root_folder` exactly)**
- `SettingsUpdate`: add `radarr_quality_profile_id: Optional[str] = None`, `sonarr_quality_profile_id: Optional[str] = None`. Stored as strings (the int id serialized) — consistent with all other settings being `Text` columns; `process_batch` casts to int in T3.
- `SettingsResponse`: add `radarr_quality_profile_id: Optional[str] = None`, `sonarr_quality_profile_id: Optional[str] = None`.
- `get_settings()`: map both via `self._get_plain(settings, "...")` (non-sensitive → plain, NOT masked).
- `SettingsService.CLEARABLE_KEYS`: add both keys so a blank dropdown clears the setting (reverts to auto-first-profile), same as root folders.

**Tests (TDD — write first, watch fail)**
- `test_settings_service.py`: extend an update-and-get test asserting `update_settings(SettingsUpdate(radarr_quality_profile_id="4"))` then `get_settings().radarr_quality_profile_id == "4"` and `get_raw_value("radarr_quality_profile_id") == "4"`; a clear test asserting `update_settings(SettingsUpdate(radarr_quality_profile_id=""))` deletes the key (`get_raw_value(...) is None`). Mirror for sonarr.
- `test_settings_schemas.py`: assert the two new optional fields exist on both schemas and default to `None`.

- **Verify (run as the task gate):** `cd backend && pytest -q tests/test_settings_schemas.py tests/test_settings_service.py`

**Verify-at-impl**
- Confirm `_get_plain` / `CLEARABLE_KEYS` / `update_settings` shapes unchanged (read `settings/service.py:36-50,76-80`).
- Quality-profile id is **non-sensitive** → use `_get_plain`, never `_get_masked` / `ENCRYPTED_KEYS`.

---

## T2 — Quality-profile list endpoints (Radarr + Sonarr)

**Target files**
- `backend/src/app/modules/radarr/router.py`
- `backend/src/app/modules/sonarr/router.py`
- Tests: `backend/tests/test_radarr_router.py`, `backend/tests/test_sonarr_router.py`

**Change**
- Add `@router.get("/quality-profiles")` to each router. Body:
  ```python
  profiles = await client.get_quality_profiles()
  return [{"id": p["id"], "name": p["name"]} for p in profiles]
  ```
  Wrap in the same `try/except TimeoutException / HTTPStatusError` pattern used by the existing `/queue` … `/add` handlers in each router (504 on timeout, 503 on `HTTPStatusError`). Use the existing `get_radarr_client` / `get_sonarr_client` `Depends`.
- Return only `id` + `name` (trim the heavy `*arr` profile object) — this is the UI contract.

**Tests (TDD)**
- `test_radarr_router.py`: with the existing `mock_radarr_client` fixture, set `mock_radarr_client.get_quality_profiles.return_value = [{"id": 1, "name": "Any", "items": [...]}, {"id": 4, "name": "HD-1080p"}]`; GET `/api/radarr/quality-profiles`; assert `200` and body `== [{"id":1,"name":"Any"},{"id":4,"name":"HD-1080p"}]` (heavy fields dropped).
- `test_sonarr_router.py`: mirror with the sonarr fixture (confirm that file's mock-client fixture name; mirror `test_radarr_router.py:11-22` if absent).

- **Verify (run as the task gate):** `cd backend && pytest -q tests/test_radarr_router.py tests/test_sonarr_router.py`

**Verify-at-impl**
- Confirm `test_sonarr_router.py` has a `get_sonarr_client` dependency-override fixture analogous to radarr's; if not, add one mirroring `test_radarr_router.py:11-22`.
- Real Radarr/Sonarr v3 `qualityprofile` objects expose `id` and `name`; the mapping assumes those keys (matches `add_*` which already reads `profiles[0]["id"]`).

---

## T3 — Pass saved quality profile through batch processing

**Target files**
- `backend/src/app/modules/watchlist/service.py` — `process_batch`
- Tests: `backend/tests/test_watchlist_batch.py`

**Change**
- In `process_batch`, alongside the existing `root_folder = get_setting(...)`, read the profile:
  - movie branch: `quality_profile_id = get_setting("radarr_quality_profile_id")`
  - show branch: `quality_profile_id = get_setting("sonarr_quality_profile_id")`
- Cast once outside the loop: `quality_profile_id = int(quality_profile_id) if quality_profile_id else None` (empty/None → `None` → client keeps auto-first-profile fallback).
- Pass `quality_profile_id=quality_profile_id` to `client.add_movie(...)` and `client.add_series(...)`. Do **not** pass it to `update_season_monitoring` (existing series keep their profile).

**Tests (TDD)**
- Extend `test_watchlist_batch.py`. Patch `app.modules.watchlist.service.get_setting` (it's imported into that module namespace at `service.py:7`) with a `side_effect` mapping, e.g. `{"radarr_quality_profile_id": "4", "radarr_root_folder": None}.get(k)`, and patch `RadarrClient.add_movie` (same style as `test_batch_process_movies` at `:84`). After processing, assert `mock_add_movie.call_args.kwargs["quality_profile_id"] == 4` (int, not str).
- Mirror for shows: patch `sonarr_quality_profile_id` → assert `add_series` received `quality_profile_id=<int>`.
- Add a "no profile set" case: `get_setting` returns `None` → assert `add_movie` called with `quality_profile_id=None` (back-compat: existing tests `test_batch_process_movies/_shows` must still pass unchanged).

- **Verify (run as the task gate):** `cd backend && pytest -q tests/test_watchlist_batch.py`

**Verify-at-impl**
- Confirm patch target is `app.modules.watchlist.service.get_setting` (bound name from `from app.config import settings, get_setting`).
- Existing `test_batch_process_*` patch `RadarrClient.add_movie` / `SonarrClient.add_series` (not the client factory), so kwarg assertions read from those mocks' `call_args`.

---

## T4 — SettingsView quality-profile dropdowns (frontend)

**Target files**
- `frontend/src/services/settings.js`
- `frontend/src/views/SettingsView.vue`

**Change**
- `settings.js`: add `getRadarrQualityProfiles()` → `api.get('/radarr/quality-profiles')` and `getSonarrQualityProfiles()` → `api.get('/sonarr/quality-profiles')`.
- `SettingsView.vue`:
  - `form`: add `radarr_quality_profile_id: ''`, `sonarr_quality_profile_id: ''`.
  - Add reactive `qualityProfiles = reactive({ radarr: [], sonarr: [] })`.
  - In `loadSettings()`: prefill `form.radarr_quality_profile_id = settings.value.radarr_quality_profile_id || ''` (mirror sonarr); fetch both profile lists (guard each in `try/catch` — empty list if the service isn't configured, mirroring how missing keys are tolerated).
  - Add a `<select>` (with a `<option value="">Use {Radarr,Sonarr} default</option>` first option) under each Root Folder field, `v-model="form.radarr_quality_profile_id"`, options `v-for` over `qualityProfiles.radarr` (`:value="p.id"` `{{ p.name }}`). Mirror for sonarr.
  - `saveSettings()`: add both keys to the `clearableFields` array so a blank selection clears the saved default.

**Tests**
- Frontend has **no test runner** (`frontend/package.json` defines only `dev`/`build`/`preview`). No automated test. Gate is a clean production build; manual smoke = open `/settings`, confirm dropdowns populate and persist.

- **Verify (run as the task gate):** `cd frontend && npm run build`

**Verify-at-impl**
- Read `SettingsView.vue:144-152,176-208` for the exact `form` / `loadSettings` / `clearableFields` shapes before editing.
- `<select>` `:value="p.id"` yields an int model value; on save, the int serializes fine to the string-typed setting. Prefill compares against the stored string — coerce option compare if needed (`String(p.id)`), verify the selected option highlights after reload.

---

## Barrier (whole-slice gate, run before the single commit)

- `cd backend && pytest` — full suite green (new tests + all existing, including unchanged `test_batch_process_*`).
- `cd frontend && npm run build` — clean build.
- Then ONE commit for T1–T4 together.

## Out of scope for tasks (closure handled by `/execute-plan` Step 9)

- `CHANGELOG.md` entry (new minor: quality-profile default). README API tables / Settings section may gain the two `quality-profiles` endpoints — closure docs, not a slice task.
- Note (not this slice): `backend/pyproject.toml` `version` is stale at `2.3.0` vs `2.5.0`; flagged separately, left untouched here.
