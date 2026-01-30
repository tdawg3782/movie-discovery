# Season Selection for TV Shows

## Overview

Allow users to select which seasons to download when adding TV shows to the watchlist, rather than downloading all seasons by default.

## User Flow

### Adding a TV Show

1. User clicks "Add to Watchlist" on a TV show detail page
2. Modal appears showing all seasons with checkboxes (all checked by default)
3. User unchecks seasons they don't want
4. User clicks "Add to Watchlist" to save

Movies skip the modal and add directly (no seasons to select).

### Editing in Watchlist

1. User clicks on a TV show row in the watchlist
2. Row expands to show season checkboxes
3. User toggles seasons on/off
4. Changes save automatically or via "Save" button
5. Row collapses when clicked again

## Data Model

### Database Schema

Add column to `watchlist` table:

```python
selected_seasons: Mapped[str | None] = mapped_column(Text, nullable=True)
# Stores JSON array like "[1, 2, 3]"
# NULL means "all seasons" (backwards compatible)
```

### API Schemas

```python
# WatchlistAdd request
class WatchlistAdd(BaseModel):
    tmdb_id: int
    media_type: str
    notes: str | None = None
    selected_seasons: list[int] | None = None  # NEW

# WatchlistItem response
class WatchlistItem(MediaBase):
    id: int
    added_at: datetime
    notes: str | None = None
    status: str = "pending"
    selected_seasons: list[int] | None = None  # NEW
    total_seasons: int | None = None           # NEW - for display
```

### Interpretation

| `selected_seasons` value | Meaning |
|--------------------------|---------|
| `None` | All seasons (default, backwards compatible) |
| `[1, 2, 3]` | Only seasons 1, 2, 3 monitored |
| `[]` | Treat as all seasons (edge case) |

## UI Components

### SeasonSelectModal.vue (New)

Modal for selecting seasons when adding a TV show.

```
┌─────────────────────────────────────────┐
│  Add to Watchlist                    ✕  │
├─────────────────────────────────────────┤
│  Shrinking (2023)                       │
│                                         │
│  Select Seasons:                        │
│  ┌─────────────────────────────────┐   │
│  │ ☑ Select All                     │   │
│  ├─────────────────────────────────┤   │
│  │ ☑ Season 1 (10 episodes)        │   │
│  │ ☑ Season 2 (12 episodes)        │   │
│  │ ☑ Season 3 (11 episodes)        │   │
│  └─────────────────────────────────┘   │
│                                         │
│            [Cancel]  [Add to Watchlist] │
└─────────────────────────────────────────┘
```

**Behavior:**
- All seasons checked by default
- "Select All" toggles all checkboxes
- Season 0 (Specials) hidden from list
- Episode count shown per season

### WatchlistView.vue Changes

Expandable rows for TV shows:

```
┌─────────────────────────────────────────────────────┐
│ [poster] Shrinking                              + × │
│          TV Show • PENDING • 2 of 3 seasons    ▼   │
└─────────────────────────────────────────────────────┘

   ↓ Click to expand ↓

┌─────────────────────────────────────────────────────┐
│ [poster] Shrinking                              + × │
│          TV Show • PENDING • 2 of 3 seasons    ▲   │
├─────────────────────────────────────────────────────┤
│  ☑ Season 1 (10 episodes)                          │
│  ☑ Season 2 (12 episodes)                          │
│  ☐ Season 3 (11 episodes)                          │
│                          [Save Changes]            │
└─────────────────────────────────────────────────────┘
```

**Behavior:**
- Arrow indicator shows expandability (TV shows only)
- Summary shows "X of Y seasons"
- Legacy items (`selected_seasons: null`) show "All seasons"

## Sonarr Integration

### API Payload

When adding to Sonarr, set `monitored` per season:

```python
{
    "title": "Shrinking",
    "tvdbId": 12345,
    "seasons": [
        {"seasonNumber": 1, "monitored": True},
        {"seasonNumber": 2, "monitored": True},
        {"seasonNumber": 3, "monitored": False}
    ],
    "addOptions": {
        "searchForMissingEpisodes": True
    }
}
```

### SonarrClient Changes

```python
async def add_series(
    self,
    tmdb_id: int,
    quality_profile_id: int | None = None,
    selected_seasons: list[int] | None = None,  # NEW
) -> dict:
    series = await self.lookup_series(tmdb_id)

    # Set season monitoring based on selection
    if selected_seasons is not None:
        for season in series.get("seasons", []):
            season["monitored"] = season["seasonNumber"] in selected_seasons

    # ... existing add logic ...
```

## Out of Scope

- Season air dates in selector
- Episode-level selection
- Bulk editing across multiple shows
- Modifying seasons for shows already in Sonarr

## Implementation Tasks

1. Database: Add `selected_seasons` column
2. Backend: Update watchlist schemas and endpoints
3. Backend: Update Sonarr client to pass season selection
4. Frontend: Create SeasonSelectModal component
5. Frontend: Update MediaDetailView to show modal for TV shows
6. Frontend: Add expandable season editing to WatchlistView
