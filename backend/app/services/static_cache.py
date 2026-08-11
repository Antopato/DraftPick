"""DB-backed cache for reduced external static data (see StaticDataCache).

Sync helpers (SQLAlchemy session per call, same style as room_manager
persistence). Callers treat every failure as a cache miss — the cache must
never take the app down.
"""

import json
from datetime import datetime, timezone

from ..db import get_session
from ..models import StaticDataCache


def load_cached(source: str, cache_key: str) -> tuple[dict, datetime] | None:
    session = get_session()
    try:
        row = (
            session.query(StaticDataCache)
            .filter(
                StaticDataCache.source == source,
                StaticDataCache.cache_key == cache_key,
            )
            .first()
        )
        if row is None:
            return None
        return json.loads(row.payload), row.fetched_at
    except Exception:
        return None
    finally:
        session.close()


def store_cached(source: str, cache_key: str, payload: dict) -> None:
    session = get_session()
    try:
        row = (
            session.query(StaticDataCache)
            .filter(
                StaticDataCache.source == source,
                StaticDataCache.cache_key == cache_key,
            )
            .first()
        )
        if row is None:
            row = StaticDataCache(source=source, cache_key=cache_key)
            session.add(row)
        row.payload = json.dumps(payload, separators=(",", ":"))
        row.fetched_at = datetime.now(timezone.utc)
        session.commit()
    except Exception:
        session.rollback()
    finally:
        session.close()
