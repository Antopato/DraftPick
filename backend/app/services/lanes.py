"""Champion lane/position catalog from Meraki lolstaticdata (static CDN, no key).

Data Dragon only exposes class tags (Fighter/Mage/...), never lanes. Meraki's
combined champions file carries a real `positions` array (TOP/JUNGLE/MIDDLE/
BOTTOM/SUPPORT) per champion, so we fetch it once, reduce it to a slim
{championId: [lanes]} map (a few KB), and cache it in memory.

The combined file is >10 MB, which is why the backend downloads and reduces it
instead of every client. Failure is non-fatal: the lane filter simply degrades
to "no lanes" and never blocks a draft.
"""

import time

import httpx

# Combined file, keyed by champion; each value has `key` (= Data Dragon id) and
# `positions`. We map by the inner `key` so keying quirks (e.g. Wukong) don't bite.
CHAMPIONS_URL = (
    "https://cdn.merakianalytics.com/riot/lol/resources/latest/en-US/champions.json"
)
CACHE_TTL_SECONDS = 6 * 3600

# Meraki enum -> our internal lane codes (frontend translates these to es-ES).
_LANE_MAP = {
    "TOP": "top",
    "JUNGLE": "jungle",
    "MIDDLE": "mid",
    "BOTTOM": "bot",
    "SUPPORT": "support",
}


class LaneCatalog:
    def __init__(self) -> None:
        self._lanes: dict[str, list[str]] | None = None
        self._fetched_at: float = 0.0

    async def get_lanes(self) -> dict[str, list[str]]:
        if self._lanes is not None and time.time() - self._fetched_at < CACHE_TTL_SECONDS:
            return self._lanes
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                data = (await client.get(CHAMPIONS_URL)).raise_for_status().json()
            lanes: dict[str, list[str]] = {}
            for champ in data.values():
                champion_id = champ.get("key")
                if not champion_id:
                    continue
                mapped = [
                    _LANE_MAP[p]
                    for p in champ.get("positions", [])
                    if p in _LANE_MAP
                ]
                if mapped:
                    lanes[champion_id] = mapped
            self._lanes = lanes
            self._fetched_at = time.time()
        except Exception:
            # Stale cache beats failing; otherwise degrade to an empty map so the
            # filter just shows every champion under every lane.
            return self._lanes if self._lanes is not None else {}
        return self._lanes


lane_catalog = LaneCatalog()
