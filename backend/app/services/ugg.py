"""Matchup winrates from u.gg's static stats JSON (no API key).

stats2.u.gg serves precomputed per-champion matchup files, but its Cloudflare
config rejects non-browser TLS fingerprints (Python clients get 403 even with
browser headers), so the backend never fetches u.gg at runtime. Instead,
scripts/refresh_matchups.py downloads everything with system curl on a dev
machine and writes a reduced snapshot to app/analysis/data/matchups/
{patch}.json.gz, which ships with the repo/deploy. At runtime we load the best
available snapshot; an older-patch snapshot is served flagged as stale, and no
snapshot at all just means the matchup section degrades.

Key codes (undocumented; confirmed empirically with scripts/probe_ugg.py on
patch 16_15, 2026-08-11 — rerun that script to re-verify after a schema change):
- region "12" = world aggregate (largest samples by far)
- rank "8"   = broadest rank aggregate
- roles: "1"=jungle  "2"=support  "3"=bot  "4"=top  "5"=mid
- shape: data[region][rank][role] = [rows, timestamp];
  row = [opponent_id, wins, games, ...deltas] where wins are the file
  champion's wins against that opponent.
"""

import gzip
import json
import time
from dataclasses import dataclass
from pathlib import Path

MATCHUPS_URL = (
    "https://stats2.u.gg/lol/1.5/matchups/{patch}/ranked_solo_5x5/{champ_id}/1.5.0.json"
)
BROWSER_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0 Safari/537.36"
)

REGION_WORLD = "12"
RANK_AGGREGATE = "8"
ROLE_TO_LANE = {"1": "jungle", "2": "support", "3": "bot", "4": "top", "5": "mid"}
# Rows below this many games carry no signal and only bloat the snapshot.
MIN_GAMES = 10

SNAPSHOT_DIR = Path(__file__).resolve().parent.parent / "analysis" / "data" / "matchups"
CACHE_TTL_SECONDS = 6 * 3600

# {lane: {opponent_numeric_id(str): [wins, games]}}
LaneMatchups = dict[str, dict[str, list[int]]]


def reduce_matchup_payload(data: dict) -> LaneMatchups:
    """Reduce one raw u.gg champion file to the world/aggregate bucket only.

    Defensive on purpose: any structural surprise yields an empty/partial map
    rather than an exception, so one odd champion never breaks a refresh.
    """
    reduced: LaneMatchups = {}
    bucket = data.get(REGION_WORLD, {}).get(RANK_AGGREGATE, {})
    if not isinstance(bucket, dict):
        return reduced
    for role, payload in bucket.items():
        lane = ROLE_TO_LANE.get(role)
        if lane is None or not isinstance(payload, list) or not payload:
            continue
        rows = payload[0]
        if not isinstance(rows, list):
            continue
        lane_map: dict[str, list[int]] = {}
        for row in rows:
            if (
                isinstance(row, list)
                and len(row) >= 3
                and all(isinstance(v, int) for v in row[:3])
                and row[2] >= MIN_GAMES
                and 0 <= row[1] <= row[2]
            ):
                lane_map[str(row[0])] = [row[1], row[2]]
        if lane_map:
            reduced[lane] = lane_map
    return reduced


@dataclass
class MatchupData:
    patch: str  # u.gg patch of the snapshot actually served, e.g. "16_15"
    stale: bool  # True when it does not match the requested patch
    champions: dict[str, LaneMatchups]  # numeric id (str) -> lanes


def _patch_sort_key(patch: str) -> tuple[int, int]:
    try:
        major, minor = patch.split("_")
        return int(major), int(minor)
    except ValueError:
        return (0, 0)


class MatchupSnapshotStore:
    """Loads the newest bundled snapshot; in-memory cached with a TTL so a
    redeploy with a fresh snapshot file is picked up without a restart loop."""

    def __init__(self, directory: Path = SNAPSHOT_DIR) -> None:
        self._dir = directory
        self._data: MatchupData | None = None
        self._loaded_patch: str | None = None
        self._loaded_at: float = 0.0

    def get(self, patch: str) -> MatchupData | None:
        fresh = time.time() - self._loaded_at < CACHE_TTL_SECONDS
        if self._data is not None and fresh and self._loaded_patch == patch:
            return self._data
        loaded = self._load_best(patch)
        if loaded is not None:
            self._data = loaded
            self._loaded_patch = patch
            self._loaded_at = time.time()
        return self._data

    def _load_best(self, patch: str) -> MatchupData | None:
        try:
            files = {p.name.removesuffix(".json.gz"): p for p in self._dir.glob("*.json.gz")}
        except OSError:
            return None
        if not files:
            return None
        chosen = patch if patch in files else max(files, key=_patch_sort_key)
        try:
            with gzip.open(files[chosen], "rt", encoding="utf-8") as fh:
                raw = json.load(fh)
            champions = raw["champions"]
            if not isinstance(champions, dict):
                return None
        except (OSError, ValueError, KeyError):
            return None
        return MatchupData(patch=chosen, stale=chosen != patch, champions=champions)


snapshot_store = MatchupSnapshotStore()
