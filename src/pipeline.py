"""Run the full pipeline: download data, build features, write the leaderboard, Man City squad
table and radar charts.

Usage (from the repo root):  python -m src.pipeline
"""

import unicodedata

import pandas as pd

from src.config import FOCUS_TEAM, MIN_MINUTES_SIMILARITY, OUTPUT_DIR, PROCESSED_DIR, SAMPLE_DIR
from src.data_loader import load_match_data, load_matches
from src.features import FEATURE_COLUMNS, add_per90_features, build_player_table
from src.leaderboard import build_leaderboard
from src.radar import long_format, percentile_table, plot_radar
from src.similarity import SimilarityModel

# Man City players featured in the README examples and radar charts.
EXAMPLE_PLAYERS = ["Kevin De Bruyne", "Sergio Agüero", "Fernandinho"]


def focus_team_table(leaderboard, model):
    """One row per focus-team player in the pool: minutes, position, league rank, closest match."""
    squad = model.pool[model.pool["team"] == FOCUS_TEAM]
    ranks = leaderboard[leaderboard["team"] == FOCUS_TEAM].set_index("display_name")["rank_in_position"]
    rows = []
    for _, player in squad.sort_values("minutes", ascending=False).iterrows():
        match = model.most_similar(player["display_name"], n=1).iloc[0]
        group_size = (leaderboard["position_group"] == player["position_group"]).sum()
        rank = ranks.get(player["display_name"])
        rows.append({
            "player": player["display_name"],
            "position_group": player["position_group"],
            "minutes": player["minutes"],
            "league_rank_in_position": f"{rank} of {group_size}" if rank is not None else "under minutes cut",
            "most_similar_other_club": f"{match['display_name']} ({match['team']})",
            "similarity": match["similarity"],
        })
    return pd.DataFrame(rows)


def main():
    matches = load_matches()
    print(f"Loading {len(matches)} matches...")
    match_data = load_match_data([m["match_id"] for m in matches])

    players = add_per90_features(build_player_table(matches, match_data))
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    players.to_csv(PROCESSED_DIR / "player_features.csv", index=False)
    print(f"Built features for {len(players)} players.")

    # The committed sample is just the similarity pool's features, so the lookup script
    # works straight after cloning without the 1 GB download.
    model = SimilarityModel(players)
    sample_columns = ["player_id", "player_name", "display_name", "team", "matches",
                      "minutes", "main_position", "position_group"] + FEATURE_COLUMNS
    SAMPLE_DIR.mkdir(parents=True, exist_ok=True)
    model.pool[sample_columns].round(4).to_csv(SAMPLE_DIR / "player_features_sample.csv", index=False)
    print(f"Similarity pool: {len(model.pool)} outfield players with {MIN_MINUTES_SIMILARITY}+ minutes.")

    OUTPUT_DIR.mkdir(exist_ok=True)
    leaderboard = build_leaderboard(players)
    leaderboard.to_csv(OUTPUT_DIR / "leaderboard_by_position.csv", index=False)
    print("\nTop 3 per position group:")
    print(leaderboard[leaderboard["rank_in_position"] <= 3].to_string(index=False))

    squad = focus_team_table(leaderboard, model)
    squad.to_csv(OUTPUT_DIR / "man_city_squad.csv", index=False)
    print(f"\n{FOCUS_TEAM} squad (players with {MIN_MINUTES_SIMILARITY}+ minutes):")
    print(squad.to_string(index=False))

    percentiles = percentile_table(model.pool)
    long_format(percentiles).to_csv(OUTPUT_DIR / "radar_percentiles_long.csv", index=False)

    radar_dir = OUTPUT_DIR / "radars"
    radar_dir.mkdir(exist_ok=True)
    for name in EXAMPLE_PLAYERS:
        similar = model.most_similar(name, n=5)
        example = model.pool.loc[model.find_player(name), "display_name"]
        print(f"\nMost similar to {example} (other clubs):")
        print(similar.to_string(index=False))
        ascii_name = unicodedata.normalize("NFKD", example).encode("ascii", "ignore").decode()
        filename = ascii_name.lower().replace(" ", "_") + ".png"
        plot_radar(percentiles, example, similar.loc[0, "display_name"], radar_dir / filename)

    print(f"\nWrote outputs to {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
