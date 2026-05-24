import os
import pandas as pd
from fpl_api import get_manager_history, current_gw

DRAW_PATH = "data/wtl_cup_seed.csv"

ROUND_WINDOWS = {
    "R32": (19, 20),
    "R16": (21, 22),
    "Quarter Final": (23, 24),
    "Semi Final": (25, 26),
    "Final": (27, 28),
}

def _get_points(entry_id, start_gw: int, end_gw: int) -> int:
    if entry_id in [None, "", "BYE"] or pd.isna(entry_id):
        return 0
    hist = get_manager_history(int(entry_id)).get("current", [])
    return sum(h.get("points", 0) for h in hist if start_gw <= int(h["event"]) <= end_gw)

def _load_or_create_seed(standings: pd.DataFrame, seed: int = 199171) -> pd.DataFrame:
    if os.path.exists(DRAW_PATH):
        seed_df = pd.read_csv(DRAW_PATH)
        if len(seed_df) == 20:
            return seed_df

    teams = standings[["entry_id", "team_name", "manager_name"]].copy()
    shuffled = teams.sample(frac=1, random_state=seed).reset_index(drop=True)
    shuffled["draw_seed"] = range(1, len(shuffled) + 1)
    shuffled.to_csv(DRAW_PATH, index=False)
    return shuffled

def _make_match(round_name, match_no, start_gw, end_gw, a, b):
    gw_now = current_gw()

    a_is_bye = str(a.get("team_name", "")).upper() == "BYE"
    b_is_bye = str(b.get("team_name", "")).upper() == "BYE"

    a_points = _get_points(a.get("entry_id"), start_gw, end_gw)
    b_points = _get_points(b.get("entry_id"), start_gw, end_gw)

    if a_is_bye and not b_is_bye:
        winner, winner_entry_id, winner_manager, status = b["team_name"], b["entry_id"], b["manager_name"], "Bye"
    elif b_is_bye and not a_is_bye:
        winner, winner_entry_id, winner_manager, status = a["team_name"], a["entry_id"], a["manager_name"], "Bye"
    elif gw_now < start_gw:
        winner, winner_entry_id, winner_manager, status = "", None, "", "Upcoming"
    elif gw_now < end_gw:
        winner, winner_entry_id, winner_manager, status = "", None, "", "In progress"
    elif a_points >= b_points:
        winner, winner_entry_id, winner_manager, status = a["team_name"], a["entry_id"], a["manager_name"], "Completed"
    else:
        winner, winner_entry_id, winner_manager, status = b["team_name"], b["entry_id"], b["manager_name"], "Completed"

    return {
        "round": round_name,
        "match": f"{round_name} - Game {match_no}",
        "GW window": f"GW{start_gw}–GW{end_gw}",
        "team_a": a["team_name"],
        "team_b": b["team_name"],
        "fixture": f"{a['team_name']} vs {b['team_name']}",
        "team_a_points": "-" if a_is_bye else a_points,
        "team_b_points": "-" if b_is_bye else b_points,
        "winner": winner,
        "status": status,
        "winner_entry_id": winner_entry_id,
        "winner_manager": winner_manager,
    }

def _winners(matches: pd.DataFrame) -> pd.DataFrame:
    completed = matches[matches["winner_entry_id"].notna()].copy()
    if completed.empty:
        return pd.DataFrame(columns=["entry_id", "team_name", "manager_name"])
    return completed.rename(
        columns={
            "winner_entry_id": "entry_id",
            "winner": "team_name",
            "winner_manager": "manager_name",
        }
    )[["entry_id", "team_name", "manager_name"]]

def _pair_round(teams: pd.DataFrame, round_name: str) -> pd.DataFrame:
    start_gw, end_gw = ROUND_WINDOWS[round_name]
    rows = []
    temp = teams.reset_index(drop=True).copy()

    for i in range(0, len(temp), 2):
        a = temp.iloc[i].to_dict()
        b = temp.iloc[i + 1].to_dict()
        rows.append(_make_match(round_name, (i // 2) + 1, start_gw, end_gw, a, b))

    return pd.DataFrame(rows)

def build_cup_bracket_live(standings: pd.DataFrame) -> pd.DataFrame:
    seed_df = _load_or_create_seed(standings)

    bye_row = {"entry_id": None, "team_name": "BYE", "manager_name": ""}

    # 32-slot bracket from your image:
    # R32 has 16 games = 12 teams vs BYE + 4 real fixtures.
    bye_teams = seed_df.iloc[:12][["entry_id", "team_name", "manager_name"]].to_dict("records")
    playing_teams = seed_df.iloc[12:][["entry_id", "team_name", "manager_name"]].to_dict("records")

    r32_slots = []
    for team in bye_teams:
        r32_slots.append(team)
        r32_slots.append(bye_row.copy())
    for team in playing_teams:
        r32_slots.append(team)

    rounds = []
    r32 = _pair_round(pd.DataFrame(r32_slots), "R32")
    rounds.append(r32)

    r16_teams = _winners(r32)
    if len(r16_teams) != 16:
        return pd.concat(rounds, ignore_index=True)

    r16 = _pair_round(r16_teams, "R16")
    rounds.append(r16)

    qf_teams = _winners(r16)
    if len(qf_teams) != 8:
        return pd.concat(rounds, ignore_index=True)

    qf = _pair_round(qf_teams, "Quarter Final")
    rounds.append(qf)

    sf_teams = _winners(qf)
    if len(sf_teams) != 4:
        return pd.concat(rounds, ignore_index=True)

    sf = _pair_round(sf_teams, "Semi Final")
    rounds.append(sf)

    final_teams = _winners(sf)
    if len(final_teams) != 2:
        return pd.concat(rounds, ignore_index=True)

    final = _pair_round(final_teams, "Final")
    rounds.append(final)

    out = pd.concat(rounds, ignore_index=True)
    return out[["round", "match", "GW window", "team_a", "team_b", "fixture", "team_a_points", "team_b_points", "winner", "status"]]
