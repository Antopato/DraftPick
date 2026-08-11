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


def to_ugg_patch(version: str) -> str:
    """Data Dragon version to u.gg patch label: '16.15.1' -> '16_15'."""
    major, minor = version.split(".")[:2]
    return f"{major}_{minor}"


class ChampionCatalog:
    def __init__(self) -> None:
        self._pool: set[str] | None = None
        self._numeric_ids: dict[str, int] | None = None
        self._tags: dict[str, list[str]] | None = None
        self._version: str | None = None
        self._fetched_at: float = 0.0

    async def get_pool(self) -> set[str]:
        await self._refresh()
        return self._pool

    async def get_numeric_ids(self) -> dict[str, int]:
        """Data Dragon id -> Riot numeric key (e.g. 'Aatrox' -> 266)."""
        await self._refresh()
        return self._numeric_ids

    async def get_version(self) -> str:
        await self._refresh()
        return self._version

    async def get_tags(self) -> dict[str, list[str]]:
        """Data Dragon id -> class tags (e.g. ['Fighter', 'Tank'])."""
        await self._refresh()
        return self._tags

    async def _refresh(self) -> None:
        if self._pool is not None and time.time() - self._fetched_at < CACHE_TTL_SECONDS:
            return
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
            self._numeric_ids = {
                cid: int(champ["key"]) for cid, champ in data["data"].items()
            }
            self._tags = {
                cid: list(champ.get("tags", [])) for cid, champ in data["data"].items()
            }
            self._version = version
            self._fetched_at = time.time()
        except Exception as exc:
            if self._pool is not None:
                return  # stale cache beats failing
            raise ChampionCatalogError(
                "No se ha podido cargar la lista de campeones. Inténtalo de nuevo."
            ) from exc


catalog = ChampionCatalog()
