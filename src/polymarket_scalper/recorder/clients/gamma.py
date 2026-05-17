from __future__ import annotations

from typing import Any

import httpx


class GammaClient:
    def __init__(self, base_url: str, timeout_seconds: float = 10.0) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds

    async def fetch_markets_by_slug(self, slug: str) -> list[dict[str, Any]]:
        async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
            response = await client.get(
                f"{self.base_url}/markets",
                params={"slug": slug},
            )
            response.raise_for_status()
            return list(response.json())
