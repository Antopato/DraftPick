"""Server-side champion catalog from Riot Data Dragon (static CDN, no API key).

The server needs the champion id list to validate picks/bans and to resolve
random picks on timeout. Cached in memory and refreshed every few hours.
"""

import time

import httpx

VERSIONS_URL = "https://ddragon.leagueoflegends.com/api/versions.json"
CHAMPIONS_URL = (
    "https://ddragon.leagueoflegends.com/cdn/{version}/data/en_US/champion.json"
)
CACHE_TTL_SECONDS = 6 * 3600


class ChampionCatalogError(Exception):
    """User-facing (es-ES) message."""


class ChampionCatalog:
    def __init__(self) -> None:
        self._pool: set[str] | None = None
        self._version: str | None = None
        self._fetched_at: float = 0.0

    async def get_pool(self) -> set[str]:
        if self._pool is not None and time.time() - self._fetched_at < CACHE_TTL_SECONDS:
            return self._pool
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                versions = (await client.get(VERSIONS_URL)).raise_for_status().json()
                version = versions[0]
                data = (
                    (await client.get(CHAMPIONS_URL.format(version=version)))
                    .raise_for_status()
                    .json()
                )
            self._pool = set(data["data"].keys())
            self._version = version
            self._fetched_at = time.time()
        except Exception as exc:
            if self._pool is not None:
                return self._pool  # stale cache beats failing
            raise ChampionCatalogError(
                "No se ha podido cargar la lista de campeones. Inténtalo de nuevo."
            ) from exc
        return self._pool


catalog = ChampionCatalog()
