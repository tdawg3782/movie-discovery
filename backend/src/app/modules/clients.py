"""Shared external-client factory.

Holds the process-wide singletons/caches for the outbound HTTP clients (TMDB,
Radarr, Sonarr) so their httpx connection pools are reused across requests.
Credentials are resolved DB-first (via ``get_setting``) with ``.env`` fallback,
so a settings change takes effect without a restart:

- ``TMDBClient`` reads ``self.api_key`` at call time, so the singleton's key is
  simply refreshed in place and the pool is kept.
- ``BaseArrClient`` bakes ``X-Api-Key`` into the pool headers, so a credential
  change requires building a new client and closing the previous pool.

All clients are closed once at application shutdown via ``close_all_clients``.

The ``TMDBClient`` import + singleton and the ``RadarrClient``/``SonarrClient``
imports are all deferred to the bottom of the module (after the factory
functions are defined) to break the import cycle: the discovery/radarr/sonarr
router packages re-export the factories from here, so importing their client
submodules would otherwise re-enter this module before the factory names exist.
``from __future__ import annotations`` keeps the typed globals from evaluating
those names before the deferred imports run.
"""
from __future__ import annotations

from app.config import get_setting, settings

# Cached *arr clients; rebuilt only when their resolved credentials change.
_radarr_client: RadarrClient | None = None
_sonarr_client: SonarrClient | None = None


def get_tmdb_client() -> TMDBClient:
    """Return the shared TMDB client, refreshing its api_key from settings (DB-first)."""
    tmdb_client.api_key = get_setting("tmdb_api_key") or ""
    return tmdb_client


async def get_radarr_client() -> RadarrClient:
    """Return a Radarr client built from DB-first credentials, reusing the pool when unchanged."""
    global _radarr_client
    url = get_setting("radarr_url") or settings.radarr_url
    api_key = get_setting("radarr_api_key") or ""

    cached = _radarr_client
    if cached is not None and cached.url == url.rstrip("/") and cached.api_key == api_key:
        return cached

    if cached is not None:
        await cached.close()

    _radarr_client = RadarrClient(url=url, api_key=api_key)
    return _radarr_client


async def get_sonarr_client() -> SonarrClient:
    """Return a Sonarr client built from DB-first credentials, reusing the pool when unchanged."""
    global _sonarr_client
    url = get_setting("sonarr_url") or settings.sonarr_url
    api_key = get_setting("sonarr_api_key") or ""

    cached = _sonarr_client
    if cached is not None and cached.url == url.rstrip("/") and cached.api_key == api_key:
        return cached

    if cached is not None:
        await cached.close()

    _sonarr_client = SonarrClient(url=url, api_key=api_key)
    return _sonarr_client


async def close_all_clients() -> None:
    """Close every shared client pool. Called once at application shutdown."""
    global _radarr_client, _sonarr_client
    await tmdb_client.close()
    if _radarr_client is not None:
        await _radarr_client.close()
        _radarr_client = None
    if _sonarr_client is not None:
        await _sonarr_client.close()
        _sonarr_client = None


# Deferred to break the clients <-> router import cycle (see module docstring).
from app.modules.discovery.tmdb_client import TMDBClient  # noqa: E402
from app.modules.radarr.client import RadarrClient  # noqa: E402
from app.modules.sonarr.client import SonarrClient  # noqa: E402

# Process-wide singleton: api_key is refreshed in place; the pool persists.
tmdb_client: TMDBClient = TMDBClient(api_key="")
