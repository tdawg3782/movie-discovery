"""Shared base client for *arr APIs (Radarr, Sonarr)."""
import httpx
from typing import Any


class BaseArrClient:
    """Base HTTP client for Radarr/Sonarr with persistent connection reuse."""

    def __init__(self, url: str, api_key: str):
        self.url = url.rstrip("/")
        self.api_key = api_key
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                timeout=httpx.Timeout(30.0),
                headers={"X-Api-Key": self.api_key},
            )
        return self._client

    async def _get(self, endpoint: str, params: dict | None = None) -> Any:
        client = await self._get_client()
        response = await client.get(
            f"{self.url}/api/v3{endpoint}",
            params=params,
        )
        response.raise_for_status()
        return response.json()

    async def _post(self, endpoint: str, data: dict) -> Any:
        client = await self._get_client()
        response = await client.post(
            f"{self.url}/api/v3{endpoint}",
            json=data,
        )
        response.raise_for_status()
        return response.json()

    async def _put(self, endpoint: str, data: dict) -> Any:
        client = await self._get_client()
        response = await client.put(
            f"{self.url}/api/v3{endpoint}",
            json=data,
        )
        response.raise_for_status()
        return response.json()

    async def close(self) -> None:
        if self._client is not None and not self._client.is_closed:
            await self._client.aclose()
            self._client = None
