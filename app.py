import streamlit as st
import pandas as pd
import altair as alt

from config import LEAGUE_ID, APP_TITLE
from fpl_api import get_all_league_standings, current_gw
from prize_rules import (
    league_finisher_prizes, gw_winners, manager_of_month,
    transfer_efficiency, chip_awards_live, prize_summary,
    standings_history,
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
        "Chip Awards", "Transfer Efficiency", "WTL Cup", "Prize Summary", "Rules"
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
    st.caption("20 teams: 12 byes, 4 first-round fixtures. R1 GW19–20, QF GW21–22, SF GW23–24, Final GW25–26.")
    bracket = build_cup_bracket_live(standings)
    if bracket.empty:
        st.info("Cup bracket will activate once league standings are available.")
    else:
        rounds = ["Round 1", "Quarter Final", "Semi Final", "Final"]
        cols = st.columns(4)
        for col, round_name in zip(cols, rounds):
            with col:
                st.markdown(f"### {round_name}")
                r = bracket[bracket["round"] == round_name]
                if r.empty:
                    st.caption("Pending")
                for _, row in r.iterrows():
                    winner_line = f"🏆 {row['winner']}" if row["winner"] else "Winner pending"
                    st.markdown(f"""
                    <div class="cup-card">
                        <div class="cup-title">{row['GW window']}</div>
                        <div class="cup-fixture">{row['team_a']}<br/>vs<br/>{row['team_b']}</div>
                        <div class="cup-score">{row['team_a_points']} - {row['team_b_points']}</div>
                        <div class="cup-winner">{winner_line}</div>
                        <div class="cup-status">{row['status']}</div>
                    </div>
                    """, unsafe_allow_html=True)
        st.subheader("Cup Table")
        st.dataframe(bracket, use_container_width=True, hide_index=True)

elif page == "Prize Summary":
    st.subheader("Prize Payout Summary")
    st.caption("Includes league, GW, MOTM, live chip awards, transfer efficiency, mid-season winner and current total.")
    df = prize_summary(standings)
    df2 = df.reset_index(drop=True)
    df2.insert(0, "rank", df2.index + 1)
    st.dataframe(top3_style(df2, "rank"), use_container_width=True, hide_index=True)

elif page == "Rules":
    st.subheader("Prize Rules")
    st.markdown("""
### League Finishers — ₹18,700
1st ₹6,000 · 2nd ₹4,100 · 3rd ₹2,600 · 4th ₹1,500 · 5th ₹1,100 · 6th ₹800

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
Highest net points gained from transfers, including hits.

### Troll Awards — ₹500
Ctrl + Z Award and Wooden Spoon.
""")
