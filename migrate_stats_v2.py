#!/usr/bin/env python3
import os
import json
import httpx
import re
import asyncio
from collections import defaultdict

# Configuration
API_URL = "https://et-stats.local.maryan.io/api/submit-stats"
API_TOKEN = "super-mega-secret-token"
STATS_DIR = "refs/gamestats"

headers = {
    "Authorization": f"Bearer {API_TOKEN}",
    "Content-Type": "application/json"
}

def parse_filename(filename):
    # Pattern: [game]stats-<matchid>-<date>-<time>-<map>-round-<n>.json
    pattern = re.compile(r"(?:game)?stats-(\d+)-(\d+-\d+-\d+)-(\d+)-(.*)-round-(\d+)\.json")
    m = pattern.match(filename)
    if m:
        mid, date_str, time_str, mapname, round_num = m.groups()
        return {
            "filename": filename,
            "mid": mid,
            "date": date_str,
            "time": time_str,
            "map": mapname,
            "round": int(round_num)
        }
    return None

async def migrate():
    if not os.path.exists(STATS_DIR):
        print(f"Directory {STATS_DIR} not found.")
        return

    files = [f for f in os.listdir(STATS_DIR) if f.endswith(".json")]
    parsed = [parse_filename(f) for f in files if parse_filename(f)]
    parsed.sort(key=lambda x: (x["date"], x["time"]))

    print(f"Found {len(parsed)} files to migrate.")

    # Grouping logic: Collect rounds until a new Round 1 for the same map appears
    match_groups = []
    current_group = []
    
    for item in parsed:
        # If we see a Round 1 and current group isn't empty, it's a new match
        if item["round"] == 1 and current_group:
            # Check if it's the same map or different
            match_groups.append(current_group)
            current_group = [item]
        else:
            current_group.append(item)
    
    if current_group:
        match_groups.append(current_group)

    print(f"Grouped into {len(match_groups)} matches.")

    async with httpx.AsyncClient(verify=False) as client:
        for group in match_groups:
            mapname = group[0]["map"]
            date_str = group[0]["date"]
            
            print(f"Migrating match {mapname} on {date_str} ({len(group)} rounds)...")
            
            payloads = []
            for item in group:
                filepath = os.path.join(STATS_DIR, item["filename"])
                try:
                    with open(filepath, "r") as f:
                        data = json.load(f)
                        if "round_info" in data:
                            # Use the round number from filename to ensure consistency
                            data["round_info"]["round_index"] = item["round"]
                        payloads.append(data)
                except Exception as e:
                    print(f"  Error reading {item['filename']}: {e}")

            if not payloads:
                continue

            try:
                resp = await client.post(API_URL, json=payloads, headers=headers, timeout=60.0)
                if resp.status_code == 200:
                    print(f"  SUCCESS: {resp.json().get('match_id')}")
                else:
                    print(f"  ERROR: HTTP {resp.status_code}: {resp.text}")
            except Exception as e:
                print(f"  FAILED to connect: {e}")

if __name__ == "__main__":
    asyncio.run(migrate())
