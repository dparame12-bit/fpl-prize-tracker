import requests
import pandas as pd
import streamlit as st

BASE_URL = "https://fantasy.premierleague.com/api"

@st.cache_data(ttl=60 * 60)
def get_bootstrap():
    return requests.get(f"{BASE_URL}/bootstrap-static/", timeout=30).json()

@st.cache_data(ttl=60 * 60)
def get_classic_league(league_id: int, page: int = 1):
    url = f"{BASE_URL}/leagues-classic/{league_id}/standings/?page_standings={page}"
    return requests.get(url, timeout=30).json()

@st.cache_data(ttl=60 * 60)
def get_all_league_standings(league_id: int) -> pd.DataFrame:
    rows = []
    page = 1
    while True:
        data = get_classic_league(league_id, page)
        standings = data.get("standings", {})
        results = standings.get("results", [])
        rows.extend(results)
        if not standings.get("has_next"):
            break
        page += 1

    df = pd.DataFrame(rows)
    if df.empty:
        return df

    keep_cols = [
        "entry", "entry_name", "player_name", "rank", "last_rank",
        "total", "event_total"
    ]
    df = df[[c for c in keep_cols if c in df.columns]]
    df = df.rename(columns={
        "entry": "entry_id",
        "entry_name": "team_name",
        "player_name": "manager_name",
        "rank": "current_rank",
        "last_rank": "last_rank",
        "total": "total_points",
        "event_total": "gw_points",
    })
    return df

@st.cache_data(ttl=60 * 60)
def get_manager_history(entry_id: int):
    return requests.get(f"{BASE_URL}/entry/{entry_id}/history/", timeout=30).json()

@st.cache_data(ttl=60 * 60)
def get_manager_picks(entry_id: int, event_id: int):
    return requests.get(f"{BASE_URL}/entry/{entry_id}/event/{event_id}/picks/", timeout=30).json()

@st.cache_data(ttl=60 * 60)
def get_manager_transfers(entry_id: int):
    return requests.get(f"{BASE_URL}/entry/{entry_id}/transfers/", timeout=30).json()

def current_gw() -> int:
    data = get_bootstrap()
    events = data.get("events", [])
    current = [e for e in events if e.get("is_current")]
    if current:
        return int(current[0]["id"])
    finished = [e for e in events if e.get("finished")]
    return max([int(e["id"]) for e in finished], default=1)

def events_df() -> pd.DataFrame:
    return pd.DataFrame(get_bootstrap().get("events", []))
