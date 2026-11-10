"""Download and cache StatsBomb open data (matches, events, lineups).

Data source: StatsBomb Open Data, https://github.com/statsbomb/open-data
Files are cached under data/raw/ so the download only happens once.
"""

import json
import time
from concurrent.futures import ThreadPoolExecutor

import requests

from src.config import COMPETITIONS, RAW_DIR, STATSBOMB_BASE_URL

MAX_ATTEMPTS = 4


def _fetch_json(relative_path):
    """Return parsed JSON for a file in the open-data repo, using the local cache if present."""
    cache_path = RAW_DIR / relative_path
    if cache_path.exists():
        return json.loads(cache_path.read_text(encoding="utf-8"))

    # Large event files occasionally arrive truncated, so retry a few times before giving up.
    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            response = requests.get(f"{STATSBOMB_BASE_URL}/{relative_path}", timeout=60)
            response.raise_for_status()
            data = response.json()
            break
        except (requests.RequestException, ValueError):
            if attempt == MAX_ATTEMPTS:
                raise
            time.sleep(2 * attempt)

    # Only cache after the full file parsed, so a broken download is never saved.
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    cache_path.write_text(response.text, encoding="utf-8")
    return data


def load_matches():
    """Return a list of match dicts for every configured competition, tagged with its label."""
    matches = []
    for competition_id, season_id, label in COMPETITIONS:
        for match in _fetch_json(f"matches/{competition_id}/{season_id}.json"):
            match["competition_label"] = label
            matches.append(match)
    return matches


def load_match_data(match_ids, workers=4):
    """Return {match_id: (events, lineups)} for the given matches, downloading in parallel."""

    def fetch_one(match_id):
        events = _fetch_json(f"events/{match_id}.json")
        lineups = _fetch_json(f"lineups/{match_id}.json")
        return match_id, (events, lineups)

    with ThreadPoolExecutor(max_workers=workers) as pool:
        return dict(pool.map(fetch_one, match_ids))
