import streamlit as st
import pandas as pd
import altair as alt

from config import LEAGUE_ID, APP_TITLE
from fpl_api import get_all_league_standings, current_gw
from prize_rules import (
    league_finisher_prizes, gw_winners, manager_of_month,
    transfer_efficiency, chip_awards_live, prize_summary,
    standings_history,
    mid_season_table, bench_points_table, biggest_climb_table,
    captain_points_table, highest_gw_without_chip,
    ctrl_z_breakdown_table, transfer_tactician_table, wooden_spoon_table,
)
from cup_logic import build_cup_bracket_live
from utils import password_gate

st.set_page_config(page_title=APP_TITLE, layout="wide")

st.markdown("""
<style>
.block-container { padding-top: 2rem; }
.big-title { font-size: 44px; font-weight: 850; letter-spacing: -1px; }
.subtle { color: #6b7280; font-size: 14px; }
.metric-card {
    background: linear-gradient(135deg, #ffffff 0%, #f8fafc 100%);
    border: 1px solid #e5e7eb; border-radius: 20px;
    padding: 18px 22px; box-shadow: 0 8px 24px rgba(15,23,42,0.06);
}
.metric-label { color: #64748b; font-size: 13px; font-weight: 600; }
.metric-value { font-size: 30px; font-weight: 850; color: #0f172a; }
.cup-card {
    border-radius: 18px; padding: 14px; margin-bottom: 12px;
    background: linear-gradient(135deg, #f8fafc, #ffffff);
    border: 1px solid #e5e7eb; box-shadow: 0 4px 16px rgba(15,23,42,0.05);
}
.cup-title { font-weight: 800; font-size: 15px; color: #111827; }
.cup-fixture { font-size: 13px; color: #374151; margin-top: 8px; }
.cup-score { font-size: 21px; font-weight: 850; margin-top: 8px; }
.cup-winner { color: #15803d; font-weight: 800; margin-top: 8px; }
.cup-status { color: #64748b; font-size: 12px; margin-top: 4px; }
</style>
""", unsafe_allow_html=True)

if not password_gate():
    st.stop()

standings = get_all_league_standings(LEAGUE_ID)
if standings.empty:
    st.error("No league data found. Please check the league code or FPL API availability.")
    st.stop()

gw_now = current_gw()

with st.sidebar:
    st.header("Controls")
    if st.button("Refresh FPL data"):
        st.cache_data.clear()
        st.rerun()

    page = st.radio("Go to", [
        "Dashboard", "League Standings", "GW Winners", "Manager of the Month",
        "Chip Awards", "Transfer Efficiency", "WTL Cup", "Special Awards",
        "Rules", "Prize Summary"
    ])

st.markdown(f'<div class="big-title">{APP_TITLE}</div>', unsafe_allow_html=True)
st.markdown(f'<div class="subtle">Private league code: {LEAGUE_ID} · Current GW: {gw_now}</div>', unsafe_allow_html=True)
st.write("")

