"""Refresh the bundled u.gg matchup snapshot for the current patch.

Run on a dev machine (uses system curl — see app/services/ugg.py for why) and
commit the resulting app/analysis/data/matchups/{patch}.json.gz. Old patches
can be deleted; the runtime store just serves the newest file.

Usage: python scripts/refresh_matchups.py
"""

import asyncio
import gzip
import json
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.services.ugg import (  # noqa: E402
    BROWSER_UA,
    MATCHUPS_URL,
    SNAPSHOT_DIR,
    reduce_matchup_payload,
)

VERSIONS_URL = "https://ddragon.leagueoflegends.com/api/versions.json"
CHAMPIONS_URL = (
    "https://ddragon.leagueoflegends.com/cdn/{version}/data/en_US/champion.json"
)


def fetch_via_curl(url: str) -> dict | None:
    proc = subprocess.run(
        ["curl", "-s", "--fail", "-A", BROWSER_UA, url],
        capture_output=True,
        timeout=30,
    )
    if proc.returncode != 0:
        return None
    try:
        return json.loads(proc.stdout)
    except ValueError:
        return None


async def main() -> None:
    async with httpx.AsyncClient(timeout=20) as client:
        version = (await client.get(VERSIONS_URL)).raise_for_status().json()[0]
        champs = (
            (await client.get(CHAMPIONS_URL.format(version=version)))
            .raise_for_status()
            .json()["data"]
        )
    major, minor = version.split(".")[:2]
    patch = f"{major}_{minor}"
    numeric_ids = sorted(int(c["key"]) for c in champs.values())
    print(f"Patch {patch} ({version}), {len(numeric_ids)} champions")

    champions: dict[str, dict] = {}
    failures: list[int] = []
    for i, champ_id in enumerate(numeric_ids, 1):
        data = fetch_via_curl(MATCHUPS_URL.format(patch=patch, champ_id=champ_id))
        reduced = reduce_matchup_payload(data) if data else {}
        if reduced:
            champions[str(champ_id)] = reduced
        else:
            failures.append(champ_id)
        if i % 25 == 0:
            print(f"  {i}/{len(numeric_ids)} downloaded")
        time.sleep(0.1)  # be polite to the CDN

    SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)
    out = SNAPSHOT_DIR / f"{patch}.json.gz"
    payload = {
        "patch": patch,
        "version": version,
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "champions": champions,
    }
    with gzip.open(out, "wt", encoding="utf-8") as fh:
        json.dump(payload, fh, separators=(",", ":"))
    size_kb = out.stat().st_size // 1024
    print(f"Wrote {out} ({size_kb} KB, {len(champions)} champions)")
    if failures:
        print(f"WARNING: no data for numeric ids: {failures}")


if __name__ == "__main__":
    asyncio.run(main())
