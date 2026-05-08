import streamlit as st
import pandas as pd

from config import LEAGUE_ID, APP_TITLE, PRIZES
from fpl_api import get_all_league_standings, current_gw
from prize_rules import (
    league_finisher_prizes,
    gw_winners,
    manager_of_month,
    transfer_efficiency,
    chip_usage_awards,
    prize_summary,
)
from cup_logic import generate_or_load_draw
from utils import password_gate

st.set_page_config(page_title=APP_TITLE, layout="wide")

if not password_gate():
    st.stop()

st.title(APP_TITLE)
st.caption(f"Private league code: {LEAGUE_ID}")

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

standings = get_all_league_standings(LEAGUE_ID)

if standings.empty:
    st.error("No league data found. Please check the league code or FPL API availability.")
    st.stop()

gw_now = current_gw()

if page == "Dashboard":
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Current GW", gw_now)
    c2.metric("Participants", len(standings))
    c3.metric("Total Prize Pool", "₹36,000")
    c4.metric("League Code", LEAGUE_ID)

    st.subheader("Current Prize View")
    st.dataframe(prize_summary(standings), use_container_width=True, hide_index=True)

elif page == "League Standings":
    st.subheader("Live League Standings")
    st.dataframe(league_finisher_prizes(standings), use_container_width=True, hide_index=True)

elif page == "GW Winners":
    st.subheader("Gameweek Winners")
    st.info("GW19 and GW38 are bonus GWs worth ₹300. Other GW winners get ₹150.")
    st.dataframe(gw_winners(standings), use_container_width=True, hide_index=True)

elif page == "Manager of the Month":
    st.subheader("Manager of the Month")
    st.caption("Initial version uses fixed GW-month mapping from config.py.")
    st.dataframe(manager_of_month(standings), use_container_width=True, hide_index=True)

elif page == "Chip Awards":
    st.subheader("Chip Usage Tracker")
    st.caption("MVP uses GW score for chip tracking. Exact chip impact can be refined in v2 using picks-level logic.")
    st.dataframe(chip_usage_awards(standings), use_container_width=True, hide_index=True)

elif page == "Transfer Efficiency":
    st.subheader("Best Transfer Efficiency")
    st.caption("Formula: (Total points - penalty points) / (38 + number of hits)")
    st.dataframe(transfer_efficiency(standings), use_container_width=True, hide_index=True)

elif page == "WTL Cup":
    st.subheader("WTL Cup Draw")
    st.caption("Randomized once and saved. Starts GW19. Each fixture runs for 2 GWs.")
    draw = generate_or_load_draw(standings)
    st.dataframe(draw, use_container_width=True, hide_index=True)

elif page == "Prize Summary":
    st.subheader("Prize Payout Summary")
    st.caption("Shows currently computable prizes. Advanced awards will be added after validation.")
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
