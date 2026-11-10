"""Turn StatsBomb event and lineup data into one row of per-90 features per player.

StatsBomb pitch coordinates: x runs 0 to 120 toward the opponent's goal, y runs 0 to 80.
Every team's events are recorded attacking left to right, so a larger x is always
closer to the goal that player's team is attacking.
"""

from collections import defaultdict

import pandas as pd

# Clock minute at which each period starts in StatsBomb's match clock.
# Period 5 (penalty shootout) is ignored everywhere: it is not open play.
PERIOD_START_MINUTE = {1: 0, 2: 45, 3: 90, 4: 105}

# Map StatsBomb's 25 detailed positions to six broader groups.
POSITION_GROUPS = {
    "Goalkeeper": "Goalkeeper",
    "Right Back": "Full Back", "Left Back": "Full Back",
    "Right Wing Back": "Full Back", "Left Wing Back": "Full Back",
    "Right Center Back": "Center Back", "Left Center Back": "Center Back", "Center Back": "Center Back",
    "Right Defensive Midfield": "Central Midfield", "Left Defensive Midfield": "Central Midfield",
    "Center Defensive Midfield": "Central Midfield", "Right Center Midfield": "Central Midfield",
    "Left Center Midfield": "Central Midfield", "Center Midfield": "Central Midfield",
    "Right Midfield": "Winger / Attacking Mid", "Left Midfield": "Winger / Attacking Mid",
    "Right Wing": "Winger / Attacking Mid", "Left Wing": "Winger / Attacking Mid",
    "Right Attacking Midfield": "Winger / Attacking Mid", "Left Attacking Midfield": "Winger / Attacking Mid",
    "Center Attacking Midfield": "Winger / Attacking Mid",
    "Right Center Forward": "Striker", "Left Center Forward": "Striker",
    "Center Forward": "Striker", "Secondary Striker": "Striker",
}

# Set pieces are excluded from "progressive" and "final third" pass counts so those
# features describe open-play passing, not who takes corners and goal kicks.
SET_PIECE_PASS_TYPES = {"Corner", "Free Kick", "Throw-in", "Goal Kick", "Kick Off"}

# Raw counts collected per player. Each becomes a per-90 feature.
COUNT_COLUMNS = [
    "np_goals", "np_xg", "shots", "assists", "key_passes",
    "passes_completed", "passes_attempted", "progressive_passes", "final_third_passes",
    "progressive_carries", "dribbles_completed", "pressures",
    "tackles_won", "interceptions", "ball_recoveries", "clearances", "blocks", "aerials_won",
]


def _clock_minutes(clock):
    """'67:12' -> 67.2"""
    minutes, seconds = clock.split(":")
    return int(minutes) + int(seconds) / 60


def _period_lengths(events):
    """Return {period: minutes played in that period}, read from the 'Half End' events."""
    ends = defaultdict(float)
    for event in events:
        if event["type"]["name"] == "Half End" and event["period"] in PERIOD_START_MINUTE:
            ends[event["period"]] = max(ends[event["period"]], event["minute"] + event["second"] / 60)
    return {period: end - PERIOD_START_MINUTE[period] for period, end in ends.items()}


def _elapsed(clock_minutes, period, period_lengths):
    """Convert a clock time within a period to real minutes played since kick-off.

    StatsBomb's clock restarts at 45:00 for the second half, so first-half stoppage time
    overlaps the second half's clock. Summing each completed period's actual length fixes that.
    """
    before = sum(period_lengths.get(p, 0) for p in PERIOD_START_MINUTE if p < period)
    return before + (clock_minutes - PERIOD_START_MINUTE[period])


def minutes_and_positions(lineups, events):
    """Return {player_id: {"name", "team", "minutes", "position_minutes": {position: minutes}}}."""
    period_lengths = _period_lengths(events)
    match_length = sum(period_lengths.values())
    players = {}

    for team in lineups:
        for player in team["lineup"]:
            position_minutes = defaultdict(float)
            for spell in player["positions"]:
                if spell["from_period"] not in PERIOD_START_MINUTE:
                    continue  # appeared only in the penalty shootout
                start = _elapsed(_clock_minutes(spell["from"]), spell["from_period"], period_lengths)
                if spell["to"] is None or spell["to_period"] not in PERIOD_START_MINUTE:
                    end = match_length  # still on the pitch at the final whistle
                else:
                    end = _elapsed(_clock_minutes(spell["to"]), spell["to_period"], period_lengths)
                position_minutes[spell["position"]] += max(end - start, 0)

            if position_minutes:
                players[player["player_id"]] = {
                    "name": player["player_name"],
                    "nickname": player.get("player_nickname") or player["player_name"],
                    "team": team["team_name"],
                    "minutes": sum(position_minutes.values()),
                    "position_minutes": dict(position_minutes),
                }
    return players


def _is_completed(event, key):
    # StatsBomb leaves out the "outcome" field on successful passes and carries.
    return "outcome" not in event.get(key, {})


