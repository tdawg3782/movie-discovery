"""Pure seed/exclusion/aggregation logic for the For You surface. No I/O, no ORM, no clients."""

SEED_LIMIT = 20
RESULT_LIMIT = 40

Key = tuple[str, int]  # (media_type in {"movie", "show"}, tmdb_id)


def select_seeds(watchlist_keys: list[Key], owned_keys: list[Key], limit: int = SEED_LIMIT) -> list[Key]:
    """Watchlist keys first, then owned; dedupe preserving first-seen order; cap at limit."""
    seen: set[Key] = set()
    out: list[Key] = []
    for key in (*watchlist_keys, *owned_keys):
        if key in seen:
            continue
        seen.add(key)
        out.append(key)
        if len(out) >= limit:
            break
    return out


def exclusion_set(watchlist_keys: list[Key], owned_keys: list[Key]) -> set[Key]:
    """Union of watchlisted + owned keys (everything the surface must never show)."""
    return set(watchlist_keys) | set(owned_keys)


def _normalize(item: dict, media_type: str) -> dict:
    """TMDB result -> MediaResponse-shaped dict."""
    return {
        "tmdb_id": item.get("id"),
        "media_type": media_type,
        "title": item.get("title") or item.get("name") or "",
        "overview": item.get("overview"),
        "poster_path": item.get("poster_path"),
        "release_date": item.get("release_date") or item.get("first_air_date"),
        "vote_average": item.get("vote_average"),
        "library_status": None,
    }


def aggregate(rec_results: list[tuple[str, list[dict]]], exclude: set[Key], limit: int = RESULT_LIMIT) -> list[dict]:
    """rec_results: list of (media_type, tmdb_results_list).
    Per (media_type, id): frequency = number of DISTINCT result-lists recommending it
    (a repeat within the SAME list counts once); keep first-seen metadata.
    Drop any key in `exclude`. Sort by (frequency desc, vote_average desc, popularity desc).
    Return up to `limit` normalized dicts."""
    acc: dict[Key, dict] = {}
    for media_type, results in rec_results:
        seen_in_list: set[Key] = set()
        for item in results:
            tid = item.get("id")
            if tid is None:
                continue
            key = (media_type, tid)
            if key in exclude:
                continue
            entry = acc.get(key)
            if entry is None:
                entry = acc[key] = {
                    "freq": 0,
                    "meta": _normalize(item, media_type),
                    "vote": item.get("vote_average") or 0.0,
                    "pop": item.get("popularity", 0) or 0,
                }
            if key not in seen_in_list:
                entry["freq"] += 1
                seen_in_list.add(key)
    ranked = sorted(acc.values(), key=lambda e: (e["freq"], e["vote"], e["pop"]), reverse=True)
    return [e["meta"] for e in ranked[:limit]]
