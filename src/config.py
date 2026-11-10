"""Project settings: which StatsBomb competitions to load and the minute thresholds."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "data" / "raw"          # cached StatsBomb JSON (git-ignored)
PROCESSED_DIR = ROOT / "data" / "processed"  # full feature table (git-ignored)
SAMPLE_DIR = ROOT / "data" / "sample"    # small CSV committed to the repo
OUTPUT_DIR = ROOT / "outputs"

STATSBOMB_BASE_URL = "https://raw.githubusercontent.com/statsbomb/open-data/master/data"

# (competition_id, season_id, label) from StatsBomb's competitions.json.
# The full 2015/16 Premier League season: all 380 matches are in the open data.
COMPETITIONS = [
    (2, 27, "Premier League 2015/16"),
]

# The club the project focuses on: examples, radar charts and the squad table.
FOCUS_TEAM = "Manchester City"

# Players need this many minutes (10 full matches) to enter the similarity pool.
# Per-90 rates on fewer minutes are mostly noise.
MIN_MINUTES_SIMILARITY = 900

# A stricter cut for the leaderboard (15 full matches), since a ranking invites direct comparison.
MIN_MINUTES_LEADERBOARD = 1350
