import pandas as pd
from config import PRIZES, MONTH_GW_MAP
from fpl_api import get_manager_history, get_manager_picks, get_event_live, current_gw
from cup_logic import build_cup_bracket_live


def _element_points(event_id: int) -> dict:
    live = get_event_live(event_id)
    return {int(e['id']): e.get('stats', {}).get('total_points', 0) for e in live.get('elements', [])}


def league_finisher_prizes(standings: pd.DataFrame) -> pd.DataFrame:
    df = standings.copy()
    df['league_finish_prize'] = df['current_rank'].map(PRIZES['league_finishers']).fillna(0).astype(int)
    return df[['entry_id', 'team_name', 'manager_name', 'current_rank', 'total_points', 'gw_points', 'league_finish_prize']]


def _all_gw_rows(standings: pd.DataFrame) -> pd.DataFrame:
    rows = []
    gw_now = current_gw()
    for _, row in standings.iterrows():
        hist = get_manager_history(int(row.entry_id)).get('current', [])
        for h in hist:
            event = int(h['event'])
            if event <= gw_now:
                rows.append({
                    'GW': event,
                    'entry_id': row.entry_id,
                    'team_name': row.team_name,
                    'manager_name': row.manager_name,
                    'points': h.get('points', 0),
                    'cumulative_points': h.get('total_points', 0),
                    'transfers_cost': h.get('event_transfers_cost', 0),
                    'points_on_bench': h.get('points_on_bench', 0),
                })
    return pd.DataFrame(rows)


def standings_history(standings: pd.DataFrame) -> pd.DataFrame:
    df = _all_gw_rows(standings)
    if df.empty:
        return df
    df['rank'] = df.groupby('GW')['cumulative_points'].rank(method='min', ascending=False).astype(int)
    return df.sort_values(['GW', 'rank'])


def gw_winners(standings: pd.DataFrame) -> pd.DataFrame:
    df = _all_gw_rows(standings)
    if df.empty:
        return df
    df['prize'] = df['GW'].map(PRIZES['gw_bonus']).fillna(PRIZES['gw_normal']).astype(int)
    return df.sort_values(['GW', 'points'], ascending=[True, False]).groupby('GW', as_index=False).head(1).reset_index(drop=True)[['GW', 'team_name', 'manager_name', 'points', 'prize']]


