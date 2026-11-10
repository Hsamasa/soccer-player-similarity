"""Look up the players most similar to a given player.

Examples:
    python similar_players.py "Lionel Messi"
    python similar_players.py "Rodri" --n 10
    python similar_players.py "Bukayo Saka" --any-position
"""

import argparse

import pandas as pd

from src.config import PROCESSED_DIR, SAMPLE_DIR
from src.similarity import SimilarityModel


def load_players():
    """Use the full feature table if the pipeline has been run, otherwise the committed sample."""
    full = PROCESSED_DIR / "player_features.csv"
    return pd.read_csv(full if full.exists() else SAMPLE_DIR / "player_features_sample.csv")


def similar_players(name, n=5, same_position_group=True):
    """Return a DataFrame of the n players most similar to `name`."""
    return SimilarityModel(load_players()).most_similar(name, n=n, same_position_group=same_position_group)


def main():
    parser = argparse.ArgumentParser(description="Find the most similar players by per-90 profile.")
    parser.add_argument("player", help="Player name or nickname, e.g. 'Lionel Messi'")
    parser.add_argument("--n", type=int, default=5, help="How many similar players to return (default 5)")
    parser.add_argument("--any-position", action="store_true",
                        help="Compare against all outfield players, not only the same position group")
    args = parser.parse_args()

    try:
        result = similar_players(args.player, n=args.n, same_position_group=not args.any_position)
    except ValueError as error:
        parser.exit(1, f"{error}\n")
    print(result.to_string(index=False))


if __name__ == "__main__":
    main()
