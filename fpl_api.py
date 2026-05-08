import os
import random
import pandas as pd

DRAW_PATH = "data/wtl_cup_draw.csv"

def generate_or_load_draw(standings: pd.DataFrame, seed: int = 199171) -> pd.DataFrame:
    if os.path.exists(DRAW_PATH):
        return pd.read_csv(DRAW_PATH)

    teams = standings[["entry_id", "team_name", "manager_name"]].copy()
    random.seed(seed)
    shuffled = teams.sample(frac=1, random_state=seed).reset_index(drop=True)

    # 20 participants: first 8 play preliminary round, 12 get byes into R16.
    prelim = shuffled.iloc[:8].reset_index(drop=True)
    byes = shuffled.iloc[8:].reset_index(drop=True)

    rows = []
    match_no = 1
    for i in range(0, 8, 2):
        a = prelim.iloc[i]
        b = prelim.iloc[i + 1]
        rows.append({
            "round": "Preliminary",
            "match": f"P{match_no}",
            "GW_start": 19,
            "GW_end": 20,
            "team_a": a.team_name,
            "manager_a": a.manager_name,
            "entry_a": a.entry_id,
            "team_b": b.team_name,
            "manager_b": b.manager_name,
            "entry_b": b.entry_id,
        })
        match_no += 1

    for i, row in byes.iterrows():
        rows.append({
            "round": "Bye to R16",
            "match": f"B{i+1}",
            "GW_start": 19,
            "GW_end": 20,
            "team_a": row.team_name,
            "manager_a": row.manager_name,
            "entry_a": row.entry_id,
            "team_b": "BYE",
            "manager_b": "",
            "entry_b": None,
        })

    df = pd.DataFrame(rows)
    df.to_csv(DRAW_PATH, index=False)
    return df