def manager_of_month(standings: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for month_no, (month, gws) in enumerate(MONTH_GW_MAP.items(), start=1):
        for _, row in standings.iterrows():
            hist = get_manager_history(int(row.entry_id)).get('current', [])
            points = sum(h.get('points', 0) for h in hist if int(h['event']) in gws)
            played = sum(1 for h in hist if int(h['event']) in gws)
            if played > 0:
                rows.append({'month_order': month_no, 'month': month, 'team_name': row.team_name, 'manager_name': row.manager_name, 'month_points': points, 'prize': PRIZES['manager_of_month']})
    df = pd.DataFrame(rows)
    if df.empty:
        return df
    return df.sort_values(['month_order', 'month_points'], ascending=[True, False]).groupby('month_order', as_index=False).head(1).sort_values('month_order').reset_index(drop=True)[['month', 'team_name', 'manager_name', 'month_points', 'prize']]


def transfer_efficiency(standings: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for _, row in standings.iterrows():
        hist = get_manager_history(int(row.entry_id)).get('current', [])
        total_points = sum(h.get('points', 0) for h in hist)
        penalty_points = sum(abs(h.get('event_transfers_cost', 0)) for h in hist)
        hits = penalty_points // 4
        denominator = 38 + hits
        efficiency = (total_points - penalty_points) / denominator if denominator else 0
        rows.append({'entry_id': row.entry_id, 'team_name': row.team_name, 'manager_name': row.manager_name, 'total_points': total_points, 'penalty_points': penalty_points, 'hits': hits, 'transfer_efficiency': round(efficiency, 2)})
    return pd.DataFrame(rows).sort_values('transfer_efficiency', ascending=False)


def chip_usage_awards(standings: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for _, row in standings.iterrows():
        hist = get_manager_history(int(row.entry_id))
        for c in hist.get('chips', []):
            chip = c.get('name')
            gw = int(c.get('event', 0))
            chip_label = {'bboost': 'Bench Boost', '3xc': 'Triple Captain', 'freehit': 'Free Hit', 'wildcard': 'Wildcard'}.get(chip, chip)
            gw_row = next((h for h in hist.get('current', []) if int(h['event']) == gw), {})
            rows.append({'entry_id': row.entry_id, 'team_name': row.team_name, 'manager_name': row.manager_name, 'chip_code': chip, 'chip': chip_label, 'GW': gw, 'half': 'H1' if gw <= 19 else 'H2', 'score': gw_row.get('points', 0), 'bench_points': gw_row.get('points_on_bench', 0)})
    return pd.DataFrame(rows)


def chip_awards_live(standings: pd.DataFrame) -> pd.DataFrame:
    usage = chip_usage_awards(standings)
    rows = []
    for chip in ['Bench Boost', 'Triple Captain', 'Free Hit']:
        for half in ['H1', 'H2']:
            award = f'Best {chip} {half}'
            if usage.empty:
                rows.append({'award': award, 'status': 'No usage yet', 'team_name': '', 'manager_name': '', 'GW': '', 'score': '', 'prize': 250})
                continue
            temp = usage[(usage['chip'] == chip) & (usage['half'] == half)]
            if temp.empty:
                rows.append({'award': award, 'status': 'No usage yet', 'team_name': '', 'manager_name': '', 'GW': '', 'score': '', 'prize': 250})
            else:
                w = temp.sort_values('score', ascending=False).iloc[0]
                rows.append({'award': award, 'status': 'Current Leader', 'team_name': w.team_name, 'manager_name': w.manager_name, 'GW': int(w.GW), 'score': int(w.score), 'prize': 250})
    return pd.DataFrame(rows)


def captain_points_table(standings: pd.DataFrame) -> pd.DataFrame:
    rows = []
    gw_now = current_gw()
    for _, row in standings.iterrows():
        total_captain_points = 0
        for gw in range(1, gw_now + 1):
            try:
                picks = get_manager_picks(int(row.entry_id), gw).get('picks', [])
                pts_map = _element_points(gw)
                captain = next((p for p in picks if p.get('is_captain')), None)
                if captain:
                    total_captain_points += pts_map.get(int(captain['element']), 0) * int(captain.get('multiplier', 0))
            except Exception:
                continue
        rows.append({'entry_id': row.entry_id, 'team_name': row.team_name, 'manager_name': row.manager_name, 'captain_points': total_captain_points})
    return pd.DataFrame(rows).sort_values('captain_points', ascending=False)


def highest_gw_without_chip(standings: pd.DataFrame) -> pd.DataFrame:
    rows = []
    usage = chip_usage_awards(standings)
    excluded = {}
    if not usage.empty:
        for _, r in usage.iterrows():
            if r['chip'] in ['Bench Boost', 'Triple Captain', 'Free Hit', 'Wildcard']:
                excluded.setdefault(int(r.entry_id), set()).add(int(r.GW))
    for _, row in standings.iterrows():
        hist = get_manager_history(int(row.entry_id)).get('current', [])
        valid = [h for h in hist if int(h['event']) not in excluded.get(int(row.entry_id), set())]
        if valid:
            best = max(valid, key=lambda x: x.get('points', 0))
            rows.append({'entry_id': row.entry_id, 'team_name': row.team_name, 'manager_name': row.manager_name, 'GW': int(best['event']), 'points': best.get('points', 0)})
    return pd.DataFrame(rows).sort_values('points', ascending=False)


def biggest_climb_table(standings: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for _, row in standings.iterrows():
        hist = get_manager_history(int(row.entry_id)).get('current', [])
        h1 = sum(h.get('points', 0) for h in hist if 1 <= int(h['event']) <= 19)
        h2 = sum(h.get('points', 0) for h in hist if 20 <= int(h['event']) <= 38)
        rows.append({'entry_id': row.entry_id, 'team_name': row.team_name, 'manager_name': row.manager_name, 'gw1_19_points': h1, 'gw20_38_points': h2, 'climb_score': h2 - h1})
    return pd.DataFrame(rows).sort_values('climb_score', ascending=False)


def worst_chip_usage_table(standings: pd.DataFrame) -> pd.DataFrame:
    df = ctrl_z_breakdown_table(standings)
    if df.empty:
        return df
    return df[df["qualifies_for_ctrl_z"]].sort_values("impact", ascending=True).reset_index(drop=True)

def wooden_spoon_table(standings: pd.DataFrame) -> pd.DataFrame:
    usage = chip_usage_awards(standings)
    rows = []
    for _, row in standings.iterrows():
        hist = get_manager_history(int(row.entry_id)).get('current', [])
        transfer_gws = {int(h['event']) for h in hist if h.get('event_transfers', 0) > 0}
        chip_gws = set() if usage.empty else set(usage[usage['entry_id'] == row.entry_id]['GW'].astype(int).tolist())
        active_gws = len(transfer_gws.union(chip_gws))
        rows.append({'entry_id': row.entry_id, 'team_name': row.team_name, 'manager_name': row.manager_name, 'total_points': row.total_points, 'active_gws': active_gws, 'eligible': active_gws >= 25})
    df = pd.DataFrame(rows)
    eligible = df[df['eligible']]
    if eligible.empty:
        eligible = df.copy()
    return eligible.sort_values('total_points', ascending=True)


def wtl_cup_winner_table(standings: pd.DataFrame) -> pd.DataFrame:
    try:
        bracket = build_cup_bracket_live(standings)
        final = bracket[(bracket['round'] == 'Final') & (bracket['status'].isin(['Completed', 'Bye']))]
        if final.empty:
            return pd.DataFrame()
        winner = final.iloc[0]['winner']
        row = standings[standings['team_name'] == winner].head(1)
        if row.empty:
            return pd.DataFrame()
        return pd.DataFrame([{'entry_id': row.iloc[0].entry_id, 'team_name': row.iloc[0].team_name, 'manager_name': row.iloc[0].manager_name, 'prize': PRIZES['wtl_cup']}])
    except Exception:
        return pd.DataFrame()


def prize_summary(standings: pd.DataFrame) -> pd.DataFrame:
    base = standings[["entry_id", "team_name", "manager_name", "current_rank", "total_points"]].copy()
    base["league_finish_prize"] = base["current_rank"].map(PRIZES["league_finishers"]).fillna(0)

    gw = gw_winners(standings)
    if not gw.empty:
        base = base.merge(
            gw.groupby("team_name", as_index=False)["prize"].sum().rename(columns={"prize": "gw_winner_prize"}),
            on="team_name",
            how="left",
        )
    else:
        base["gw_winner_prize"] = 0

    mom = manager_of_month(standings)
    if not mom.empty:
        base = base.merge(
            mom.groupby("team_name", as_index=False)["prize"].sum().rename(columns={"prize": "motm_prize"}),
            on="team_name",
            how="left",
        )
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
        if r.get("status") == "Current Leader":
            col = chip_cols.get(r["award"])
            if col:
                base.loc[base["team_name"] == r["team_name"], col] += float(r["prize"])

    base["wtl_cup_prize"] = 0
    cup = wtl_cup_winner_table(standings)
    if not cup.empty:
        base.loc[base["entry_id"] == cup.iloc[0].entry_id, "wtl_cup_prize"] = PRIZES["wtl_cup"]

    base["transfer_efficiency_prize"] = 0
    te = transfer_efficiency(standings).head(1)
    if not te.empty:
        base.loc[base["entry_id"] == te.iloc[0].entry_id, "transfer_efficiency_prize"] = 500

    base["mid_season_winner_prize"] = 0
    mid_table = mid_season_table(standings)
    if not mid_table.empty:
        for _, r in mid_table[mid_table["is_winner"]].iterrows():
            base.loc[base["entry_id"] == r.entry_id, "mid_season_winner_prize"] = r.mid_season_prize

    base["most_bench_points_prize"] = 0
    bench = bench_points_table(standings).head(1)
    if not bench.empty:
        base.loc[base["entry_id"] == bench.iloc[0].entry_id, "most_bench_points_prize"] = 500

    base["biggest_climb_prize"] = 0
    bc = biggest_climb_table(standings).head(1)
    if not bc.empty:
        base.loc[base["entry_id"] == bc.iloc[0].entry_id, "biggest_climb_prize"] = 500

    base["most_captain_points_prize"] = 0
    cp = captain_points_table(standings).head(1)
    if not cp.empty:
        base.loc[base["entry_id"] == cp.iloc[0].entry_id, "most_captain_points_prize"] = 500

    base["highest_gw_without_chip_prize"] = 0
    hg = highest_gw_without_chip(standings).head(1)
    if not hg.empty:
        base.loc[base["entry_id"] == hg.iloc[0].entry_id, "highest_gw_without_chip_prize"] = 500

    base["ctrl_z_award_prize"] = 0
    wz = worst_chip_usage_table(standings)
    if not wz.empty:
        base.loc[base["entry_id"] == wz.iloc[0].entry_id, "ctrl_z_award_prize"] = 250

    base["transfer_tactician_prize"] = 0
    tt = transfer_tactician_table(standings).head(1)
    if not tt.empty:
        base.loc[base["entry_id"] == tt.iloc[0].entry_id, "transfer_tactician_prize"] = 500

    base["wooden_spoon_prize"] = 0
    ws = wooden_spoon_table(standings).head(1)
    if not ws.empty:
        base.loc[base["entry_id"] == ws.iloc[0].entry_id, "wooden_spoon_prize"] = 250

    prize_cols = [c for c in base.columns if "prize" in c]
    for c in prize_cols:
        base[c] = base[c].fillna(0)

    base["known_prize_total"] = base[prize_cols].sum(axis=1)
    return base.sort_values(["known_prize_total", "total_points"], ascending=[False, False])


def mid_season_table(standings: pd.DataFrame) -> pd.DataFrame:
    all_gw = _all_gw_rows(standings)
    if all_gw.empty or not (all_gw["GW"] == 19).any():
        return pd.DataFrame()

    df = (
        all_gw[all_gw["GW"] == 19]
        .rename(columns={"cumulative_points": "total_points_gw19"})
        .sort_values("total_points_gw19", ascending=False)
        [["entry_id", "team_name", "manager_name", "total_points_gw19"]]
        .reset_index(drop=True)
    )

    top_score = df["total_points_gw19"].max()
    tied_winners = df[df["total_points_gw19"] == top_score]
    split_prize = round(500 / len(tied_winners), 2) if len(tied_winners) else 0

    df["is_winner"] = df["total_points_gw19"] == top_score
    df["mid_season_prize"] = df["is_winner"].map(lambda x: split_prize if x else 0)

    return df

def bench_points_table(standings: pd.DataFrame) -> pd.DataFrame:
    all_gw = _all_gw_rows(standings)
    if all_gw.empty:
        return pd.DataFrame()
    return (
        all_gw.groupby(["entry_id", "team_name", "manager_name"], as_index=False)["points_on_bench"]
        .sum()
        .rename(columns={"points_on_bench": "bench_points"})
        .sort_values("bench_points", ascending=False)
        .reset_index(drop=True)
    )


def _chip_impact(entry_id: int, gw: int, chip_code: str, gw_score: int = 0, bench_points_fallback: int = 0) -> int:
    """
    Impact logic:
    - TC: captain's final points * 3, using event-live player total and picks multiplier.
    - FH: full GW score.
    - BB: sum of bench players' points from event-live data.
    """
    try:
        if chip_code == "freehit":
            return int(gw_score or 0)

        picks = get_manager_picks(int(entry_id), int(gw)).get("picks", [])
        pts_map = _element_points(int(gw))

        if chip_code == "3xc":
            captain = next((p for p in picks if p.get("is_captain")), None)
            if captain:
                element_points = pts_map.get(int(captain["element"]), 0)
                multiplier = int(captain.get("multiplier", 3))
                return int(element_points * multiplier)
            return int(gw_score or 0)

        if chip_code == "bboost":
            bench_total = 0
            for p in picks:
                # In FPL, bench positions are usually 12-15.
                if int(p.get("position", 0)) > 11:
                    bench_total += pts_map.get(int(p["element"]), 0)
            if bench_total > 0:
                return int(bench_total)
            return int(bench_points_fallback or 0)

    except Exception:
        return int(gw_score or bench_points_fallback or 0)

    return int(gw_score or bench_points_fallback or 0)

def ctrl_z_breakdown_table(standings: pd.DataFrame) -> pd.DataFrame:
    usage = chip_usage_awards(standings)
    if usage.empty:
        return pd.DataFrame()

    rows = []
    count_tracker = {}

    for _, r in usage.iterrows():
        if r["chip"] not in ["Triple Captain", "Free Hit", "Bench Boost"]:
            continue

        key = (int(r.entry_id), r["chip"])
        count_tracker[key] = count_tracker.get(key, 0) + 1
        chip_instance = f"{r['chip']} {count_tracker[key]}"

        chip_code_map = {
            "Triple Captain": "3xc",
            "Free Hit": "freehit",
            "Bench Boost": "bboost",
        }
        chip_code = chip_code_map[r["chip"]]
        impact = _chip_impact(
            int(r.entry_id),
            int(r.GW),
            chip_code,
            gw_score=int(r.score or 0),
            bench_points_fallback=int(r.get("bench_points", 0) or 0),
        )

        tc_score = impact if r["chip"] == "Triple Captain" else None
        fh_score = impact if r["chip"] == "Free Hit" else None
        bb_score = impact if r["chip"] == "Bench Boost" else None

        qualifies = (
            (r["chip"] == "Triple Captain" and impact < 6)
            or (r["chip"] == "Free Hit" and impact < 40)
            or (r["chip"] == "Bench Boost" and impact < 8)
        )

        rows.append({
            "entry_id": r.entry_id,
            "team_name": r.team_name,
            "manager_name": r.manager_name,
            "chip": chip_instance,
            "GW": int(r.GW),
            "tc_score": tc_score,
            "fh_score": fh_score,
            "bb_score": bb_score,
            "impact": impact,
            "threshold": "TC < 6 / FH < 40 / BB < 8",
            "qualifies_for_ctrl_z": qualifies,
        })

    df = pd.DataFrame(rows)
    if df.empty:
        return df

    return df.sort_values(["qualifies_for_ctrl_z", "impact"], ascending=[False, True]).reset_index(drop=True)


def transfer_tactician_table(standings: pd.DataFrame) -> pd.DataFrame:
    """
    MVP logic: net points gained from transfer activity including hits.
    Uses each GW's score minus transfer cost for GWs where the manager made transfers.
    Higher is better.
    """
    rows = []

    for _, row in standings.iterrows():
        hist = get_manager_history(int(row.entry_id)).get("current", [])
        transfer_gws = [h for h in hist if h.get("event_transfers", 0) > 0]

        gross_points = sum(h.get("points", 0) for h in transfer_gws)
        transfer_cost = sum(abs(h.get("event_transfers_cost", 0)) for h in transfer_gws)
        net_transfer_points = gross_points - transfer_cost
        transfer_count = sum(h.get("event_transfers", 0) for h in transfer_gws)
        active_transfer_gws = len(transfer_gws)

        rows.append({
            "entry_id": row.entry_id,
            "team_name": row.team_name,
            "manager_name": row.manager_name,
            "gross_points_on_transfer_gws": gross_points,
            "transfer_cost": transfer_cost,
            "net_transfer_points": net_transfer_points,
            "transfer_count": transfer_count,
            "active_transfer_gws": active_transfer_gws,
        })

    return pd.DataFrame(rows).sort_values("net_transfer_points", ascending=False).reset_index(drop=True)
