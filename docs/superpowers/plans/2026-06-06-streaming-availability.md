<!-- orchestrator-native-plan: v1 -->

## Orchestrator execution contract — READ FIRST (how `/execute-plan` runs this slice)

- **Task ids:** literal labels `T1 T2 T3 T4`, used verbatim in `orchestrator_begin`/`orchestrator_report`.
- **Dependency levels:** all four tasks touch **disjoint files** → **one parallel level** (T1, T2, T3, T4 run together). NEVER `isolated: true`; they share the working tree and build against the **Contract** block below.
- **ONE barrier commit for the whole slice** — no commit per task. All four tasks land together at the barrier.
- **No fixture/snapshot regen** in this slice — there are no golden files or snapshots; tests are hand-written. Nothing to authorize.
- **Per-task `Verify`** is stated on each task as `- **Verify (run as the task gate):** <exact command>`.
- **Barrier gate (whole slice):** `cd backend && pytest` **and** `cd frontend && npm run test && npm run build`.
- **Closure is `/execute-plan` Step 9's job** — the CHANGELOG version entry and flipping Tier 1 #3 to SHIPPED in the roadmap spec are closure, NOT tasks here. T4 covers only project docs (`CLAUDE.md`).

---

# Slice: Streaming-availability ("Where to Watch") on detail pages — Roadmap Tier 1 #3

