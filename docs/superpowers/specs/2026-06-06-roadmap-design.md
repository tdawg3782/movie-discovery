# Movie Discovery — Feature Roadmap

**Date:** 2026-06-06
**Status:** Draft for review
**Type:** Roadmap (multiple features; each tier becomes its own spec → plan → implementation cycle)

## Context

Movie Discovery is a single-user, self-hosted "browse-and-add" front end for a home
media server. TMDB powers discovery (trending, search, genre/year/rating filters,
detail/person/collection pages); a watchlist stages picks; Radarr/Sonarr do the actual
downloading. FastAPI + SQLite backend, Vue 3 frontend, deployed on a Synology NAS and
reached remotely through a Cloudflare tunnel. Codebase is recently cleaned up (v2.6.0).

This roadmap captures the agreed direction for the next chapter of features.

## Goals

- A well-rounded menu of features, weighted toward day-to-day quality-of-life and
  smarter discovery.
- Tiered by effort: a set of quick wins, a few medium features, and one flagship.
- Each feature ships independently (framing "A": itch-first, ship-as-you-go).

## Constraints

- **Stays single-user.** No accounts, profiles, or access control.
- **Tight dependency footprint.** Willing to add at most one free notification channel.
  **Trakt and any external watch-tracking account are explicitly excluded.**
- Discovery improvements come from TMDB data not yet used, plus the app's own local data.
- No background scheduler unless a feature genuinely needs one (currently none do).

## Non-goals

- Multi-user, authentication, per-user profiles.
- Deep Plex/Jellyfin coupling or building a media player.
- Trakt / external watch-history services.
- A mobile redesign (parked in backlog; not flagged as painful).

---

## Tier 1 — Quick wins

### 1. Paginated browsing with restored position  *(top user itch)*

**Status:** SHIPPED — v2.7.0 (2026-06-06). Numbered Prev/Next replaces Load-More; activeTab/page/search/filters mirrored to the URL and restored on reload/back (results + FilterPanel chips). Pure unit-tested `frontend/src/utils/discoverState.js` + Vitest harness added. Known limitation carried to backlog: `inLibrary`/`notInLibrary` still filter client-side per page (server-side filtering remains a backlog item).

**What:** Replace the load-more/infinite append on Discover with numbered page
navigation (Prev/Next + page numbers). Persist the active tab, page, search query, and
filters in the URL query string so a reload — or the back button from a detail page —
returns the user to exactly where they were instead of resetting to page 1 / trending /
movies.

**Why:** The current feed appends results into component state only; any reload throws
away position. This is the user's #1 complaint.

**Size:** Quick win (frontend-heavy).

**Dependencies:** None.

**Implementation notes:**
- `DiscoverView.vue` already has `currentPage`/`totalPages`; backend `discover()` and the
  trending/search endpoints already return TMDB `total_pages`.
- Change `fetchContent`/`performSearch` to always replace results (drop the `append`
  path / `loadNextPage`). Add page controls to the template.
- Sync `activeTab`, `currentPage`, `searchQuery`, and `filters` to `route.query`; hydrate
  from the query on mount.
- **Known limitation to note (not fixed here):** `inLibrary`/`notInLibrary` filters run
  client-side after each page fetch, so paginated pages may look unevenly filled. Moving
  that filtering server-side is a backlog item.

**Acceptance:** Reload while on page 5 of "Action movies" returns to page 5 of Action
movies; navigating back from a detail page preserves tab, page, and filters.

### 2. Watchlist sort & filter  *(part of the "flat dump" itch)*

**Status:** SHIPPED — v2.8.0 (2026-06-06). Watchlist gained sort (date added / title / rating / release date, either direction, nulls-last) and filter (media type + status); the media-type tabs became state-driven. The chosen sort/filter is mirrored to the URL query (`router.replace`, defaults omitted) and restored on reload/back. Logic lives in a new pure, unit-tested `frontend/src/utils/watchlistState.js` (`parseWatchlistState` / `serializeWatchlistState` / `applyWatchlistView`, 20 Vitest cases); `WatchlistView.vue` is thin glue over it.

**What:** Add sort (date added, title, rating, release date) and filter (movies vs shows,
status) controls to the watchlist.

**Why:** The watchlist already carries title, rating, added date, release date, type, and
status, but offers no way to use any of it — it's one undifferentiated list.

**Size:** Quick win (frontend; data already present).

**Dependencies:** None.

**Implementation notes:** Client-side sort/filter over the already-enriched items.
Persist the chosen sort/filter in the URL query or localStorage.

**Acceptance:** Can sort by rating descending and filter to shows-only; choice survives a
reload.

### 3. Streaming-availability badges

**Status:** SHIPPED — v2.9.0 (2026-06-06). Detail pages (movie + show) now list streaming providers for a configurable region via a new top-level `watch_providers` field; data piggybacks on the existing detail request (`append_to_response=...,watch/providers`, no extra HTTP call). "Streamable" = `flatrate` + (`free`+`ads`), deduped, with `rent`/`buy` excluded; the raw all-regions blob is stripped. New `streaming_region` setting (plain/clearable, default US) editable in Settings. UI: new `frontend/src/components/WatchProviders.vue` rendered on `MediaDetailView` (hidden when no providers). Scope note: the poster-badge surface was deliberately deferred (TMDB list endpoints carry no provider data → one extra call per card) and remains a backlog idea.

**What:** Show where a title can be streamed (region-aware) on detail pages and as a small
poster badge, so the user can tell whether to download it or just stream it.

**Why:** Complements discovery cheaply; avoids downloading things already available.

