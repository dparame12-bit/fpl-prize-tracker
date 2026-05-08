import streamlit as st
import pandas as pd
import altair as alt

from config import LEAGUE_ID, APP_TITLE
from fpl_api import get_all_league_standings, current_gw
from prize_rules import (
    league_finisher_prizes,
    gw_winners,
    manager_of_month,
    transfer_efficiency,
    chip_awards_live,
    prize_summary,
)
from cup_logic import build_cup_bracket_live
from utils import password_gate

st.set_page_config(page_title=APP_TITLE, layout="wide")

st.markdown("""
<style>
.block-container { padding-top: 2rem; }
.big-title { font-size: 44px; font-weight: 800; margin-bottom: 0px; }
.subtle { color: #6b7280; font-size: 14px; }
.metric-card {
    background: #ffffff;
    border: 1px solid #e5e7eb;
    border-radius: 18px;
    padding: 18px 20px;
    box-shadow: 0 2px 10px rgba(0,0,0,0.04);
}
.metric-label { color: #6b7280; font-size: 13px; }
.metric-value { font-size: 30px; font-weight: 800; }
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

    page = st.radio(
        "Go to",
        [
            "Dashboard",
            "League Standings",
            "GW Winners",
            "Manager of the Month",
            "Chip Awards",
            "Transfer Efficiency",
            "WTL Cup",
            "Prize Summary",
            "Rules",
        ],
    )

st.markdown(f'<div class="big-title">{APP_TITLE}</div>', unsafe_allow_html=True)
st.markdown(f'<div class="subtle">Private league code: {LEAGUE_ID} · Current GW: {gw_now}</div>', unsafe_allow_html=True)
st.write("")

def show_top_metrics():
    c1, c2, c3, c4 = st.columns(4)
    cards = [
        ("Current GW", gw_now),
        ("Participants", len(standings)),
        ("Total Prize Pool", "₹36,000"),
        ("League Code", LEAGUE_ID),
    ]
    for col, (label, value) in zip([c1, c2, c3, c4], cards):
        col.markdown(
            f"""
            <div class="metric-card">
                <div class="metric-label">{label}</div>
                <div class="metric-value">{value}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

if page == "Dashboard":
    show_top_metrics()
    st.write("")
    st.subheader("Current Prize View")
    st.caption("Includes currently computable prizes. More advanced awards can be refined once the season ends.")
    st.dataframe(prize_summary(standings), use_container_width=True, hide_index=True)

elif page == "League Standings":
    st.subheader(f"Live League Standings — as of GW{gw_now}")
    df = league_finisher_prizes(standings)
    st.dataframe(df, use_container_width=True, hide_index=True)

elif page == "GW Winners":
    st.subheader(f"Gameweek Winners — through GW{gw_now}")
    st.caption("Normal GW winner = ₹150. Bonus GW19 and GW38 = ₹300.")
    df = gw_winners(standings)
    if df.empty:
        st.info("No GW winners available yet.")
    else:
        chart = (
            alt.Chart(df)
            .mark_bar(cornerRadiusTopLeft=4, cornerRadiusTopRight=4)
            .encode(
                x=alt.X("GW:O", title="Gameweek"),
                y=alt.Y("points:Q", title="Winning Score"),
                color=alt.Color("team_name:N", legend=None),
                tooltip=["GW", "team_name", "manager_name", "points", "prize"],
            )
            .properties(height=320)
        )
        st.altair_chart(chart, use_container_width=True)
        st.dataframe(df, use_container_width=True, hide_index=True)

elif page == "Manager of the Month":
    st.subheader("Manager of the Month")
    st.caption("Shown in calendar order.")
    df = manager_of_month(standings)
    st.dataframe(df, use_container_width=True, hide_index=True)

elif page == "Chip Awards":
    st.subheader("Live Chip Awards")
    st.caption("Shows the current leader for BB / TC / FH in H1 and H2. MVP uses GW score as chip score for now.")
    df = chip_awards_live(standings)
    st.dataframe(df, use_container_width=True, hide_index=True)

elif page == "Transfer Efficiency":
    st.subheader("Best Transfer Efficiency")
    st.caption("Formula: (Total points - penalty points) / (38 + number of hits)")
    df = transfer_efficiency(standings)

    chart = (
        alt.Chart(df.head(10))
        .mark_bar(cornerRadiusTopLeft=4, cornerRadiusTopRight=4)
        .encode(
            x=alt.X("transfer_efficiency:Q", title="Transfer Efficiency"),
            y=alt.Y("team_name:N", sort="-x", title="Team"),
            tooltip=["team_name", "manager_name", "total_points", "penalty_points", "hits", "transfer_efficiency"],
        )
        .properties(height=360)
    )
    st.altair_chart(chart, use_container_width=True)
    st.dataframe(df, use_container_width=True, hide_index=True)

elif page == "WTL Cup":
    st.subheader("WTL Cup — Live Bracket")
    st.caption("Random draw. Each round runs for 2 GWs: R1 GW19–20, QF GW21–22, SF GW23–24, Final GW25–26.")
    bracket = build_cup_bracket_live(standings)
    if bracket.empty:
        st.info("Cup bracket will activate once league standings are available.")
    else:
        for round_name in ["Round 1", "Quarter Final", "Semi Final", "Final"]:
            r = bracket[bracket["round"] == round_name]
            if not r.empty:
                st.markdown(f"### {round_name}")
                st.dataframe(r, use_container_width=True, hide_index=True)

elif page == "Prize Summary":
    st.subheader("Prize Payout Summary")
    st.caption("Includes league, GW, MOTM, live chip awards, transfer efficiency, mid-season winner and current total.")
    st.dataframe(prize_summary(standings), use_container_width=True, hide_index=True)

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
Randomized knockout draw from GW19. Each fixture runs for 2 GWs.

### Special Awards — ₹3,000
Biggest Climb, Mid Season Winner, Best Transfer Efficiency, Most Captain Points, Most Bench Points, Highest GW Score Without Chip.

### Chip Awards — ₹1,500
Best BB, TC, FH in H1 and H2.

### Transfer Tactician — ₹500
Highest net points gained from transfers, including hits.

### Troll Awards — ₹500
Ctrl + Z Award and Wooden Spoon.
""")
