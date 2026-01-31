# Manage Seasons for Existing Shows

## Problem

When a user adds a TV show with partial seasons (e.g., Season 1 of a 9-season show), there's no way to go back and add more seasons later. The app shows "added" status but provides no management capability.

## Solution

Allow users to select additional seasons for shows already in Sonarr, using the existing watchlist as a staging area.

---

## Feature 1: Season Management from Detail View

### User Flow

1. User views a show that's already in Sonarr
2. Clicks "+" button (same as new shows)
3. SeasonSelectModal opens with color-coded status:
   - Green = Downloaded (not selectable)
   - Yellow = Monitored/downloading (not selectable)
   - Gray = Not monitored (checkbox, can select)
4. User selects additional seasons
5. Clicks "Add X Seasons" → goes to watchlist
6. User batch processes from watchlist

### UI Mockup

```
┌─────────────────────────────────────────┐
│  Breaking Bad - Select Seasons          │
├─────────────────────────────────────────┤
│  [green]  Season 1    (8/8 episodes)    │
│  [green]  Season 2    (13/13 episodes)  │
│  [yellow] Season 3    (5/13 downloading)│
│  [ ]      Season 4    (not monitored)   │
│  [ ]      Season 5    (not monitored)   │
├─────────────────────────────────────────┤
│  [Cancel]            [Add 0 Seasons]    │
└─────────────────────────────────────────┘
```

---

## Feature 2: Library Status Filter

### User Flow

1. User opens Discovery page
2. Filter panel shows "Library Status" section
3. When viewing Movies: "In Radarr" / "Not in Library" checkboxes
4. When viewing TV Shows: "In Sonarr" / "Not in Library" checkboxes
5. Checking "In Sonarr" shows only shows already in library

### UI Mockup

```
┌─────────────────────────┐
│ Media Type              │
│ ( ) Movies  (•) TV Shows│
├─────────────────────────┤
│ Library Status          │
│ [x] In Sonarr           │
│ [ ] Not in Library      │
├─────────────────────────┤
│ Genres, Year, etc...    │
└─────────────────────────┘
```

---

## Technical Design

### New Sonarr Client Methods

```python
async def get_series_details(self, tmdb_id: int) -> dict | None:
    """Get full series info including season status from Sonarr library.

    Returns:
        {
            "id": 123,
            "title": "Breaking Bad",
            "seasons": [
                {"seasonNumber": 1, "monitored": True, "statistics": {"percentOfEpisodes": 100}},
                {"seasonNumber": 2, "monitored": True, "statistics": {"percentOfEpisodes": 38}},
                {"seasonNumber": 3, "monitored": False, "statistics": {"percentOfEpisodes": 0}},
            ]
        }
    """

async def update_season_monitoring(self, tmdb_id: int, seasons_to_add: list[int]) -> dict:
    """Add monitoring for additional seasons and trigger search.

    1. GET existing series from Sonarr
    2. Modify seasons array - set monitored=True for new seasons
    3. PUT updated series back to Sonarr
    4. POST command to search for new episodes
    """
```

### New API Endpoint

```
GET /api/sonarr/series/{tmdb_id}/seasons

Response:
{
    "in_library": true,
    "sonarr_id": 123,
    "seasons": [
        {"number": 1, "status": "downloaded", "episodes": "8/8"},
        {"number": 2, "status": "monitored", "episodes": "5/13"},
        {"number": 3, "status": "available", "episodes": "0/13"}
    ]
}
```

### Watchlist Model Change

```python
class Watchlist(Base):
    # ... existing fields ...
    is_season_update: bool = False  # True when adding seasons to existing show
```

### Batch Processing Logic

```python
async def batch_process(self, tmdb_ids, media_type):
    for tmdb_id in tmdb_ids:
        item = self.get_by_tmdb_id(tmdb_id)

        if item.is_season_update:
            # Show already exists - update monitoring
            await sonarr_client.update_season_monitoring(
                tmdb_id,
                json.loads(item.selected_seasons)
            )
        else:
            # New show - add to Sonarr
            await sonarr_client.add_series(
                tmdb_id,
                selected_seasons=json.loads(item.selected_seasons)
            )
```

### Watchlist Display

Season update items show differently:

```
┌──────────────────────────────────────────────┐
│ [ ] [poster] Breaking Bad      +Seasons 4, 5 │  ← Update
│ [ ] [poster] New Show          Seasons 1-3   │  ← New
└──────────────────────────────────────────────┘
```

---

## Edge Cases

| Scenario | Handling |
|----------|----------|
| User selects seasons already monitored | Filter them out silently |
| Show removed from Sonarr before processing | Fall back to `add_series()` |
| Show has no unmonitored seasons | Disable "+" button or show "All seasons monitored" |

---

## Out of Scope (YAGNI)

- Removing/unmonitoring seasons (use Sonarr directly)
- Radarr equivalent (movies don't have seasons)
- Dedicated library management view (filter on Discovery is sufficient)

---

## Implementation Order

1. Backend: Sonarr client methods (`get_series_details`, `update_season_monitoring`)
2. Backend: New API endpoint for season status
3. Backend: Watchlist model + batch processing changes
4. Frontend: SeasonSelectModal with status display
5. Frontend: FilterPanel library status section
6. Frontend: WatchlistView display changes
