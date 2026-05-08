import os
import pandas as pd
from fpl_api import get_manager_history, current_gw

DRAW_PATH = "data/wtl_cup_seed.csv"

def _get_points(entry_id: int, start_gw: int, end_gw: int) -> int:
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

def _pair_teams(teams: pd.DataFrame, round_name: str, start_gw: int, end_gw: int) -> pd.DataFrame:
    rows = []
    temp = teams.reset_index(drop=True).copy()
    for i in range(0, len(temp), 2):
        a = temp.iloc[i]
        b = temp.iloc[i + 1] if i + 1 < len(temp) else None
        a_points = _get_points(a.entry_id, start_gw, end_gw)
        if b is None:
            rows.append({"round": round_name, "GW window": f"GW{start_gw}–GW{end_gw}", "team_a": a.team_name, "team_b": "BYE", "fixture": f"{a.team_name} vs BYE", "team_a_points": a_points, "team_b_points": "", "winner": a.team_name, "status": "Bye", "winner_entry_id": a.entry_id, "winner_manager": a.manager_name})
            continue
        b_points = _get_points(b.entry_id, start_gw, end_gw)
        gw_now = current_gw()
        if gw_now < start_gw:
            winner, winner_entry_id, winner_manager, status = "", None, "", "Upcoming"
        elif gw_now < end_gw:
            winner, winner_entry_id, winner_manager, status = "", None, "", "In progress"
        elif a_points >= b_points:
            winner, winner_entry_id, winner_manager, status = a.team_name, a.entry_id, a.manager_name, "Completed"
        else:
            winner, winner_entry_id, winner_manager, status = b.team_name, b.entry_id, b.manager_name, "Completed"
        rows.append({"round": round_name, "GW window": f"GW{start_gw}–GW{end_gw}", "team_a": a.team_name, "team_b": b.team_name, "fixture": f"{a.team_name} vs {b.team_name}", "team_a_points": a_points, "team_b_points": b_points, "winner": winner, "status": status, "winner_entry_id": winner_entry_id, "winner_manager": winner_manager})
    return pd.DataFrame(rows)

def _winners(df):
    return df[df["winner_entry_id"].notna()].rename(columns={"winner_entry_id": "entry_id", "winner": "team_name", "winner_manager": "manager_name"})[["entry_id", "team_name", "manager_name"]]

def build_cup_bracket_live(standings: pd.DataFrame) -> pd.DataFrame:
    seed_df = _load_or_create_seed(standings)
    r1_teams = seed_df.iloc[:8].copy().reset_index(drop=True)
    bye_teams = seed_df.iloc[8:].copy().reset_index(drop=True)[["entry_id", "team_name", "manager_name"]]

    all_rounds = []
    r1 = _pair_teams(r1_teams, "Round 1", 19, 20)
    all_rounds.append(r1)
    r1_winners = _winners(r1)

    # Note: with 20 teams and 12 byes, the next stage mathematically has 16 teams = 8 fixtures.
    # We label it Quarter Final because this is the first full knockout round after byes.
    qf_pool = pd.concat([bye_teams, r1_winners], ignore_index=True)
    if len(qf_pool) == 16:
        qf = _pair_teams(qf_pool, "Quarter Final", 21, 22)
        all_rounds.append(qf)
    else:
        return pd.concat(all_rounds, ignore_index=True)

    qf_winners = _winners(qf)
    if len(qf_winners) == 8:
        sf = _pair_teams(qf_winners, "Semi Final", 23, 24)
        all_rounds.append(sf)
    else:
        return pd.concat(all_rounds, ignore_index=True)

    sf_winners = _winners(sf)
    if len(sf_winners) == 4:
        final = _pair_teams(sf_winners, "Final", 25, 26)
        all_rounds.append(final)

    out = pd.concat(all_rounds, ignore_index=True)
    return out[["round", "GW window", "team_a", "team_b", "fixture", "team_a_points", "team_b_points", "winner", "status"]]
