# Parallel Features Design

**Date:** 2026-01-29
**Status:** Approved

## Overview

Five independent feature departments to be developed in parallel using git worktrees.

## Departments

### A: Settings & Config
**Branch:** `feature/settings-config`
**Worktree:** `../movie_discovery-settings`

**Purpose:** Replace .env file with UI-based configuration.

**Backend:**
- `modules/settings/` - router, service, schemas, storage
- `GET /api/settings` - Get current settings (keys masked)
- `PUT /api/settings` - Update settings
- `POST /api/settings/test` - Test API connection

**Frontend:**
- `views/SettingsView.vue` - Settings page
- `services/settings.js` - API calls

**Features:**
- Form fields for each API (URL + API key)
- "Test Connection" button per service
- Keys hidden by default, reveal on click
- Auto-import from .env on first load
- Encrypted storage (SQLite)

---

### B: Discovery Filters
**Branch:** `feature/discovery-filters`
**Worktree:** `../movie_discovery-discovery`

**Purpose:** Transform trending view into filterable discovery.

**Backend:**
- Modify `modules/discovery/` - add filter params
- `GET /api/genres/movies` - List movie genres
- `GET /api/genres/shows` - List TV genres

**Filter Parameters:**
```
?genre=28,12          # Action, Adventure
&year=2024            # Release year
&year_gte=2020        # Released after
&year_lte=2024        # Released before
&rating_gte=7.0       # Minimum TMDB rating
&certification=PG-13  # Content rating
&sort_by=popularity   # popularity, rating, release_date
```

**Frontend:**
- `components/FilterPanel.vue` - Collapsible filter sidebar
- `components/GenreSelector.vue` - Multi-select genre chips
- `components/RangeSlider.vue` - Year/rating range picker

**UX:**
- Filters in collapsible panel (mobile-friendly)
- Chips show active filters, click to remove
- Results update as filters change (debounced)

---

### C: Media Deep Dive
**Branch:** `feature/media-deep-dive`
**Worktree:** `../movie_discovery-media`

**Purpose:** Rich exploration pages for people, collections, related content.

**Backend:**
- `GET /api/person/{id}` - Person details + credits
- `GET /api/movies/{id}` - Movie details (trailer, collection_id)
- `GET /api/shows/{id}` - Show details (trailer)
- `GET /api/movies/{id}/similar` - Similar movies
- `GET /api/shows/{id}/similar` - Similar shows
- `GET /api/collection/{id}` - Collection details

**Frontend:**
- `views/PersonView.vue` - Actor/director filmography
- `views/MediaDetailView.vue` - Full movie/show detail page
- `views/CollectionView.vue` - Franchise browser
- `components/TrailerModal.vue` - YouTube embed modal
- `components/CastCarousel.vue` - Horizontal cast scroll
- `components/MediaCarousel.vue` - "More Like This" row

**UX Flow:**
- Click poster → MediaDetailView
- Click actor → PersonView
- Click collection badge → CollectionView
- Trailers play in YouTube modal

---

### D: Watchlist Workflow
**Branch:** `feature/watchlist-workflow`
**Worktree:** `../movie_discovery-watchlist`

**Purpose:** Watchlist as staging queue before Radarr/Sonarr.

**Current Flow:**
```
Browse → Click "Add" → Immediately sent to Radarr/Sonarr
```

**New Flow:**
```
Browse → Click "Add" → Watchlist → Review → Batch send
```

**Backend:**
- `POST /api/watchlist/process` - Send selected to Radarr/Sonarr
- `DELETE /api/watchlist/batch` - Remove multiple items

**Frontend:**
- Modify `views/WatchlistView.vue` - Add selection + batch actions
- `components/WatchlistItem.vue` - Checkbox, status indicator
- `components/BatchActions.vue` - Batch action buttons

**UX Features:**
- Checkbox selection (select all / none)
- Batch actions: "Add to Library", "Remove Selected"
- Status column: Pending, In Library, Downloading
- Confirmation modal before batch processing

---

### E: Library Monitor
**Branch:** `feature/library-monitor`
**Worktree:** `../movie_discovery-library`

**Purpose:** Visibility into library and download progress.

**Backend:**
- `GET /api/radarr/recent` - Recently added movies
- `GET /api/radarr/queue` - Current download queue
- `GET /api/sonarr/recent` - Recently added shows
- `GET /api/sonarr/queue` - Current download queue
- `GET /api/library/activity` - Combined feed

**Frontend:**
- `views/LibraryView.vue` - Activity + queue page
- `components/ActivityFeed.vue` - Recently added list
- `components/QueueItem.vue` - Download progress row
- `components/DownloadProgress.vue` - Progress bar

**UX Features:**
- Recently Added tab: Poster grid with dates
- Downloads tab: Queue with progress bars, ETA
- Auto-refresh toggle (30s polling)

---

## Navigation

```
┌─────────────────────────────────────────┐
│  Discover  │  Watchlist  │  Library  │  ⚙️  │
└─────────────────────────────────────────┘
     B            D            E          A
```

## Merge Order

1. **A (Settings)** first - other features may read config
2. **B, C, D, E** in any order - fully independent

## Worktree Commands

```bash
# Create all worktrees
git worktree add -b feature/settings-config ../movie_discovery-settings main
git worktree add -b feature/discovery-filters ../movie_discovery-discovery main
git worktree add -b feature/media-deep-dive ../movie_discovery-media main
git worktree add -b feature/watchlist-workflow ../movie_discovery-watchlist main
git worktree add -b feature/library-monitor ../movie_discovery-library main

# List worktrees
git worktree list

# Remove when done
git worktree remove ../movie_discovery-settings
```
