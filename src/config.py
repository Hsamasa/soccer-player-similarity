"""Project settings: which StatsBomb competitions to load and the minute thresholds."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "data" / "raw"          # cached StatsBomb JSON (git-ignored)
PROCESSED_DIR = ROOT / "data" / "processed"  # full feature table (git-ignored)
SAMPLE_DIR = ROOT / "data" / "sample"    # small CSV committed to the repo
OUTPUT_DIR = ROOT / "outputs"

STATSBOMB_BASE_URL = "https://raw.githubusercontent.com/statsbomb/open-data/master/data"

# (competition_id, season_id, label) from StatsBomb's competitions.json.
# Three men's international tournaments from 2022 to 2024, each with every match released.
COMPETITIONS = [
    (43, 106, "FIFA World Cup 2022"),
    (55, 282, "UEFA Euro 2024"),
    (223, 282, "Copa America 2024"),
]

# Players need this many minutes (summed across all three tournaments) to enter
# the similarity pool. Per-90 rates on fewer minutes are mostly noise.
MIN_MINUTES_SIMILARITY = 180

# A stricter cut for the leaderboard (four full matches), since a ranking invites direct comparison.
MIN_MINUTES_LEADERBOARD = 360