def show_top_metrics():
    cols = st.columns(4)
    cards = [("Current GW", gw_now), ("Participants", len(standings)), ("Total Prize Pool", "₹36,000"), ("League Code", LEAGUE_ID)]
    for col, (label, value) in zip(cols, cards):
        col.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">{label}</div>
            <div class="metric-value">{value}</div>
        </div>
        """, unsafe_allow_html=True)

def top3_style(df, rank_col):
    def style_row(row):
        try:
            rank = int(row[rank_col])
        except Exception:
            return [''] * len(row)
        if rank == 1:
            return ['background-color: #fff7cc; font-weight: 750'] * len(row)
        if rank == 2:
            return ['background-color: #eef2ff; font-weight: 700'] * len(row)
        if rank == 3:
            return ['background-color: #ffedd5; font-weight: 700'] * len(row)
        return [''] * len(row)
    return df.style.apply(style_row, axis=1)


def pretty_prize_summary(df):
    rename_map = {
        "rank": "Prize Rank",
        "entry_id": "Entry ID",
        "team_name": "Team",
        "manager_name": "Manager",
        "current_rank": "League Rank",
        "total_points": "Total Points",
        "league_finish_prize": "League Finish",
        "gw_winner_prize": "GW Winners",
        "motm_prize": "Manager of the Month",
        "bb_h1_prize": "Bench Boost H1",
        "bb_h2_prize": "Bench Boost H2",
        "tc_h1_prize": "Triple Captain H1",
        "tc_h2_prize": "Triple Captain H2",
        "fh_h1_prize": "Free Hit H1",
        "fh_h2_prize": "Free Hit H2",
        "wtl_cup_prize": "WTL Cup",
        "transfer_efficiency_prize": "Transfer Efficiency",
        "mid_season_winner_prize": "Mid Season Winner",
        "most_bench_points_prize": "Most Bench Points",
        "biggest_climb_prize": "Biggest Climb",
        "most_captain_points_prize": "Most Captain Points",
        "highest_gw_without_chip_prize": "Highest GW No Chip",
        "ctrl_z_award_prize": "Ctrl + Z",
        "transfer_tactician_prize": "Transfer Tactician",
        "wooden_spoon_prize": "Wooden Spoon",
        "known_prize_total": "Total Prize",
    }
    out = df.rename(columns=rename_map)
    preferred = [
        "Prize Rank", "Entry ID", "Team", "Manager", "League Rank", "Total Points",
        "League Finish", "GW Winners", "Manager of the Month", "Bench Boost H1",
        "Bench Boost H2", "Triple Captain H1", "Triple Captain H2", "Free Hit H1",
        "Free Hit H2", "WTL Cup", "Transfer Efficiency", "Mid Season Winner",
        "Most Bench Points", "Biggest Climb", "Most Captain Points",
        "Highest GW No Chip", "Ctrl + Z", "Transfer Tactician", "Wooden Spoon", "Total Prize"
    ]
    return out[[c for c in preferred if c in out.columns]]

def render_prize_summary_table(df):
    display_df = pretty_prize_summary(df).copy()
    prize_cols = [
        c for c in display_df.columns
        if c not in ["Prize Rank", "Entry ID", "Team", "Manager", "League Rank", "Total Points"]
    ]

    def style_prize_cells(val, col):
        try:
            num = float(val)
        except Exception:
            num = 0
        if col == "Total Prize":
            return "background-color: #fef3c7; color: #92400e; font-weight: 900"
        if col in prize_cols and num > 0:
            return "background-color: #dcfce7; color: #166534; font-weight: 850"
        return ""

    def row_style(row):
        styles = []
        for col in display_df.columns:
            styles.append(style_prize_cells(row[col], col))
        return styles

    fmt = {c: "₹{:,.0f}" for c in prize_cols}
    st.dataframe(
        display_df.style.apply(row_style, axis=1).format(fmt),
        use_container_width=True,
        hide_index=True,
    )


if page == "Dashboard":
    show_top_metrics()
    st.write("")
    st.subheader(f"League Snapshot — as of GW{gw_now}")
    dash = standings[["current_rank", "team_name", "manager_name", "total_points", "gw_points"]].copy()
    dash = dash.rename(columns={
        "current_rank": "Rank", "team_name": "Team", "manager_name": "Manager",
        "total_points": "Total Points", "gw_points": f"GW{gw_now} Points"
    })
    st.dataframe(top3_style(dash, "Rank"), use_container_width=True, hide_index=True)

    st.write("")
    st.subheader("Ranking Race")
    st.caption("Cumulative rank movement from GW1 onward. Lower is better, so rank 1 appears at the top.")
    race = standings_history(standings)
    if race.empty:
        st.info("Ranking history is not available yet.")
    else:
        chart = (
            alt.Chart(race)
            .mark_line(point=True, strokeWidth=3)
            .encode(
                x=alt.X("GW:O", title="Gameweek"),
                y=alt.Y("rank:Q", title="Rank", scale=alt.Scale(reverse=True), axis=alt.Axis(tickMinStep=1)),
                color=alt.Color("team_name:N", title="Team", scale=alt.Scale(scheme="tableau20")),
                tooltip=["GW", "team_name", "manager_name", "cumulative_points", "rank"],
            )
            .properties(height=520)
            .interactive()
        )
        st.altair_chart(chart, use_container_width=True)

elif page == "League Standings":
    st.subheader(f"Live League Standings — as of GW{gw_now}")
    df = league_finisher_prizes(standings)
    st.dataframe(top3_style(df, "current_rank"), use_container_width=True, hide_index=True)

elif page == "GW Winners":
    st.subheader(f"Gameweek Winners — through GW{gw_now}")
    st.caption("Normal GW winner = ₹150. Bonus GW19 and GW38 = ₹300.")
    df = gw_winners(standings)
    if df.empty:
        st.info("No GW winners available yet.")
    else:
        chart = (
            alt.Chart(df)
            .mark_bar(cornerRadiusTopLeft=5, cornerRadiusTopRight=5)
            .encode(
                x=alt.X("GW:O", title="Gameweek"),
                y=alt.Y("points:Q", title="Winning Score"),
                color=alt.Color("team_name:N", legend=None, scale=alt.Scale(scheme="tableau20")),
                tooltip=["GW", "team_name", "manager_name", "points", "prize"],
            ).properties(height=340)
        )
        st.altair_chart(chart, use_container_width=True)
        st.dataframe(df, use_container_width=True, hide_index=True)

elif page == "Manager of the Month":
    st.subheader("Manager of the Month")
    st.caption("Shown in calendar order.")
    st.dataframe(manager_of_month(standings), use_container_width=True, hide_index=True)

elif page == "Chip Awards":
    st.subheader("Live Chip Awards")
    st.caption("Shows the current leader for BB / TC / FH in H1 and H2. MVP uses GW score as chip score for now.")
    st.dataframe(chip_awards_live(standings), use_container_width=True, hide_index=True)

elif page == "Transfer Efficiency":
    st.subheader("Best Transfer Efficiency")
    st.caption("Formula: (Total points - penalty points) / (38 + number of hits)")
    df = transfer_efficiency(standings)
    chart = (
        alt.Chart(df.head(15))
        .mark_bar(cornerRadiusTopLeft=5, cornerRadiusTopRight=5)
        .encode(
            x=alt.X("transfer_efficiency:Q", title="Transfer Efficiency"),
            y=alt.Y("team_name:N", sort="-x", title="Team"),
            color=alt.Color("team_name:N", legend=None, scale=alt.Scale(scheme="category20")),
            tooltip=["team_name", "manager_name", "total_points", "penalty_points", "hits", "transfer_efficiency"],
        ).properties(height=480)
    )
    st.altair_chart(chart, use_container_width=True)
    df2 = df.reset_index(drop=True)
    df2.insert(0, "rank", df2.index + 1)
    st.dataframe(top3_style(df2, "rank"), use_container_width=True, hide_index=True)


elif page == "WTL Cup":
    st.subheader("WTL Cup — Bracket View")
    st.caption("32-slot bracket: 20 teams + 12 byes. R32 has 16 games, then R16, Quarter Final, Semi Final and one Final.")
    bracket = build_cup_bracket_live(standings)

    if bracket.empty:
        st.info("Cup bracket will activate once league standings are available.")
    else:
        rounds = ["R32", "R16", "Quarter Final", "Semi Final", "Final"]
        cols = st.columns(5)

        for col, round_name in zip(cols, rounds):
            with col:
                st.markdown(f"### {round_name}")
                r = bracket[bracket["round"] == round_name]

                if r.empty:
                    st.caption("Pending")

                for _, row in r.iterrows():
                    winner_line = f"🏆 {row['winner']}" if row["winner"] else "Winner pending"
                    st.markdown(
                        f"""
                        <div class="cup-card">
                            <div class="cup-title">{row['match']} · {row['GW window']}</div>
                            <div class="cup-fixture">{row['team_a']}<br/>vs<br/>{row['team_b']}</div>
                            <div class="cup-score">{row['team_a_points']} - {row['team_b_points']}</div>
                            <div class="cup-winner">{winner_line}</div>
                            <div class="cup-status">{row['status']}</div>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )

        st.subheader("Cup Table")
        st.dataframe(bracket, use_container_width=True, hide_index=True)

