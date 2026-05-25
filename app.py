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
    worst_chip_usage_table, ctrl_z_breakdown_table, wooden_spoon_table,
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
        "Chip Awards", "Transfer Efficiency", "WTL Cup", "Prize Summary", "Special Awards", "Rules"
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
    st.caption("Includes league, GW, MOTM, live chip awards, transfer efficiency, mid-season winner and current total.")
    df = prize_summary(standings)
    df2 = df.reset_index(drop=True)
    df2.insert(0, "rank", df2.index + 1)
    st.dataframe(top3_style(df2, "rank"), use_container_width=True, hide_index=True)



elif page == "Special Awards":
    st.subheader("Special Awards — Live Leaderboards")
    st.caption("Different views for each award so everyone can see how the winner is being decided.")

    tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
        "Mid Season",
        "Bench Points",
        "Biggest Climb",
        "Captain Points",
        "Highest GW No Chip",
        "Ctrl + Z",
        "Wooden Spoon",
    ])

    def winner_cards(df, metric_col):
        if df is None or df.empty:
            st.info("No data available yet.")
            return False
        winner = df.iloc[0]
        c1, c2, c3 = st.columns(3)
        c1.metric("Current Winner", winner["team_name"])
        c2.metric("Manager", winner["manager_name"])
        c3.metric(metric_col.replace("_", " ").title(), winner[metric_col])
        return True

    with tab1:
        st.markdown("### Mid Season Winner")
        st.caption("Leader after GW19 based on cumulative total points. If tied, the ₹500 prize is split equally.")
        df = mid_season_table(standings)

        if df is None or df.empty:
            st.info("No GW19 data available yet.")
        else:
            winners = df[df["is_winner"]]
            winner_names = ", ".join(winners["team_name"].tolist())
            split_prize = winners["mid_season_prize"].iloc[0] if not winners.empty else 0

            c1, c2, c3 = st.columns(3)
            c1.metric("Winner(s)", winner_names)
            c2.metric("Winning GW19 Total", int(winners["total_points_gw19"].iloc[0]))
            c3.metric("Prize Each", f"₹{split_prize:,.0f}" if float(split_prize).is_integer() else f"₹{split_prize:,.2f}")

            chart_df = df.head(15).copy()
            chart_df["winner_status"] = chart_df["is_winner"].map({True: "Winner", False: "Others"})

            bars = (
                alt.Chart(chart_df)
                .mark_bar(cornerRadiusTopLeft=5, cornerRadiusTopRight=5)
                .encode(
                    x=alt.X("total_points_gw19:Q", title="Total Points at GW19"),
                    y=alt.Y("team_name:N", sort="-x", title="Team"),
                    color=alt.Color("winner_status:N", scale=alt.Scale(domain=["Winner", "Others"], range=["#f59e0b", "#94a3b8"])),
                    tooltip=["team_name", "manager_name", "total_points_gw19", "mid_season_prize"],
                )
                .properties(height=460)
            )

            labels = (
                alt.Chart(chart_df)
                .mark_text(align="left", dx=5)
                .encode(
                    x="total_points_gw19:Q",
                    y=alt.Y("team_name:N", sort="-x"),
                    text="total_points_gw19:Q",
                )
            )

            st.altair_chart(bars + labels, use_container_width=True)

            df2 = df.reset_index(drop=True)
            df2.insert(0, "rank", df2.index + 1)
            st.dataframe(top3_style(df2, "rank"), use_container_width=True, hide_index=True)

    with tab2:
        st.markdown("### Most Points on Bench")
        st.caption("Total points left on the bench across all gameweeks.")
        df = bench_points_table(standings)
        if winner_cards(df, "bench_points"):
            chart = (
                alt.Chart(df.head(15))
                .mark_bar(cornerRadiusTopLeft=5, cornerRadiusTopRight=5)
                .encode(
                    x=alt.X("bench_points:Q", title="Bench Points"),
                    y=alt.Y("team_name:N", sort="-x", title="Team"),
                    color=alt.Color("bench_points:Q", scale=alt.Scale(scheme="orangered"), legend=None),
                    tooltip=["team_name", "manager_name", "bench_points"],
                )
                .properties(height=460)
            )
            st.altair_chart(chart, use_container_width=True)
            df2 = df.reset_index(drop=True)
            df2.insert(0, "rank", df2.index + 1)
            st.dataframe(top3_style(df2, "rank"), use_container_width=True, hide_index=True)

    with tab3:
        st.markdown("### Biggest Climb")
        st.caption("GW20–38 points minus GW1–19 points. Highest positive difference wins.")
        df = biggest_climb_table(standings)
        if winner_cards(df, "climb_score"):
            melt = df.head(15).melt(
                id_vars=["team_name", "manager_name", "climb_score"],
                value_vars=["gw1_19_points", "gw20_38_points"],
                var_name="period",
                value_name="points",
            )
            chart = (
                alt.Chart(melt)
                .mark_bar(cornerRadiusTopLeft=4, cornerRadiusTopRight=4)
                .encode(
                    x=alt.X("points:Q", title="Points"),
                    y=alt.Y("team_name:N", sort="-x", title="Team"),
                    color=alt.Color("period:N", scale=alt.Scale(scheme="set2")),
                    tooltip=["team_name", "manager_name", "period", "points", "climb_score"],
                )
                .properties(height=500)
            )
            st.altair_chart(chart, use_container_width=True)
            df2 = df.reset_index(drop=True)
            df2.insert(0, "rank", df2.index + 1)
            st.dataframe(top3_style(df2, "rank"), use_container_width=True, hide_index=True)

    with tab4:
        st.markdown("### Most Captain Points")
        st.caption("Sum of captain points across all gameweeks, including captain multiplier.")
        df = captain_points_table(standings)
        if winner_cards(df, "captain_points"):
            chart = (
                alt.Chart(df.head(15))
                .mark_circle(size=420)
                .encode(
                    x=alt.X("captain_points:Q", title="Captain Points"),
                    y=alt.Y("team_name:N", sort="-x", title="Team"),
                    color=alt.Color("team_name:N", scale=alt.Scale(scheme="category20"), legend=None),
                    tooltip=["team_name", "manager_name", "captain_points"],
                )
                .properties(height=470)
            )
            st.altair_chart(chart, use_container_width=True)
            df2 = df.reset_index(drop=True)
            df2.insert(0, "rank", df2.index + 1)
            st.dataframe(top3_style(df2, "rank"), use_container_width=True, hide_index=True)

    with tab5:
        st.markdown("### Highest GW Score Without Chip")
        st.caption("Highest single-GW score where no Wildcard, Free Hit, Triple Captain or Bench Boost was used.")
        df = highest_gw_without_chip(standings)
        if winner_cards(df, "points"):
            chart = (
                alt.Chart(df.head(15))
                .mark_bar(cornerRadiusTopLeft=5, cornerRadiusTopRight=5)
                .encode(
                    x=alt.X("team_name:N", sort="-y", title="Team"),
                    y=alt.Y("points:Q", title="Best No-Chip GW Score"),
                    color=alt.Color("GW:O", scale=alt.Scale(scheme="viridis"), title="GW"),
                    tooltip=["team_name", "manager_name", "GW", "points"],
                )
                .properties(height=430)
            )
            st.altair_chart(chart, use_container_width=True)
            df2 = df.reset_index(drop=True)
            df2.insert(0, "rank", df2.index + 1)
            st.dataframe(top3_style(df2, "rank"), use_container_width=True, hide_index=True)

    with tab6:
        st.markdown("### Ctrl + Z Award")
        st.caption("Shows every TC/FH/BB use, the calculated score, and whether it qualifies. Winner is the lowest qualifying impact.")
        df = ctrl_z_breakdown_table(standings)

        if df is None or df.empty:
            st.info("No qualifying chip data available yet.")
        else:
            q = df[df["qualifies_for_ctrl_z"]].copy()
            if q.empty:
                st.warning("No chip usage currently meets the Ctrl + Z thresholds.")
            else:
                winner = q.sort_values("impact", ascending=True).iloc[0]
                c1, c2, c3 = st.columns(3)
                c1.metric("Current Ctrl + Z", winner["team_name"])
                c2.metric("Chip", winner["chip"])
                c3.metric("Impact", winner["impact"])

            chart_df = df.copy()
            chart_df["qualifies"] = chart_df["qualifies_for_ctrl_z"].map({True: "Qualifies", False: "Does not qualify"})
            chart = (
                alt.Chart(chart_df)
                .mark_circle(size=300)
                .encode(
                    x=alt.X("GW:O", title="Gameweek"),
                    y=alt.Y("impact:Q", title="Chip Impact"),
                    color=alt.Color("chip:N", scale=alt.Scale(scheme="set1")),
                    shape=alt.Shape("qualifies:N"),
                    tooltip=["team_name", "manager_name", "chip", "GW", "tc_score", "fh_score", "bb_score", "impact", "qualifies_for_ctrl_z"],
                )
                .properties(height=430)
            )
            st.altair_chart(chart, use_container_width=True)

            show = df.copy()
            show.insert(0, "rank", range(1, len(show) + 1))
            st.dataframe(top3_style(show, "rank"), use_container_width=True, hide_index=True)

    with tab7:
        st.markdown("### Wooden Spoon")
        st.caption("Lowest total points among active managers. Active = at least 25 GWs with transfers or chips; fallback uses lowest overall if none qualify.")
        df = wooden_spoon_table(standings)
        if winner_cards(df, "total_points"):
            chart = (
                alt.Chart(df.head(15))
                .mark_bar(cornerRadiusTopLeft=5, cornerRadiusTopRight=5)
                .encode(
                    x=alt.X("total_points:Q", title="Total Points"),
                    y=alt.Y("team_name:N", sort="x", title="Team"),
                    color=alt.Color("active_gws:Q", scale=alt.Scale(scheme="blues"), title="Active GWs"),
                    tooltip=["team_name", "manager_name", "total_points", "active_gws", "eligible"],
                )
                .properties(height=460)
            )
            st.altair_chart(chart, use_container_width=True)
            df2 = df.reset_index(drop=True)
            df2.insert(0, "rank", df2.index + 1)
            st.dataframe(top3_style(df2, "rank"), use_container_width=True, hide_index=True)


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
Highest net points gained from transfers, including hits.

### Troll Awards — ₹500
Ctrl + Z Award and Wooden Spoon.
""")
