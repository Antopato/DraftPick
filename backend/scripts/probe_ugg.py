"""Dev-only probe for the undocumented u.gg matchups JSON.

The stats2.u.gg matchup files are keyed by numeric region/rank/role codes that
u.gg never documented. This script downloads a few well-known champions and
prints the key structure with opponents resolved to names, so the constants
pinned in app/services/ugg.py can be confirmed empirically after each u.gg
schema change. Never imported by the app.

Usage: python scripts/probe_ugg.py [--save-fixture PATH]
"""

import argparse
import asyncio
import json
import subprocess

import httpx

VERSIONS_URL = "https://ddragon.leagueoflegends.com/api/versions.json"
CHAMPIONS_URL = (
    "https://ddragon.leagueoflegends.com/cdn/{version}/data/en_US/champion.json"
)
MATCHUPS_URL = (
    "https://stats2.u.gg/lol/1.5/matchups/{patch}/ranked_solo_5x5/{champ_id}/1.5.0.json"
)
UA = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/126.0 Safari/537.36"
    )
}

# Champions with unmistakable lane identities, to infer the role code mapping.
PROBES = {"Aatrox": "top", "Jinx": "bot", "Thresh": "support", "LeeSin": "jungle", "Ahri": "mid"}


def to_ugg_patch(version: str) -> str:
    major, minor = version.split(".")[:2]
    return f"{major}_{minor}"


def fetch_via_curl(url: str) -> dict | None:
    """stats2.u.gg 403s Python's TLS fingerprint; system curl with a browser
    User-Agent is served normally, so the dev-side scripts shell out to it."""
    proc = subprocess.run(
        ["curl", "-s", "--fail", "-A", UA["User-Agent"], url],
        capture_output=True,
        timeout=30,
    )
    if proc.returncode != 0:
        return None
    return json.loads(proc.stdout)


async def main(save_fixture: str | None) -> None:
    async with httpx.AsyncClient(timeout=20, headers=UA) as client:
        versions = (await client.get(VERSIONS_URL)).raise_for_status().json()
        version = versions[0]
        patch = to_ugg_patch(version)
        print(f"Data Dragon version: {version}  ->  u.gg patch: {patch}\n")

        champs = (
            (await client.get(CHAMPIONS_URL.format(version=version)))
            .raise_for_status()
            .json()["data"]
        )
        numeric = {cid: int(c["key"]) for cid, c in champs.items()}
        names = {int(c["key"]): cid for cid, c in champs.items()}

        fixture: dict[str, dict] = {}
        for cid, expected_lane in PROBES.items():
            champ_id = numeric[cid]
            url = MATCHUPS_URL.format(patch=patch, champ_id=champ_id)
            data = fetch_via_curl(url)
            if data is None:
                print(f"{cid} ({champ_id}): fetch failed — {url}")
                continue
            fixture[str(champ_id)] = data
            print(f"=== {cid} (id {champ_id}, expected lane: {expected_lane}) ===")
            print(f"  region keys: {sorted(data.keys(), key=int)}")
            for region in sorted(data.keys(), key=int):
                ranks = data[region]
                total_by_rank = {}
                for rank, roles in ranks.items():
                    games = 0
                    for role, bucket in roles.items():
                        rows = bucket[0] if isinstance(bucket, list) else []
                        games += sum(r[2] for r in rows if isinstance(r, list) and len(r) > 2)
                    total_by_rank[rank] = games
                top_ranks = sorted(total_by_rank.items(), key=lambda kv: -kv[1])[:3]
                print(f"  region {region}: rank keys {sorted(ranks.keys(), key=int)}; "
                      f"biggest samples: {top_ranks}")
            # Inspect the globally biggest (region, rank) bucket in detail.
            best = max(
                (
                    (region, rank)
                    for region, ranks in data.items()
                    for rank in ranks
                ),
                key=lambda rr: sum(
                    r[2]
                    for bucket in data[rr[0]][rr[1]].values()
                    for r in (bucket[0] if isinstance(bucket, list) else [])
                    if isinstance(r, list) and len(r) > 2
                ),
            )
            region, rank = best
            print(f"  -> biggest bucket: region={region} rank={rank}")
            for role, bucket in sorted(data[region][rank].items(), key=lambda kv: int(kv[0])):
                rows = bucket[0] if isinstance(bucket, list) else []
                rows = [r for r in rows if isinstance(r, list) and len(r) > 2]
                games = sum(r[2] for r in rows)
                top = sorted(rows, key=lambda r: -r[2])[:4]
                sample = ", ".join(
                    f"{names.get(r[0], r[0])} {r[1]}/{r[2]} ({100 * r[1] / r[2]:.1f}%)"
                    for r in top
                    if r[2]
                )
                print(f"     role {role}: {len(rows)} opponents, {games} games | {sample}")
            print()

        if save_fixture:
            with open(save_fixture, "w", encoding="utf-8") as fh:
                json.dump({"patch": patch, "version": version, "data": fixture}, fh)
            print(f"Fixture saved to {save_fixture}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--save-fixture", default=None)
    asyncio.run(main(parser.parse_args().save_fixture))