**Size:** Quick win.

**Dependencies:** TMDB only.

**Implementation notes:** TMDB `/movie/{id}/watch/providers` and `/tv/{id}/watch/providers`.
Add `get_watch_providers()` to `TMDBClient`; add a region setting (default US, configurable
in Settings). Expose providers in the detail endpoint; add a frontend badge component.
Reuse the `MediaCache` pattern if caching is wanted.

**Acceptance:** Detail page lists available providers for the configured region.

---

## Tier 2 — Medium

### 4. Watchlist 2.0 — priority, notes, tags, sections  *(rest of the "flat dump" itch)*

**Status:** SHIPPED — v2.10.0 (2026-06-06). Watchlist items gained an editable priority (High/Normal/Low), the previously-hidden notes field, and optional tags, all editable via an inline per-item panel (movies + shows) backed by a new `PATCH /api/watchlist/{id}/details` partial-update endpoint. New "Group by priority" mode sections the list High→Normal→Low (empty sections hidden), mirrored to the URL `group` key and composed with the existing sort & filter. Backend added `priority`/`tags` columns to `Watchlist` via the project's first **idempotent additive startup migration** (`_migrate_watchlist_columns` after `create_all`) — fixes the latent "no such column" 500 risk on live DBs. Grouping/tags/priority logic lives in the pure, unit-tested `watchlistState.js`.

**What:** Add a priority flag/order, surface the existing notes field, optional tags, and
group the watchlist into sections (e.g. by priority or type).

**Why:** Turns the flat list into something organizable.

**Size:** Medium (small DB change + endpoint + UI).

**Dependencies:** None.

**Implementation notes:**
- `Watchlist.notes` **already exists** in `models.py` (unused in the UI) — just expose it.
- Add `priority` (int) and optional `tags` (Text/JSON) columns. Use the same lightweight
  migration approach as the prior `is_season_update` column add.
- Add a PATCH endpoint to edit priority/notes/tags. Frontend section grouping. Builds on #2.

**Acceptance:** Set a priority and a note on an item; both persist; the list groups by
priority.

### 5. Coming-Soon / Calendar view  *("what's next" itch)*

**What:** An agenda/calendar screen of upcoming episodes for tracked shows, announced or
upcoming movies, and release dates for watchlist items not yet in the library.

**Why:** No current way to see what's releasing soon for things being tracked.

**Size:** Medium.

**Dependencies:** Existing Radarr/Sonarr (reuse `BaseArrClient`); TMDB for watchlist dates.

**Implementation notes:** Add `get_calendar(start, end)` to the Radarr and Sonarr clients
(`/api/v3/calendar`); add an aggregating endpoint and a frontend agenda/calendar view.
**On-demand fetch on page open — no background scheduler required.**

**Acceptance:** Opening the view lists episodes airing this week plus upcoming watchlist
movie release dates.

### 6. Notifications  *(optional — not user-requested)*

**What:** Push a message when a download finishes or a new episode of a tracked show airs.

**Why:** Rounds out the menu; included for completeness.

**Size:** Medium.

**Dependencies:** One free notification channel (Discord / Telegram / ntfy). Channel
choice deferred until this item is scheduled. **Not Trakt.**

**Implementation notes:** Radarr/Sonarr webhook → new backend endpoint
(`/api/webhooks/{arr}`) → forward to the configured channel; channel type + URL stored in
Settings. Push-based, so no polling loop.

**Acceptance:** A Sonarr "on download" webhook produces a notification on the chosen
channel.

---

## Tier 3 — Flagship

### 7. Personalized discovery (fully local, no external account)  *("nothing personalized" itch)*

**What:** A "Recommended for you" surface driven entirely by the app's own data plus TMDB.
Done in steps so value lands early.

**Why:** Discovery is the same generic "trending" for everyone; it doesn't learn taste.

**Size:** Flagship (multi-step).

**Dependencies:** TMDB only. **Trakt is excluded** — personalization is built from local
signals (watchlist, library, and explicit like / not-interested actions).

**Implementation notes:**
- **Step 1 — aggregate recommendations:** add `get_recommendations()`
  (`/{type}/{id}/recommendations`) to `TMDBClient`. Aggregate recommendations/similar
  across watchlist + `LibraryStatus` items, dedupe, rank by frequency and vote, and
  exclude anything already in the watchlist or library. Cache results.
- **Step 2 — sharpen with local signals:** add explicit "like / not interested" actions
  (new lightweight table) and derive genre/keyword affinity from saved/owned items; weight
  the ranking accordingly; "not interested" suppresses a title.
- **Step 3 (optional) — "Because you added X" rows.**

**Acceptance:** The recommended surface excludes owned/watchlisted titles and visibly
shifts when items are added or marked "not interested".

---

## Sequence (framing A)

1 → 2 → 3 (quick wins) → 4 → 5 → (6 optional) → 7 (steps 1 → 2 → 3).

Each tier-item is shippable on its own and gets its own spec → implementation plan when
picked up.

## Backlog — uncommitted ideas

- Person/franchise following (surface new work from followed people/franchises).
- Home dashboard with saved custom "shelves" (e.g. "90s sci-fi I don't own").
- Smarter search (multi-search for people + titles, keyword/company search).
- Mobile polish pass.
- Server-side library filtering (fixes the per-page unevenness from feature #1).

## Open questions

- **Feature 6 channel:** which notification channel (Discord / Telegram / ntfy) — decide
  if/when feature 6 is scheduled.
- All other direction questions resolved: single-user, no Trakt, tiered framing A.
