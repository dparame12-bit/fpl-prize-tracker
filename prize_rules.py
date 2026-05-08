import pandas as pd
import numpy as np
from config import PRIZES, MONTH_GW_MAP
from fpl_api import get_manager_history, get_manager_picks, current_gw

def league_finisher_prizes(standings: pd.DataFrame) -> pd.DataFrame:
    df = standings.copy()
    df["league_finish_prize"] = df["current_rank"].map(PRIZES["league_finishers"]).fillna(0).astype(int)
    return df[["entry_id", "team_name", "manager_name", "current_rank", "total_points", "league_finish_prize"]]

def gw_winners(standings: pd.DataFrame) -> pd.DataFrame:
    rows = []
    gw_now = current_gw()

    for _, row in standings.iterrows():
        hist = get_manager_history(int(row.entry_id)).get("current", [])
        for h in hist:
            event = int(h["event"])
            if event <= gw_now:
                prize = PRIZES["gw_bonus"].get(event, PRIZES["gw_normal"])
                rows.append({
                    "GW": event,
                    "entry_id": row.entry_id,
                    "team_name": row.team_name,
                    "manager_name": row.manager_name,
                    "points": h.get("points", 0),
                    "prize": prize
                })

    df = pd.DataFrame(rows)
    if df.empty:
        return df

    winners = (
        df.sort_values(["GW", "points"], ascending=[True, False])
          .groupby("GW", as_index=False)
          .head(1)
          .reset_index(drop=True)
    )
    return winners

def manager_of_month(standings: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for month, gws in MONTH_GW_MAP.items():
        month_rows = []
        for _, row in standings.iterrows():
            hist = get_manager_history(int(row.entry_id)).get("current", [])
            points = sum(h.get("points", 0) for h in hist if int(h["event"]) in gws)
            played = sum(1 for h in hist if int(h["event"]) in gws)
            if played > 0:
                month_rows.append({
                    "month": month,
                    "entry_id": row.entry_id,
                    "team_name": row.team_name,
                    "manager_name": row.manager_name,
                    "month_points": points,
                    "prize": PRIZES["manager_of_month"],
                })
        if month_rows:
            rows.extend(month_rows)

    df = pd.DataFrame(rows)
    if df.empty:
        return df

    return (
        df.sort_values(["month", "month_points"], ascending=[True, False])
          .groupby("month", as_index=False)
          .head(1)
          .reset_index(drop=True)
    )

def transfer_efficiency(standings: pd.DataFrame) -> pd.DataFrame:
    rows = []
    gw_now = current_gw()
    for _, row in standings.iterrows():
        hist = get_manager_history(int(row.entry_id)).get("current", [])
        total_points = sum(h.get("points", 0) for h in hist)
        penalty_points = sum(abs(h.get("event_transfers_cost", 0)) for h in hist)
        hits = penalty_points // 4
        denominator = 38 + hits
        efficiency = (total_points - penalty_points) / denominator if denominator else 0
        rows.append({
            "entry_id": row.entry_id,
            "team_name": row.team_name,
            "manager_name": row.manager_name,
            "total_points": total_points,
            "penalty_points": penalty_points,
            "hits": hits,
            "transfer_efficiency": round(efficiency, 2),
        })
    return pd.DataFrame(rows).sort_values("transfer_efficiency", ascending=False)

def chip_usage_awards(standings: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for _, row in standings.iterrows():
        hist = get_manager_history(int(row.entry_id))
        chips = hist.get("chips", [])
        for c in chips:
            chip = c.get("name")
            gw = int(c.get("event", 0))
            chip_label = {
                "bboost": "Bench Boost",
                "3xc": "Triple Captain",
                "freehit": "Free Hit",
                "wildcard": "Wildcard",
            }.get(chip, chip)

            # We use the full GW score as initial MVP impact.
            # For TC/BB exact impact, we can refine with picks data in v2.
            gw_row = next((h for h in hist.get("current", []) if int(h["event"]) == gw), {})
            score = gw_row.get("points", None)
            half = "H1" if gw <= 19 else "H2"

            rows.append({
                "entry_id": row.entry_id,
                "team_name": row.team_name,
                "manager_name": row.manager_name,
                "chip": chip_label,
                "GW": gw,
                "half": half,
                "score": score,
            })
    return pd.DataFrame(rows)

def prize_summary(standings: pd.DataFrame) -> pd.DataFrame:
    base = standings[["entry_id", "team_name", "manager_name", "current_rank", "total_points"]].copy()
    base["league_finish_prize"] = base["current_rank"].map(PRIZES["league_finishers"]).fillna(0).astype(int)

    gw = gw_winners(standings)
    if not gw.empty:
        gw_sum = gw.groupby("entry_id", as_index=False)["prize"].sum().rename(columns={"prize": "gw_winner_prize"})
        base = base.merge(gw_sum, on="entry_id", how="left")
    else:
        base["gw_winner_prize"] = 0

    mom = manager_of_month(standings)
    if not mom.empty:
        mom_sum = mom.groupby("entry_id", as_index=False)["prize"].sum().rename(columns={"prize": "motm_prize"})
        base = base.merge(mom_sum, on="entry_id", how="left")
    else:
        base["motm_prize"] = 0

    for c in ["gw_winner_prize", "motm_prize"]:
        if c not in base.columns:
            base[c] = 0
        base[c] = base[c].fillna(0).astype(int)

    base["known_prize_total"] = base["league_finish_prize"] + base["gw_winner_prize"] + base["motm_prize"]
    return base.sort_values(["known_prize_total", "total_points"], ascending=[False, False])