**Date:** 2026-06-06
**Spec:** `docs/superpowers/specs/2026-06-06-roadmap-design.md` (Tier 1 → #3)
**Scope class:** Medium (planning-scope signal only — two layers, small well-patterned changes across disjoint files).
**Predecessors:** #1 paginated Discover (v2.7.0) and #2 watchlist sort/filter (v2.8.0) shipped; this is the next sequenced quick win.

## Goal

On a movie/show **detail page**, show where the title can be streamed (subscription / free)
for a configurable region, so the user can decide whether to download it or just stream it.
Region defaults to `US` and is editable in Settings.

## Acceptance (from spec)

- Opening a movie or show detail page lists the available streaming providers for the
  configured region.
- Changing the region in Settings changes which region's providers appear.
- When no providers exist for the region, the section is simply absent (no error).

## Scope decision — detail page only (poster badges deferred)

The roadmap also mentions "a small poster badge". TMDB's **list** endpoints
(trending / discover / search) do **not** return watch-provider data, so a poster badge
would need one extra TMDB call **per card** — expensive and outside the stated acceptance.
This slice ships the detail-page surface only. Poster badges stay a backlog idea (would
need a batched/cached provider lookup); explicitly **out of scope here**.

## Design decisions (grounded in the current code)

- **One round-trip, reuse the existing pattern.** `TMDBClient.get_movie_detail` /
  `get_show_detail` already pass `append_to_response="credits,videos,recommendations"` to
  `_get_or_none`. Append `watch/providers` to that same string — no extra HTTP request.
  TMDB returns the data under the literal key `"watch/providers"` →
  `{"results": {"US": {"link", "flatrate":[…], "free":[…], "ads":[…], "rent":[…], "buy":[…]}, …}}`.
  (Confirmed: both methods use `_get_or_none` with that append string; no tmdb-client test
  asserts the append value, so changing it is safe.)
- **Region via the existing helper.** `from app.config import get_setting`;
  `get_setting("streaming_region")` checks the DB then `.env`, returning `None` when unset →
  router falls back to `"US"`. No DB migration: settings are key/value rows in the `settings`
  table (same approach as `radarr_quality_profile_id`).
- **Shape the response in the router**, not the client. The detail endpoints return the raw
  TMDB dict with **no `response_model`**, so a new top-level `watch_providers` field passes
  through untouched. Drop the bulky all-regions `"watch/providers"` blob before returning.
- **"Streamed" = subscription + free only.** Include `flatrate` and merge `free`+`ads`;
  **exclude `rent`/`buy`** (paying per title is not "already streamable").
- **No frontend component-test harness** (repo has no jsdom / `@vue/test-utils`; devDeps =
  vite / vitest / @vitejs-plugin-vue only). The new UI is purely presentational, so its gate
  is the Vite build (compiles the SFC, resolves imports); behavior coverage lives in the
  backend tests where the data shaping happens.

## Confirmed facts (pre-flight)

- `backend/src/app/modules/discovery/tmdb_client.py`: `get_movie_detail`/`get_show_detail`
  call `_get_or_none(f"/{type}/{id}", {"append_to_response": "credits,videos,recommendations"})`.
- `backend/src/app/modules/discovery/router.py`: `get_movie_detail`/`get_show_detail` route
  handlers return the raw `data` dict after a `if not data: raise HTTPException(404)` guard;
  module already imports `from app.config import settings`.
- `backend/src/app/config.py`: `get_setting(key)` → DB first, `.env` fallback, else None.
- `backend/src/app/models.py`: `Settings` is key/value rows; no per-setting column.
- `backend/src/app/modules/settings/{schemas,service}.py`: additive settings pattern —
  field on `SettingsUpdate`+`SettingsResponse`, `_get_plain` in `get_settings()`, membership
  in `CLEARABLE_KEYS`; non-encrypted keys persist as plain strings via the generic path.
- Endpoint tests mock `tmdb_client.get_movie_detail`/`get_show_detail` at the router and
  assert `assert_called_once_with(id)` — the router still calls those with just the id, so
  that assertion stays valid.
- `frontend/src/services/discover.js`: `getMovieDetail`/`getShowDetail` return the unwrapped
  dict (so `media.watch_providers` is available). `frontend/src/services/settings.js`:
  `updateSettings(obj)` forwards arbitrary fields (no change needed).
- `frontend/src/views/SettingsView.vue`: additive form pattern — add to `form`, prefill in
  `loadSettings()`, add to `clearableFields` in `saveSettings()`, add a UI section.

## Contract (all tasks build against this — keep shapes exact)

**New settings key:** `streaming_region` (plain string, clearable). Exposed on
`SettingsResponse.streaming_region`; accepted on `SettingsUpdate.streaming_region`.

**Backend detail response gains** `watch_providers` (and no longer contains the raw
`"watch/providers"` key):

```json
"watch_providers": {
  "region": "US",
  "link": "https://www.themoviedb.org/movie/603/watch?locale=US",
  "flatrate": [{"provider_id": 8, "provider_name": "Netflix", "logo_path": "/abc.jpg"}],
  "free":     [{"provider_id": 538, "provider_name": "Plex", "logo_path": "/xyz.jpg"}]
}
```

- `region` always present (the configured region, default `"US"`).
- `link` is the region's TMDB watch link or `null`.
- `flatrate` / `free` are arrays of `{provider_id, provider_name, logo_path}`; empty arrays
  when the region has none. `free` = TMDB `free` + `ads` deduped by `provider_id`.

**Frontend** reads `media.watch_providers`; logo URL = `https://image.tmdb.org/t/p/w92{logo_path}`.

---

## T1 — Backend: `streaming_region` setting

**Target files:**
- `backend/src/app/modules/settings/schemas.py`
- `backend/src/app/modules/settings/service.py`
- `backend/tests/test_settings_schemas.py` (extend)
- `backend/tests/test_settings_service.py` (extend)

**Change:**
- `schemas.py`: add `streaming_region: Optional[str] = None` to **both** `SettingsUpdate`
  and `SettingsResponse` (mirror the `radarr_quality_profile_id` lines).
- `service.py`:
  - In `get_settings()` add `streaming_region=self._get_plain(settings, "streaming_region")`
    to the `SettingsResponse(...)` construction.
  - Add `"streaming_region"` to the `CLEARABLE_KEYS` set.
  - No change to `_set_value`/`update_settings` (generic path; NOT in `ENCRYPTED_KEYS`, so it
    persists as a plain string).

**Tests (TDD — write first, watch fail, then implement):**
- `test_settings_schemas.py`: `SettingsUpdate(streaming_region="GB")` and
  `SettingsResponse(streaming_region="GB")` accept/expose the field; default is `None`.
- `test_settings_service.py` (reuse the existing `db` fixture):
  - round-trip: `update_settings(SettingsUpdate(streaming_region="GB"))` →
    `get_settings().streaming_region == "GB"` and `get_raw_value("streaming_region") == "GB"`.
  - clear: setting it to `""` deletes the key (`get_raw_value(...) is None`).
  - partial-update isolation: setting `streaming_region` does not wipe an existing
    `radarr_quality_profile_id` (mirror `test_partial_update_preserves_other_quality_profile`).

**Non-goals:** no encryption, no UI here (T3), no region validation/whitelist.

- **Verify (run as the task gate):** `cd backend && pytest -q tests/test_settings_schemas.py tests/test_settings_service.py`

---

## T2 — Backend: TMDB watch-providers on detail endpoints

**Target files:**
- `backend/src/app/modules/discovery/tmdb_client.py`
- `backend/src/app/modules/discovery/router.py`
- `backend/tests/test_tmdb_client.py` (extend)
- `backend/tests/test_movie_detail_endpoint.py` (extend)
- `backend/tests/test_show_detail_endpoint.py` (extend)
- NEW `backend/tests/test_watch_providers.py` (pure extractor unit tests)

**Change:**
- `tmdb_client.py`: in `get_movie_detail` and `get_show_detail`, change the
  `append_to_response` value from `"credits,videos,recommendations"` to
  `"credits,videos,recommendations,watch/providers"`. Same single `_get_or_none` call; no
  new method, no extra request.
- `router.py`:
  - Extend the config import to `from app.config import settings, get_setting`. Add module
    constant `DEFAULT_REGION = "US"`.
  - Add a pure helper `_extract_watch_providers(detail: dict, region: str) -> dict`:

```python
def _extract_watch_providers(detail: dict, region: str) -> dict:
    results = (detail.get("watch/providers") or {}).get("results", {})
    entry = results.get(region) or {}

    def _slim(items):
        return [
            {
                "provider_id": p.get("provider_id"),
                "provider_name": p.get("provider_name"),
                "logo_path": p.get("logo_path"),
            }
            for p in (items or [])
        ]

    # free = free + ads, deduped by provider_id, order preserved
    seen, free = set(), []
    for p in (entry.get("free") or []) + (entry.get("ads") or []):
        pid = p.get("provider_id")
        if pid in seen:
            continue
        seen.add(pid)
        free.append({
            "provider_id": pid,
            "provider_name": p.get("provider_name"),
            "logo_path": p.get("logo_path"),
        })

    return {
        "region": region,
        "link": entry.get("link"),
        "flatrate": _slim(entry.get("flatrate")),
        "free": free,
    }
```

  - In the `get_movie_detail` and `get_show_detail` **route handlers**, after the existing
    `if not data: raise HTTPException(...)` guard and before `return data`:

```python
    region = get_setting("streaming_region") or DEFAULT_REGION
    data["watch_providers"] = _extract_watch_providers(data, region)
    data.pop("watch/providers", None)
    return data
```

  - Do NOT touch the person / collection / list endpoints.

**Tests (TDD):**
- `test_watch_providers.py` (pure, no HTTP): import `_extract_watch_providers` from
  `app.modules.discovery.router` and assert:
  - picks the requested region's `flatrate`, slimmed to `{provider_id, provider_name, logo_path}`.
  - merges `free`+`ads` and dedupes by `provider_id`.
  - missing region / missing `"watch/providers"` key → `region` set, `link` None, empty lists.
- `test_tmdb_client.py`: add async tests that patch `tmdb_client._get_or_none` (AsyncMock)
  and assert `get_movie_detail`/`get_show_detail` call it with an `append_to_response`
  containing `"watch/providers"`.
- `test_movie_detail_endpoint.py` + `test_show_detail_endpoint.py`: extend `mock_response`
  with `"watch/providers": {"results": {"US": {"link": "...", "flatrate": [{...Netflix...}]}}}`;
  assert the response JSON has `data["watch_providers"]["region"] == "US"`, one flatrate
  provider, and that the raw `"watch/providers"` key is **absent**. Existing assertions
  (credits/videos/recommendations present, 404 path, `assert_called_once_with(id)`) stay green.

**Verify-at-impl:** in tests `get_setting("streaming_region")` opens `SessionLocal` and (no
key set) returns None → `DEFAULT_REGION` "US" is used, so endpoint tests need no DB override.
If a stray real DB value interferes, set the region explicitly via the settings service in
the test (or assert region from the mock's US block).

- **Verify (run as the task gate):** `cd backend && pytest -q tests/test_watch_providers.py tests/test_tmdb_client.py tests/test_movie_detail_endpoint.py tests/test_show_detail_endpoint.py`

---

## T3 — Frontend: "Where to Watch" UI + region setting field

**Target files:**
- NEW `frontend/src/components/WatchProviders.vue` (presentational)
- `frontend/src/views/MediaDetailView.vue`
- `frontend/src/views/SettingsView.vue`

**Change:**
- `WatchProviders.vue` (`<script setup>`, Composition API per CLAUDE.md):
  - prop `providers: { type: Object, default: null }` (the `media.watch_providers` object).
  - computed `streamItems = [...(providers?.flatrate || []), ...(providers?.free || [])]`.
  - computed `hasProviders = streamItems.length > 0`.
  - render only when `hasProviders`: a "Where to Watch (`{{ providers.region }}`)" heading and
    a row of provider logos; each is `<a :href="providers.link" target="_blank"
    rel="noopener" :title="p.provider_name">` wrapping
    `<img :src="`https://image.tmdb.org/t/p/w92${p.logo_path}`" :alt="p.provider_name">`
    (text fallback to `provider_name` when `logo_path` is null). Scoped styles, small logos.
- `MediaDetailView.vue`: import `WatchProviders`; in the `.info` column render
  `<WatchProviders :providers="media.watch_providers" />` immediately after the `.actions`
  block. No data-fetch change — `getMovieDetail`/`getShowDetail` already return the dict
  including `watch_providers`.
- `SettingsView.vue`:
  - add `streaming_region: ''` to the `form` reactive object.
  - in `loadSettings()`: `form.streaming_region = settings.value.streaming_region || ''`.
  - in `saveSettings()`: add `'streaming_region'` to the `clearableFields` array (empty value
    clears it → reverts to default US).
  - add a "Streaming Availability" `<section>` with a text input bound to
    `form.streaming_region` (placeholder "US", `maxlength="2"`) and a hint: "Two-letter
    country code (e.g. US, GB, CA). Leave empty to default to US."

**Non-goals:** no poster badges (out of scope, see Scope decision); no new frontend service
methods (`settings.updateSettings` forwards arbitrary fields; detail already returns
`watch_providers`).

- **Verify (run as the task gate):** `cd frontend && npm run build`

---

## T4 — Docs: project structure (CLAUDE.md only)

**Target files:**
- `CLAUDE.md`

**Change (project docs only — NOT CHANGELOG, NOT the roadmap spec; those are Step 9 closure):**
- In the "Project Structure" frontend `components/` list, add `WatchProviders.vue`.
- In the `settings/` module line, note the new `streaming_region` (region for
  streaming-availability lookups, default US) alongside the existing description.

- **Verify (run as the task gate):** `cd backend && pytest -q tests/test_settings_service.py`

---

## Barrier (after T1–T4 all report done)

- **Gate:** `cd backend && pytest` **and** `cd frontend && npm run test && npm run build`
- All backend tests green (existing + new), existing frontend Vitest util tests green, and
  the frontend builds. One commit for the whole slice.
- Then `/execute-plan` Step 9 handles closure (CHANGELOG entry + roadmap status flip for
  Tier 1 #3).

## Manual smoke (optional, post-barrier)

`start.bat`, open a movie detail page → "Where to Watch" shows US providers; change the
region to `GB` in Settings, reload the detail page → providers reflect GB (or the section is
hidden if none).
