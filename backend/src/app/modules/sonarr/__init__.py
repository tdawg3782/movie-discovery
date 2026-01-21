"""Sonarr module."""
from .client import SonarrClient
from .router import router

__all__ = ["SonarrClient", "router"]
