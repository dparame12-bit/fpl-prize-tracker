import pandas as pd
from config import PRIZES, MONTH_GW_MAP
from fpl_api import get_manager_history, current_gw

def league_finisher_prizes(standings: pd.DataFrame) -> pd.DataFrame:
    df = standings.copy()
    df["league_finish_prize"] = df["current_rank"].map(PRIZES["league_finishers"]).fillna(0).astype(int)
    return df[["entry_id", "team_name", "manager_name", "current_rank", "total_points", "gw_points", "league_finish_prize"]]

def _all_gw_rows(standings: pd.DataFrame) -> pd.DataFrame:
    rows = []
    gw_now = current_gw()
    for _, row in standings.iterrows():
        hist = get_manager_history(int(row.entry_id)).get("current", [])
        for h in hist:
            event = int(h["event"])
            if event <= gw_now:
                rows.append({
                    "GW": event,
                    "entry_id": row.entry_id,
                    "team_name": row.team_name,
                    "manager_name": row.manager_name,
                    "points": h.get("points", 0),
                    "total_points": h.get("total_points", 0),
                    "transfers_cost": h.get("event_transfers_cost", 0),
                    "points_on_bench": h.get("points_on_bench", 0),
                })
    return pd.DataFrame(rows)

def gw_winners(standings: pd.DataFrame) -> pd.DataFrame:
    df = _all_gw_rows(standings)
    if df.empty:
        return df
    df["prize"] = df["GW"].map(PRIZES["gw_bonus"]).fillna(PRIZES["gw_normal"]).astype(int)
    return (
        df.sort_values(["GW", "points"], ascending=[True, False])
          .groupby("GW", as_index=False)
          .head(1)
          .reset_index(drop=True)[["GW", "team_name", "manager_name", "points", "prize"]]
    )

def manager_of_month(standings: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for month_no, (month, gws) in enumerate(MONTH_GW_MAP.items(), start=1):
        month_rows = []
        for _, row in standings.iterrows():
            hist = get_manager_history(int(row.entry_id)).get("current", [])
            points = sum(h.get("points", 0) for h in hist if int(h["event"]) in gws)
            played = sum(1 for h in hist if int(h["event"]) in gws)
            if played > 0:
                month_rows.append({
                    "month_order": month_no,
                    "month": month,
                    "team_name": row.team_name,
                    "manager_name": row.manager_name,
                    "month_points": points,
                    "prize": PRIZES["manager_of_month"],
                })
        rows.extend(month_rows)

    df = pd.DataFrame(rows)
    if df.empty:
        return df

    return (
        df.sort_values(["month_order", "month_points"], ascending=[True, False])
          .groupby("month_order", as_index=False)
          .head(1)
          .sort_values("month_order")
          .reset_index(drop=True)[["month", "team_name", "manager_name", "month_points", "prize"]]
    )

def transfer_efficiency(standings: pd.DataFrame) -> pd.DataFrame:
    rows = []
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
        for c in hist.get("chips", []):
            chip = c.get("name")
            gw = int(c.get("event", 0))
            chip_label = {"bboost": "Bench Boost", "3xc": "Triple Captain", "freehit": "Free Hit", "wildcard": "Wildcard"}.get(chip, chip)
            gw_row = next((h for h in hist.get("current", []) if int(h["event"]) == gw), {})
            rows.append({
                "entry_id": row.entry_id,
                "team_name": row.team_name,
                "manager_name": row.manager_name,
                "chip": chip_label,
                "GW": gw,
                "half": "H1" if gw <= 19 else "H2",
                "score": gw_row.get("points", 0),
            })
    return pd.DataFrame(rows)

def chip_awards_live(standings: pd.DataFrame) -> pd.DataFrame:
    usage = chip_usage_awards(standings)
    rows = []
    for chip in ["Bench Boost", "Triple Captain", "Free Hit"]:
        for half in ["H1", "H2"]:
            award = f"Best {chip} {half}"
            if usage.empty:
                rows.append({"award": award, "status": "No usage yet", "team_name": "", "manager_name": "", "GW": "", "score": "", "prize": 250})
                continue
            temp = usage[(usage["chip"] == chip) & (usage["half"] == half)]
            if temp.empty:
                rows.append({"award": award, "status": "No usage yet", "team_name": "", "manager_name": "", "GW": "", "score": "", "prize": 250})
            else:
                w = temp.sort_values("score", ascending=False).iloc[0]
                rows.append({"award": award, "status": "Current Leader", "team_name": w.team_name, "manager_name": w.manager_name, "GW": int(w.GW), "score": int(w.score), "prize": 250})
    return pd.DataFrame(rows)

def prize_summary(standings: pd.DataFrame) -> pd.DataFrame:
    base = standings[["entry_id", "team_name", "manager_name", "current_rank", "total_points"]].copy()
    base["league_finish_prize"] = base["current_rank"].map(PRIZES["league_finishers"]).fillna(0).astype(int)

    gw = gw_winners(standings)
    if not gw.empty:
        base = base.merge(gw.groupby("team_name", as_index=False)["prize"].sum().rename(columns={"prize": "gw_winner_prize"}), on="team_name", how="left")
    else:
        base["gw_winner_prize"] = 0

    mom = manager_of_month(standings)
    if not mom.empty:
        base = base.merge(mom.groupby("team_name", as_index=False)["prize"].sum().rename(columns={"prize": "motm_prize"}), on="team_name", how="left")
    else:
        base["motm_prize"] = 0

    chip_cols = {
        "Best Bench Boost H1": "bb_h1_prize",
        "Best Bench Boost H2": "bb_h2_prize",
        "Best Triple Captain H1": "tc_h1_prize",
        "Best Triple Captain H2": "tc_h2_prize",
        "Best Free Hit H1": "fh_h1_prize",
        "Best Free Hit H2": "fh_h2_prize",
    }
    for col in chip_cols.values():
        base[col] = 0

    chips = chip_awards_live(standings)
    for _, r in chips.iterrows():
        if r["status"] == "Current Leader":
            col = chip_cols.get(r["award"])
            if col:
                base.loc[base["team_name"] == r["team_name"], col] += int(r["prize"])

    te = transfer_efficiency(standings).head(1)
    base["transfer_efficiency_prize"] = 0
    if not te.empty:
        base.loc[base["entry_id"] == te.iloc[0].entry_id, "transfer_efficiency_prize"] = 500

    all_gw = _all_gw_rows(standings)
    base["mid_season_winner_prize"] = 0
    base["most_bench_points_prize"] = 0

    if not all_gw.empty and (all_gw["GW"] == 19).any():
        mid = all_gw[all_gw["GW"] == 19].sort_values("total_points", ascending=False).head(1)
        base.loc[base["entry_id"] == mid.iloc[0].entry_id, "mid_season_winner_prize"] = 500

    if not all_gw.empty:
        bench = all_gw.groupby("entry_id", as_index=False)["points_on_bench"].sum().sort_values("points_on_bench", ascending=False).head(1)
        base.loc[base["entry_id"] == bench.iloc[0].entry_id, "most_bench_points_prize"] = 500

    prize_cols = [c for c in base.columns if "prize" in c]
    for c in prize_cols:
        base[c] = base[c].fillna(0).astype(int)

    base["known_prize_total"] = base[prize_cols].sum(axis=1)
    return base.sort_values(["known_prize_total", "total_points"], ascending=[False, False])
