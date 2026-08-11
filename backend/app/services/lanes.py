"""Champion lane/position + combat-profile catalog from Meraki lolstaticdata.

Data Dragon only exposes class tags (Fighter/Mage/...), never lanes. Meraki's
combined champions file carries a real `positions` array plus the combat
attributes the draft analysis needs (attributeRatings, attackType,
attackRange, adaptiveType), so we fetch it once, reduce it to a slim
per-champion meta map, and cache it in memory and in the DB (StaticDataCache)
so a Render cold start with Meraki down still has data.

The combined file is >10 MB, which is why the backend downloads and reduces it
instead of every client. Failure is non-fatal: lanes degrade to "no lanes" and
the analysis marks its composition section as partial.
"""

import time
from dataclasses import asdict, dataclass, field

import httpx

from .static_cache import load_cached, store_cached

# Combined file, keyed by champion; each value has `key` (= Data Dragon id) and
# `positions`. We map by the inner `key` so keying quirks (e.g. Wukong) don't bite.
CHAMPIONS_URL = (
    "https://cdn.merakianalytics.com/riot/lol/resources/latest/en-US/champions.json"
)
CACHE_TTL_SECONDS = 6 * 3600
CACHE_SOURCE = "meraki_champions"
CACHE_KEY = "latest"

# Meraki enum -> our internal lane codes (frontend translates these to es-ES).
_LANE_MAP = {
    "TOP": "top",
    "JUNGLE": "jungle",
    "MIDDLE": "mid",
    "BOTTOM": "bot",
    "SUPPORT": "support",
}


@dataclass
class ChampionMeta:
    lanes: list[str] = field(default_factory=list)
    attack_type: str | None = None  # 'MELEE' | 'RANGED'
    attack_range: float | None = None
    damage_type: str | None = None  # 'PHYSICAL_DAMAGE' | 'MAGIC_DAMAGE' | 'MIXED_DAMAGE'
    # Riot 0-3 scales: damage, toughness, control, mobility, utility.
    ratings: dict[str, int] = field(default_factory=dict)


def _reduce(data: dict) -> dict[str, dict]:
    meta: dict[str, dict] = {}
    for champ in data.values():
        champion_id = champ.get("key")
        if not champion_id:
            continue
        ratings_raw = champ.get("attributeRatings") or {}
        ratings = {
            k: v
            for k, v in ratings_raw.items()
            if k in ("damage", "toughness", "control", "mobility", "utility")
            and isinstance(v, int)
        }
        attack_range = ((champ.get("stats") or {}).get("attackRange") or {}).get("flat")
        meta[champion_id] = asdict(
            ChampionMeta(
                lanes=[
                    _LANE_MAP[p]
                    for p in champ.get("positions", [])
                    if p in _LANE_MAP
                ],
                attack_type=champ.get("attackType"),
                attack_range=attack_range if isinstance(attack_range, (int, float)) else None,
                damage_type=champ.get("adaptiveType"),
                ratings=ratings,
            )
        )
    return meta


class LaneCatalog:
    def __init__(self) -> None:
        self._meta: dict[str, ChampionMeta] | None = None
        self._fetched_at: float = 0.0
        self._stale: bool = False

    async def get_meta(self) -> tuple[dict[str, ChampionMeta], bool]:
        """Full per-champion meta map plus a stale flag (True when serving a
        DB fallback because the live fetch failed)."""
        if self._meta is not None and time.time() - self._fetched_at < CACHE_TTL_SECONDS:
            return self._meta, self._stale
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                data = (await client.get(CHAMPIONS_URL)).raise_for_status().json()
            reduced = _reduce(data)
            if not reduced:
                raise ValueError("empty meraki reduction")
            store_cached(CACHE_SOURCE, CACHE_KEY, reduced)
            self._meta = {cid: ChampionMeta(**m) for cid, m in reduced.items()}
            self._stale = False
            self._fetched_at = time.time()
        except Exception:
            if self._meta is not None:
                return self._meta, self._stale  # stale memory beats failing
            cached = load_cached(CACHE_SOURCE, CACHE_KEY)
            if cached is not None:
                self._meta = {cid: ChampionMeta(**m) for cid, m in cached[0].items()}
                self._stale = True
                self._fetched_at = time.time()
            else:
                return {}, True
        return self._meta, self._stale

    async def get_lanes(self) -> dict[str, list[str]]:
        meta, _ = await self.get_meta()
        return {cid: m.lanes for cid, m in meta.items() if m.lanes}


lane_catalog = LaneCatalog()