elif page == "Prize Summary":
    st.subheader("Prize Payout Summary")
    st.caption("Prize-winning cells are highlighted in green. First 6 columns are frozen while scrolling horizontally.")
    df = prize_summary(standings)
    df2 = df.reset_index(drop=True)
    df2.insert(0, "rank", df2.index + 1)

    c1, c2, c3 = st.columns(3)
    c1.metric("Total Allocated / Live", f"₹{df2['known_prize_total'].sum():,.0f}")
    c2.metric("Managers With Prize", int((df2["known_prize_total"] > 0).sum()))
    c3.metric("Top Current Payout", f"₹{df2['known_prize_total'].max():,.0f}")

    render_prize_summary_table(df2)


elif page == "Special Awards":
    st.subheader("Special Awards — Live Leaderboards")
    st.caption("Each award has its own leaderboard and visual so everyone can see how the winner is decided.")

    def safe_df(title, fn):
        try:
            data = fn(standings)
            if data is None:
                return pd.DataFrame()
            return data
        except Exception as e:
            st.error(f"{title} could not load: {e}")
            return pd.DataFrame()

    def award_cards(df, metric_col, label=None):
        if df is None or df.empty:
            st.info("No data available yet.")
            return False
        winner = df.iloc[0]
        c1, c2, c3 = st.columns(3)
        c1.metric("Current Winner", winner.get("team_name", ""))
        c2.metric("Manager", winner.get("manager_name", ""))
        c3.metric(label or metric_col.replace("_", " ").title(), winner.get(metric_col, ""))
        return True

    tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8 = st.tabs([
        "Mid Season", "Bench Points", "Biggest Climb", "Captain Points",
        "Highest GW No Chip", "Transfer Tactician", "Ctrl + Z", "Wooden Spoon"
    ])

    with tab1:
        st.markdown("### Mid Season Winner")
        df = safe_df("Mid Season Winner", mid_season_table)
        if not df.empty:
            winners = df[df["is_winner"]] if "is_winner" in df.columns else df.head(1)
            winner_names = ", ".join(winners["team_name"].astype(str).tolist())
            split_prize = winners["mid_season_prize"].iloc[0] if "mid_season_prize" in winners.columns else 500
            c1, c2, c3 = st.columns(3)
            c1.metric("Winner(s)", winner_names)
            c2.metric("GW19 Points", int(winners["total_points_gw19"].iloc[0]))
            c3.metric("Prize Each", f"₹{split_prize:,.0f}" if float(split_prize).is_integer() else f"₹{split_prize:,.2f}")
            chart_df = df.head(15).copy()
            chart_df["winner_status"] = chart_df["is_winner"].map({True: "Winner", False: "Others"}) if "is_winner" in chart_df.columns else "Others"
            chart = alt.Chart(chart_df).mark_bar(cornerRadiusTopLeft=5, cornerRadiusTopRight=5).encode(
                x=alt.X("total_points_gw19:Q", title="Total Points at GW19"),
                y=alt.Y("team_name:N", sort="-x", title="Team"),
                color=alt.Color("winner_status:N", scale=alt.Scale(domain=["Winner", "Others"], range=["#f59e0b", "#94a3b8"])),
                tooltip=list(chart_df.columns),
            ).properties(height=430)
            st.altair_chart(chart, use_container_width=True)
            out=df.reset_index(drop=True); out.insert(0,"rank",out.index+1)
            st.dataframe(top3_style(out,"rank"), use_container_width=True, hide_index=True)

    with tab2:
        st.markdown("### Most Points on Bench")
        df = safe_df("Bench Points", bench_points_table)
        if award_cards(df, "bench_points"):
            chart=alt.Chart(df.head(15)).mark_bar(cornerRadiusTopLeft=5,cornerRadiusTopRight=5).encode(
                x=alt.X("bench_points:Q", title="Bench Points"),
                y=alt.Y("team_name:N", sort="-x", title="Team"),
                color=alt.Color("bench_points:Q", scale=alt.Scale(scheme="orangered"), legend=None),
                tooltip=list(df.columns),
            ).properties(height=430)
            st.altair_chart(chart, use_container_width=True)
            out=df.reset_index(drop=True); out.insert(0,"rank",out.index+1)
            st.dataframe(top3_style(out,"rank"), use_container_width=True, hide_index=True)

    with tab3:
        st.markdown("### Biggest Climb")
        df = safe_df("Biggest Climb", biggest_climb_table)
        if award_cards(df, "climb_score"):
            chart_df=df.head(15).copy()
            chart_df["winner_status"]=["Winner" if i==0 else "Others" for i in range(len(chart_df))]
            chart=alt.Chart(chart_df).mark_bar(cornerRadiusTopLeft=5,cornerRadiusTopRight=5).encode(
                x=alt.X("climb_score:Q", title="GW20–38 minus GW1–19"),
                y=alt.Y("team_name:N", sort="-x", title="Team"),
                color=alt.Color("winner_status:N", scale=alt.Scale(domain=["Winner","Others"], range=["#22c55e","#94a3b8"]), legend=None),
                tooltip=list(chart_df.columns),
            ).properties(height=430)
            st.altair_chart(chart, use_container_width=True)
            out=df.reset_index(drop=True); out.insert(0,"rank",out.index+1)
            st.dataframe(top3_style(out,"rank"), use_container_width=True, hide_index=True)

    with tab4:
        st.markdown("### Most Captain Points")
        df = safe_df("Captain Points", captain_points_table)
        if award_cards(df, "captain_points"):
            chart=alt.Chart(df.head(15)).mark_bar(cornerRadiusTopLeft=5,cornerRadiusTopRight=5).encode(
                x=alt.X("captain_points:Q", title="Captain Points"),
                y=alt.Y("team_name:N", sort="-x", title="Team"),
                color=alt.Color("team_name:N", scale=alt.Scale(scheme="tableau20"), legend=None),
                tooltip=list(df.columns),
            ).properties(height=430)
            st.altair_chart(chart, use_container_width=True)
            out=df.reset_index(drop=True); out.insert(0,"rank",out.index+1)
            st.dataframe(top3_style(out,"rank"), use_container_width=True, hide_index=True)

    with tab5:
        st.markdown("### Highest GW Score Without Chip")
        df = safe_df("Highest GW Without Chip", highest_gw_without_chip)
        if award_cards(df, "points"):
            chart=alt.Chart(df.head(15)).mark_bar(cornerRadiusTopLeft=5,cornerRadiusTopRight=5).encode(
                x=alt.X("team_name:N", sort="-y", title="Team"),
                y=alt.Y("points:Q", title="Best No-Chip GW Score"),
                color=alt.Color("GW:O", scale=alt.Scale(scheme="viridis"), title="GW"),
                tooltip=list(df.columns),
            ).properties(height=430)
            st.altair_chart(chart, use_container_width=True)
            out=df.reset_index(drop=True); out.insert(0,"rank",out.index+1)
            st.dataframe(top3_style(out,"rank"), use_container_width=True, hide_index=True)

    with tab6:
        st.markdown("### Transfer Tactician")
        df = safe_df("Transfer Tactician", transfer_tactician_table)
        if award_cards(df, "net_transfer_points"):
            chart=alt.Chart(df.head(15)).mark_bar(cornerRadiusTopLeft=5,cornerRadiusTopRight=5).encode(
                x=alt.X("net_transfer_points:Q", title="Net Transfer Points"),
                y=alt.Y("team_name:N", sort="-x", title="Team"),
                color=alt.Color("net_transfer_points:Q", scale=alt.Scale(scheme="greens"), legend=None),
                tooltip=list(df.columns),
            ).properties(height=430)
            st.altair_chart(chart, use_container_width=True)
            out=df.reset_index(drop=True); out.insert(0,"rank",out.index+1)
            st.dataframe(top3_style(out,"rank"), use_container_width=True, hide_index=True)

    with tab7:
        st.markdown("### Ctrl + Z Award")
        df = safe_df("Ctrl + Z", ctrl_z_breakdown_table)
        if not df.empty:
            q = df[df["qualifies_for_ctrl_z"]] if "qualifies_for_ctrl_z" in df.columns else pd.DataFrame()
            if not q.empty:
                winner=q.sort_values("impact", ascending=True).iloc[0]
                c1,c2,c3=st.columns(3)
                c1.metric("Current Ctrl + Z", winner["team_name"])
                c2.metric("Chip", winner["chip"])
                c3.metric("Impact", winner["impact"])
            else:
                st.warning("No chip usage currently meets the Ctrl + Z thresholds.")
            chart_df=df.copy()
            chart_df["qualifies"]=chart_df["qualifies_for_ctrl_z"].map({True:"Qualifies",False:"Does not qualify"}) if "qualifies_for_ctrl_z" in chart_df.columns else "N/A"
            chart=alt.Chart(chart_df).mark_circle(size=300).encode(
                x=alt.X("GW:O", title="Gameweek"),
                y=alt.Y("impact:Q", title="Chip Impact"),
                color=alt.Color("chip:N", scale=alt.Scale(scheme="set1")),
                shape=alt.Shape("qualifies:N"),
                tooltip=list(chart_df.columns),
            ).properties(height=430)
            st.altair_chart(chart, use_container_width=True)
            out=df.reset_index(drop=True); out.insert(0,"rank",out.index+1)
            st.dataframe(top3_style(out,"rank"), use_container_width=True, hide_index=True)

    with tab8:
        st.markdown("### Wooden Spoon")
        df = safe_df("Wooden Spoon", wooden_spoon_table)
        if award_cards(df, "total_points"):
            chart=alt.Chart(df.head(15)).mark_bar(cornerRadiusTopLeft=5,cornerRadiusTopRight=5).encode(
                x=alt.X("total_points:Q", title="Total Points"),
                y=alt.Y("team_name:N", sort="x", title="Team"),
                color=alt.Color("active_gws:Q", scale=alt.Scale(scheme="blues"), title="Active GWs"),
                tooltip=list(df.columns),
            ).properties(height=430)
            st.altair_chart(chart, use_container_width=True)
            out=df.reset_index(drop=True); out.insert(0,"rank",out.index+1)
            st.dataframe(top3_style(out,"rank"), use_container_width=True, hide_index=True)


elif page == "Rules":
    st.subheader("Prize Rules")
    st.markdown("""
### League Finishers — ₹18,700
1st ₹6,500 · 2nd ₹4,600 · 3rd ₹3,100 · 4th ₹2,000 · 5th ₹1,600 · 6th ₹900

### Gameweek Winners — ₹6,000
36 GWs × ₹150 = ₹5,400  
GW19 and GW38 bonus: ₹300 each

### Manager of the Month — ₹5,000
10 months × ₹500

### WTL Cup — ₹800
20 teams: 12 teams get a first-round bye. 8 teams play 4 first-round fixtures, then winners join the 12 bye teams.

### Special Awards — ₹3,000
Biggest Climb, Mid Season Winner, Best Transfer Efficiency, Most Captain Points, Most Bench Points, Highest GW Score Without Chip.

### Chip Awards — ₹1,500
Best BB, TC, FH in H1 and H2.

### Transfer Tactician — ₹500
Highest net points gained from transfers, including hits. Included in Special Awards and Prize Summary. Included in Special Awards and Prize Summary.

### Troll Awards — ₹500
Ctrl + Z Award and Wooden Spoon.
""")
