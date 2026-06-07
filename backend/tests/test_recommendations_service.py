"""Unit tests for the pure recommendations service functions (no mocks)."""
from app.modules.recommendations import service


def test_select_seeds_dedupes_orders_and_caps():
    """Watchlist keys come before owned, duplicates collapse, and limit caps the output."""
    watchlist = [("movie", 1), ("show", 2), ("movie", 1)]
    owned = [("movie", 3), ("show", 2), ("movie", 4)]

    seeds = service.select_seeds(watchlist, owned, limit=3)

    assert seeds == [("movie", 1), ("show", 2), ("movie", 3)]


def test_select_seeds_orders_watchlist_before_owned():
    """Without hitting the cap, all watchlist keys precede owned-only keys."""
    watchlist = [("movie", 1)]
    owned = [("show", 2), ("movie", 1)]

    seeds = service.select_seeds(watchlist, owned)

    assert seeds == [("movie", 1), ("show", 2)]


def test_exclusion_set_is_union():
    """exclusion_set returns the set union of watchlist and owned keys."""
    watchlist = [("movie", 1), ("show", 2)]
    owned = [("show", 2), ("movie", 3)]

    assert service.exclusion_set(watchlist, owned) == {
        ("movie", 1),
        ("show", 2),
        ("movie", 3),
    }


def test_aggregate_ranks_higher_frequency_first():
    """A key recommended by two distinct lists outranks one recommended by a single list."""
    list_a = [{"id": 1, "title": "Twice", "vote_average": 5.0, "popularity": 10}]
    list_b = [{"id": 1, "title": "Twice", "vote_average": 5.0, "popularity": 10}]
    list_c = [{"id": 2, "title": "Once", "vote_average": 9.0, "popularity": 99}]

    out = service.aggregate(
        [("movie", list_a), ("movie", list_b), ("movie", list_c)], exclude=set()
    )

    assert [r["tmdb_id"] for r in out] == [1, 2]


def test_aggregate_repeat_within_same_list_counts_once():
    """A key appearing twice in the SAME list counts as frequency 1, not 2."""
    # id 1 appears twice in ONE list (freq must be 1, not 2).
    same_list = [
        {"id": 1, "title": "Dup", "vote_average": 5.0, "popularity": 1},
        {"id": 1, "title": "Dup", "vote_average": 5.0, "popularity": 1},
    ]
    # id 2 appears once but with a HIGHER vote, so on a freq tie it sorts first.
    other_list = [{"id": 2, "title": "Solo", "vote_average": 9.0, "popularity": 1}]

    out = service.aggregate([("movie", same_list), ("movie", other_list)], exclude=set())

    # Correct (both freq 1): id 2 wins the vote tie-break -> order [2, 1].
    # Buggy (id 1 freq 2): id 1 would sort first -> [1, 2]. So assert the order.
    assert [r["tmdb_id"] for r in out] == [2, 1]


def test_aggregate_keeps_first_seen_metadata():
    """When a key recurs across lists with different fields, first-seen metadata wins."""
    first = [{"id": 1, "title": "Original", "vote_average": 8.0, "popularity": 50}]
    second = [{"id": 1, "title": "Changed", "vote_average": 1.0, "popularity": 1}]

    out = service.aggregate([("movie", first), ("movie", second)], exclude=set())

    assert len(out) == 1
    assert out[0]["title"] == "Original"
    assert out[0]["vote_average"] == 8.0


def test_aggregate_tiebreak_by_vote_then_popularity():
    """Equal frequency -> higher vote_average first; equal vote -> higher popularity first."""
    high_vote = [{"id": 1, "title": "HighVote", "vote_average": 8.0, "popularity": 1}]
    low_vote = [{"id": 2, "title": "LowVote", "vote_average": 4.0, "popularity": 1}]
    high_pop = [{"id": 3, "title": "HighPop", "vote_average": 4.0, "popularity": 100}]

    out = service.aggregate(
        [("movie", high_vote), ("movie", low_vote), ("movie", high_pop)],
        exclude=set(),
    )

    # freq all 1. vote: id1(8) first. Then id2 and id3 both vote 4 -> pop breaks: id3(100) > id2(1).
    assert [r["tmdb_id"] for r in out] == [1, 3, 2]


def test_aggregate_drops_excluded_keys():
    """Keys present in `exclude` never appear in the output."""
    results = [
        {"id": 1, "title": "Owned", "vote_average": 9.0, "popularity": 9},
        {"id": 2, "title": "New", "vote_average": 5.0, "popularity": 5},
    ]

    out = service.aggregate([("movie", results)], exclude={("movie", 1)})

    assert [r["tmdb_id"] for r in out] == [2]


def test_aggregate_movie_and_show_same_id_are_distinct():
    """('movie', 100) and ('show', 100) are different keys; both can appear."""
    movie_list = [{"id": 100, "title": "Movie100", "vote_average": 5.0, "popularity": 5}]
    show_list = [{"id": 100, "name": "Show100", "vote_average": 5.0, "popularity": 5}]

    out = service.aggregate(
        [("movie", movie_list), ("show", show_list)], exclude=set()
    )

    keys = {(r["media_type"], r["tmdb_id"]) for r in out}
    assert keys == {("movie", 100), ("show", 100)}


def test_aggregate_caps_output_at_limit():
    """aggregate returns at most `limit` items."""
    results = [
        {"id": i, "title": f"M{i}", "vote_average": float(i), "popularity": i}
        for i in range(1, 6)
    ]

    out = service.aggregate([("movie", results)], exclude=set(), limit=2)

    assert len(out) == 2


def test_aggregate_normalization_fields():
    """name falls back to title, first_air_date to release_date, library_status is None."""
    show = [
        {
            "id": 7,
            "name": "Only Name",
            "first_air_date": "2026-01-01",
            "vote_average": 6.0,
            "popularity": 3,
        }
    ]

    out = service.aggregate([("show", show)], exclude=set())

    entry = out[0]
    assert entry["title"] == "Only Name"
    assert entry["release_date"] == "2026-01-01"
    assert entry["library_status"] is None
    assert entry["media_type"] == "show"
    assert entry["tmdb_id"] == 7