def count_events(events):
    """Return {player_id: {count_column: value}} for one match."""
    counts = defaultdict(lambda: dict.fromkeys(COUNT_COLUMNS, 0.0))

    for event in events:
        if "player" not in event or event["period"] not in PERIOD_START_MINUTE:
            continue
        row = counts[event["player"]["id"]]
        kind = event["type"]["name"]

        # Aerial wins are flagged on several event types (passes, shots, clearances, ...).
        if any(isinstance(v, dict) and v.get("aerial_won") for v in event.values()):
            row["aerials_won"] += 1

        if kind == "Shot":
            shot = event["shot"]
            if shot["type"]["name"] == "Penalty":
                continue
            row["shots"] += 1
            row["np_xg"] += shot.get("statsbomb_xg", 0)
            if shot["outcome"]["name"] == "Goal":
                row["np_goals"] += 1

        elif kind == "Pass":
            pass_ = event["pass"]
            open_play = pass_.get("type", {}).get("name") not in SET_PIECE_PASS_TYPES
            row["passes_attempted"] += 1
            if pass_.get("goal_assist"):
                row["assists"] += 1
            if pass_.get("shot_assist") or pass_.get("goal_assist"):
                row["key_passes"] += 1
            if not _is_completed(event, "pass"):
                continue
            row["passes_completed"] += 1
            start_x, end_x = event["location"][0], pass_["end_location"][0]
            if open_play and end_x - start_x >= 10 and end_x >= 60:
                row["progressive_passes"] += 1
            if open_play and start_x < 80 <= end_x:
                row["final_third_passes"] += 1

        elif kind == "Carry":
            start_x, end_x = event["location"][0], event["carry"]["end_location"][0]
            if end_x - start_x >= 10 and end_x >= 60:
                row["progressive_carries"] += 1

        elif kind == "Dribble":
            if event["dribble"]["outcome"]["name"] == "Complete":
                row["dribbles_completed"] += 1

        elif kind == "Pressure":
            row["pressures"] += 1

        elif kind == "Duel":
            duel = event["duel"]
            if duel["type"]["name"] == "Tackle" and duel.get("outcome", {}).get("name") in {
                "Won", "Success", "Success In Play", "Success Out"}:
                row["tackles_won"] += 1

        elif kind == "Interception":
            if event["interception"]["outcome"]["name"] in {"Won", "Success", "Success In Play", "Success Out"}:
                row["interceptions"] += 1

        elif kind == "Ball Recovery":
            if not event.get("ball_recovery", {}).get("recovery_failure"):
                row["ball_recoveries"] += 1

        elif kind == "Clearance":
            row["clearances"] += 1

        elif kind == "Block":
            row["blocks"] += 1

    return counts


def build_player_table(matches, match_data):
    """Aggregate every match into one row per player with totals, minutes and position."""
    totals = defaultdict(lambda: dict.fromkeys(COUNT_COLUMNS, 0.0))
    info = {}

    for match in matches:
        events, lineups = match_data[match["match_id"]]
        played = minutes_and_positions(lineups, events)
        counts = count_events(events)

        for player_id, details in played.items():
            entry = info.setdefault(player_id, {
                "player_id": player_id, "player_name": details["name"], "display_name": details["nickname"],
                "team_minutes": defaultdict(float),
                "minutes": 0.0, "matches": 0, "position_minutes": defaultdict(float),
                "competitions": set(),
            })
            entry["minutes"] += details["minutes"]
            entry["team_minutes"][details["team"]] += details["minutes"]
            entry["matches"] += 1
            entry["competitions"].add(match["competition_label"])
            for position, minutes in details["position_minutes"].items():
                entry["position_minutes"][position] += minutes
            for column, value in counts.get(player_id, {}).items():
                totals[player_id][column] += value

    rows = []
    for player_id, entry in info.items():
        # Pick the position GROUP with the most minutes first. Picking the single most-played
        # detailed position would mislabel a midfielder whose minutes are split across
        # "Left/Center/Right Defensive Midfield" if he once played one position elsewhere longer.
        group_minutes = defaultdict(float)
        for position, minutes in entry["position_minutes"].items():
            group_minutes[POSITION_GROUPS.get(position, "Other")] += minutes
        position_group = max(group_minutes, key=group_minutes.get)
        main_position = max(
            (p for p in entry["position_minutes"] if POSITION_GROUPS.get(p, "Other") == position_group),
            key=entry["position_minutes"].get,
        )
        rows.append({
            "player_id": player_id,
            "player_name": entry["player_name"],
            "display_name": entry["display_name"],
            # A player who moved clubs mid-season is listed under the club he played most for.
            "team": max(entry["team_minutes"], key=entry["team_minutes"].get),
            "competitions": "; ".join(sorted(entry["competitions"])),
            "matches": entry["matches"],
            "minutes": round(entry["minutes"], 1),
            "main_position": main_position,
            "position_group": position_group,
            **totals[player_id],
        })
    return pd.DataFrame(rows)


# The features used for similarity. All are per 90 minutes except pass_completion_pct.
FEATURE_COLUMNS = [
    "np_goals_p90", "np_xg_p90", "shots_p90", "assists_p90", "key_passes_p90",
    "passes_completed_p90", "pass_completion_pct", "progressive_passes_p90",
    "final_third_passes_p90", "progressive_carries_p90", "dribbles_completed_p90",
    "pressures_p90", "tackles_won_p90", "interceptions_p90", "ball_recoveries_p90",
    "clearances_p90", "blocks_p90", "aerials_won_p90",
]


def add_per90_features(players):
    """Add per-90 versions of every count, plus pass completion percentage."""
    players = players.copy()
    per90_factor = 90 / players["minutes"]
    for column in COUNT_COLUMNS:
        if column != "passes_attempted":
            players[f"{column}_p90"] = players[column] * per90_factor
    players["pass_completion_pct"] = (
        100 * players["passes_completed"] / players["passes_attempted"].where(players["passes_attempted"] > 0)
    ).fillna(0)
    return players
