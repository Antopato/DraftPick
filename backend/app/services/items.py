"""Legendary item costs from Meraki lolstaticdata, for power-spike timing.

The spike heuristic only needs "how expensive is a typical completed damage
item", so the reduction keeps just legendary items with their total gold and a
coarse AD/AP/OTHER kind derived from their stats. Cached in memory + DB like
the champion meta (see lanes.py).
"""

import time

import httpx

from .static_cache import load_cached, store_cached

ITEMS_URL = "https://cdn.merakianalytics.com/riot/lol/resources/latest/en-US/items.json"
CACHE_TTL_SECONDS = 6 * 3600
CACHE_SOURCE = "meraki_items"
CACHE_KEY = "latest"


def _reduce(data: dict) -> list[dict]:
    reduced: list[dict] = []
    for item in data.values():
        if item.get("removed") or "LEGENDARY" not in (item.get("rank") or []):
            continue
        shop = item.get("shop") or {}
        total = (shop.get("prices") or {}).get("total")
        if not isinstance(total, int) or total <= 0 or not shop.get("purchasable", True):
            continue
        stats = item.get("stats") or {}

        def _has(stat: str) -> bool:
            value = stats.get(stat)
            return bool(value) and any(bool(v) for v in value.values())

        if _has("attackDamage") or _has("attackSpeed") or _has("criticalStrikeChance"):
            kind = "AD"
        elif _has("abilityPower"):
            kind = "AP"
        else:
            kind = "OTHER"
        reduced.append({"name": item.get("name", ""), "total": total, "kind": kind})
    return reduced


class ItemCatalog:
    def __init__(self) -> None:
        self._items: list[dict] | None = None
        self._fetched_at: float = 0.0
        self._stale: bool = False

    async def get_legendary_items(self) -> tuple[list[dict], bool]:
        if self._items is not None and time.time() - self._fetched_at < CACHE_TTL_SECONDS:
            return self._items, self._stale
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                data = (await client.get(ITEMS_URL)).raise_for_status().json()
            reduced = _reduce(data)
            if not reduced:
                raise ValueError("empty meraki items reduction")
            store_cached(CACHE_SOURCE, CACHE_KEY, {"items": reduced})
            self._items = reduced
            self._stale = False
            self._fetched_at = time.time()
        except Exception:
            if self._items is not None:
                return self._items, self._stale
            cached = load_cached(CACHE_SOURCE, CACHE_KEY)
            if cached is not None:
                self._items = cached[0].get("items", [])
                self._stale = True
                self._fetched_at = time.time()
            else:
                return [], True
        return self._items, self._stale


item_catalog = ItemCatalog()
