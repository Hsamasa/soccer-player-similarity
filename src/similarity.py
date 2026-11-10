"""Find comparable players with cosine similarity on standardized per-90 features."""

import unicodedata

import numpy as np
import pandas as pd
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.preprocessing import StandardScaler

from src.config import MIN_MINUTES_SIMILARITY
from src.features import FEATURE_COLUMNS


def _normalize(text):
    """Lowercase and strip accents so 'mbappe' matches 'Kylian Mbappé Lottin'."""
    text = unicodedata.normalize("NFKD", str(text))
    return "".join(c for c in text if not unicodedata.combining(c)).lower().strip()


class SimilarityModel:
    """Holds the scaled feature matrix for the eligible player pool.

    Goalkeepers are excluded: none of the outfield features describe goalkeeping.
    """

    def __init__(self, players, min_minutes=MIN_MINUTES_SIMILARITY):
        pool = players[(players["minutes"] >= min_minutes) & (players["position_group"] != "Goalkeeper")]
        self.pool = pool.reset_index(drop=True)
        # z-score each feature so high-volume stats (passes) don't drown out rare ones (goals).
        self.scaler = StandardScaler()
        self.matrix = self.scaler.fit_transform(self.pool[FEATURE_COLUMNS])
        self.similarity = cosine_similarity(self.matrix)

    def find_player(self, name):
        """Return the pool row index for a name, matching full name or nickname, accents ignored."""
        query = _normalize(name)
        full = self.pool["player_name"].map(_normalize)
        short = self.pool["display_name"].map(_normalize)

        exact = self.pool.index[(full == query) | (short == query)]
        if len(exact) == 1:
            return exact[0]
        partial = self.pool.index[full.str.contains(query, regex=False) | short.str.contains(query, regex=False)]
        if len(partial) == 1:
            return partial[0]
        if len(partial) == 0:
            raise ValueError(f"No player matching '{name}' with at least the minimum minutes.")
        options = ", ".join(self.pool.loc[partial, "display_name"].head(10))
        raise ValueError(f"'{name}' matches several players: {options}. Be more specific.")

    def most_similar(self, name, n=5, same_position_group=True, exclude_teammates=True):
        """Return the n players most similar to `name`, highest cosine similarity first.

        Teammates are excluded by default: the scouting question is who at OTHER clubs plays
        like this player, and teammates share a system that makes their numbers look alike.
        """
        index = self.find_player(name)
        scores = pd.Series(self.similarity[index], index=self.pool.index)
        candidates = self.pool.index != index
        if same_position_group:
            candidates &= self.pool["position_group"] == self.pool.loc[index, "position_group"]
        if exclude_teammates:
            candidates &= self.pool["team"] != self.pool.loc[index, "team"]
        top = scores[candidates].sort_values(ascending=False).head(n)

        result = self.pool.loc[top.index, ["display_name", "team", "position_group", "minutes"]].copy()
        result.insert(0, "similarity", np.round(top.values, 3))
        return result.reset_index(drop=True)
