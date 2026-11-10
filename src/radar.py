"""Radar charts comparing a player with his closest match, plus a long-format CSV for BI tools."""

import matplotlib

matplotlib.use("Agg")  # render to files, no display needed
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from src.config import COMPETITIONS

# A readable subset of the features for the chart. All are percentiles within position group.
RADAR_FEATURES = {
    "np_xg_p90": "npxG",
    "shots_p90": "Shots",
    "key_passes_p90": "Key passes",
    "progressive_passes_p90": "Prog. passes",
    "progressive_carries_p90": "Prog. carries",
    "dribbles_completed_p90": "Dribbles",
    "pressures_p90": "Pressures",
    "tackles_won_p90": "Tackles won",
    "interceptions_p90": "Interceptions",
    "ball_recoveries_p90": "Recoveries",
}


def percentile_table(pool):
    """Percentile rank (0-100) of each radar feature, computed within position group."""
    percentiles = pool.groupby("position_group")[list(RADAR_FEATURES)].rank(pct=True) * 100
    return pd.concat([pool[["display_name", "team", "position_group"]], percentiles.round(1)], axis=1)


def plot_radar(percentiles, player_a, player_b, path):
    """Draw two players' percentile profiles on one radar and save it as a PNG."""
    labels = list(RADAR_FEATURES.values())
    angles = np.linspace(0, 2 * np.pi, len(labels), endpoint=False).tolist()
    angles += angles[:1]  # repeat the first angle to close the polygon

    fig, ax = plt.subplots(figsize=(6.5, 6.5), subplot_kw={"polar": True})
    for name, colour in [(player_a, "#1f5aa6"), (player_b, "#d9822b")]:
        row = percentiles.loc[percentiles["display_name"] == name].iloc[0]
        values = [row[f] for f in RADAR_FEATURES] + [row[list(RADAR_FEATURES)[0]]]
        ax.plot(angles, values, color=colour, linewidth=2, label=f"{name} ({row['team']})")
        ax.fill(angles, values, color=colour, alpha=0.15)

    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(labels, fontsize=9)
    ax.set_ylim(0, 100)
    ax.set_yticks([25, 50, 75])
    ax.set_yticklabels(["25th", "50th", "75th"], fontsize=7, color="grey")
    group = percentiles.loc[percentiles["display_name"] == player_a, "position_group"].iloc[0]
    ax.set_title(f"Percentile among Premier League {group.lower()} players (per 90)", fontsize=11, pad=18)
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.06), ncol=1, frameon=False, fontsize=9)
    competitions = ", ".join(label for _, _, label in COMPETITIONS)
    fig.text(0.5, 0.01, f"Data: StatsBomb Open Data ({competitions})",
             ha="center", fontsize=7, color="grey")
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)


def long_format(percentiles):
    """One row per player and metric, the shape Tableau or Power BI radar templates expect."""
    long = percentiles.melt(id_vars=["display_name", "team", "position_group"],
                            var_name="metric", value_name="percentile")
    long["metric"] = long["metric"].map(RADAR_FEATURES)
    return long
