"""Tests for the _extract_watch_providers pure helper."""
from app.modules.discovery.router import _extract_watch_providers


def test_picks_region_flatrate_slimmed():
    """Should pick the region's flatrate, slimmed to id/name/logo only."""
    detail = {
        "watch/providers": {
            "results": {
                "US": {
                    "link": "L",
                    "flatrate": [
                        {
                            "provider_id": 8,
                            "provider_name": "Netflix",
                            "logo_path": "/n.jpg",
                            "display_priority": 1,
                        }
                    ],
                }
            }
        }
    }

    result = _extract_watch_providers(detail, "US")

    assert result == {
        "region": "US",
        "link": "L",
        "flatrate": [{"provider_id": 8, "provider_name": "Netflix", "logo_path": "/n.jpg"}],
        "free": [],
    }


def test_merges_free_and_ads_deduped_order_preserved():
    """free = free + ads deduped by provider_id, free entries first."""
    detail = {
        "watch/providers": {
            "results": {
                "US": {
                    "link": "L",
                    "free": [
                        {"provider_id": 538, "provider_name": "Plex", "logo_path": "/p.jpg"},
                        {"provider_id": 613, "provider_name": "Freevee", "logo_path": "/f.jpg"},
                    ],
                    "ads": [
                        {"provider_id": 613, "provider_name": "Freevee", "logo_path": "/f.jpg"},
                        {"provider_id": 73, "provider_name": "Tubi", "logo_path": "/t.jpg"},
                    ],
                }
            }
        }
    }

    result = _extract_watch_providers(detail, "US")

    assert result["free"] == [
        {"provider_id": 538, "provider_name": "Plex", "logo_path": "/p.jpg"},
        {"provider_id": 613, "provider_name": "Freevee", "logo_path": "/f.jpg"},
        {"provider_id": 73, "provider_name": "Tubi", "logo_path": "/t.jpg"},
    ]
    assert result["flatrate"] == []


def test_missing_region_returns_empty_shape():
    """Region not present in results → empty arrays, link None."""
    detail = {"watch/providers": {"results": {"GB": {"link": "L"}}}}

    result = _extract_watch_providers(detail, "US")

    assert result == {"region": "US", "link": None, "flatrate": [], "free": []}


def test_missing_watch_providers_key_returns_empty_shape():
    """No watch/providers key at all → empty shape with region set."""
    detail = {"id": 603, "title": "The Matrix"}

    result = _extract_watch_providers(detail, "DE")

    assert result == {"region": "DE", "link": None, "flatrate": [], "free": []}
