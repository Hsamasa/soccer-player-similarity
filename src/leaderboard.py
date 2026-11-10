"""Composite score leaderboard: rank players within each position group.

The composite score is a weighted average of z-scores, where each z-score is computed
against players in the same position group only. The weights below are a judgment call
about what matters for each role, not something learned from data.
"""

import pandas as pd

from src.config import MIN_MINUTES_LEADERBOARD

POSITION_WEIGHTS = {
    "Striker": {
        "np_xg_p90": 0.30, "np_goals_p90": 0.20, "shots_p90": 0.15,
        "key_passes_p90": 0.15, "dribbles_completed_p90": 0.10, "pressures_p90": 0.10,
    },
    "Winger / Attacking Mid": {
        "key_passes_p90": 0.20, "np_xg_p90": 0.20, "progressive_carries_p90": 0.15,
        "dribbles_completed_p90": 0.15, "final_third_passes_p90": 0.15, "assists_p90": 0.15,
    },
    "Central Midfield": {
        "progressive_passes_p90": 0.25, "passes_completed_p90": 0.15, "pass_completion_pct": 0.10,
        "ball_recoveries_p90": 0.15, "tackles_won_p90": 0.10, "interceptions_p90": 0.10,
        "key_passes_p90": 0.15,
    },
    "Full Back": {
        "progressive_passes_p90": 0.15, "progressive_carries_p90": 0.15, "final_third_passes_p90": 0.15,
        "key_passes_p90": 0.10, "tackles_won_p90": 0.15, "interceptions_p90": 0.15,
        "ball_recoveries_p90": 0.15,
    },
    "Center Back": {
        "interceptions_p90": 0.20, "clearances_p90": 0.15, "aerials_won_p90": 0.20,
        "blocks_p90": 0.10, "tackles_won_p90": 0.10, "progressive_passes_p90": 0.15,
        "pass_completion_pct": 0.10,
    },
}


def build_leaderboard(players, min_minutes=MIN_MINUTES_LEADERBOARD):
    """Return a DataFrame ranked by composite score inside each position group."""
    frames = []
    for group, weights in POSITION_WEIGHTS.items():
        subset = players[(players["position_group"] == group) & (players["minutes"] >= min_minutes)].copy()
        if subset.empty:
            continue
        features = list(weights)
        z_scores = (subset[features] - subset[features].mean()) / subset[features].std(ddof=0)
        subset["composite_score"] = sum(z_scores[f] * w for f, w in weights.items()).round(3)
        subset["rank_in_position"] = subset["composite_score"].rank(ascending=False, method="min").astype(int)
        frames.append(subset)

    columns = ["position_group", "rank_in_position", "display_name", "team",
               "matches", "minutes", "composite_score"]
    leaderboard = pd.concat(frames)[columns]
    return leaderboard.sort_values(["position_group", "rank_in_position"]).reset_index(drop=True)
