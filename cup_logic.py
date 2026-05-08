import os
import pandas as pd
from fpl_api import get_manager_history, current_gw

DRAW_PATH = "data/wtl_cup_seed.csv"

ROUND_CONFIG = [
    ("Round 1", 19, 20),
    ("Quarter Final", 21, 22),
    ("Semi Final", 23, 24),
    ("Final", 25, 26),
]

def _get_points(entry_id: int, start_gw: int, end_gw: int) -> int:
    hist = get_manager_history(int(entry_id)).get("current", [])
    return sum(h.get("points", 0) for h in hist if start_gw <= int(h["event"]) <= end_gw)

def _load_or_create_seed(standings: pd.DataFrame, seed: int = 199171) -> pd.DataFrame:
    if os.path.exists(DRAW_PATH):
        return pd.read_csv(DRAW_PATH)

    teams = standings[["entry_id", "team_name", "manager_name"]].copy()
    shuffled = teams.sample(frac=1, random_state=seed).reset_index(drop=True)
    shuffled["draw_seed"] = range(1, len(shuffled) + 1)
    shuffled.to_csv(DRAW_PATH, index=False)
    return shuffled

def _pair_teams(teams: pd.DataFrame, round_name: str, start_gw: int, end_gw: int) -> pd.DataFrame:
    rows = []
    temp = teams.reset_index(drop=True).copy()

    for i in range(0, len(temp), 2):
        a = temp.iloc[i]
        b = temp.iloc[i + 1] if i + 1 < len(temp) else None

        a_points = _get_points(a.entry_id, start_gw, end_gw)
        if b is None:
            rows.append({
                "round": round_name,
                "GW window": f"GW{start_gw}–GW{end_gw}",
                "fixture": f"{a.team_name} vs BYE",
                "team_a_points": a_points,
                "team_b_points": "",
                "winner": a.team_name,
                "status": "Bye",
                "winner_entry_id": a.entry_id,
                "winner_manager": a.manager_name,
            })
            continue

        b_points = _get_points(b.entry_id, start_gw, end_gw)
        gw_now = current_gw()

        if gw_now < start_gw:
            winner = ""
            winner_entry_id = None
            winner_manager = ""
            status = "Upcoming"
        elif gw_now < end_gw:
            winner = ""
            winner_entry_id = None
            winner_manager = ""
            status = "In progress"
        elif a_points >= b_points:
            winner = a.team_name
            winner_entry_id = a.entry_id
            winner_manager = a.manager_name
            status = "Completed"
        else:
            winner = b.team_name
            winner_entry_id = b.entry_id
            winner_manager = b.manager_name
            status = "Completed"

        rows.append({
            "round": round_name,
            "GW window": f"GW{start_gw}–GW{end_gw}",
            "fixture": f"{a.team_name} vs {b.team_name}",
            "team_a_points": a_points,
            "team_b_points": b_points,
            "winner": winner,
            "status": status,
            "winner_entry_id": winner_entry_id,
            "winner_manager": winner_manager,
        })

    return pd.DataFrame(rows)

def build_cup_bracket_live(standings: pd.DataFrame) -> pd.DataFrame:
    seed_df = _load_or_create_seed(standings)
    active = seed_df.copy()
    all_rounds = []

    for round_name, start_gw, end_gw in ROUND_CONFIG:
        matches = _pair_teams(active, round_name, start_gw, end_gw)
        all_rounds.append(matches)

        completed = matches[matches["winner_entry_id"].notna()].copy()
        if completed.empty:
            break

        active = completed.rename(
            columns={
                "winner_entry_id": "entry_id",
                "winner": "team_name",
                "winner_manager": "manager_name",
            }
        )[["entry_id", "team_name", "manager_name"]]

        if len(active) <= 1:
            break

    out = pd.concat(all_rounds, ignore_index=True) if all_rounds else pd.DataFrame()
    if out.empty:
        return out

    return out[["round", "GW window", "fixture", "team_a_points", "team_b_points", "winner", "status"]]
