import streamlit as st
from config import APP_PASSWORD

def password_gate():
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False

    if st.session_state.authenticated:
        return True

    st.title("WTL FPL Prize Tracker")
    password = st.text_input("Enter app password", type="password")

    if st.button("Login"):
        if password == APP_PASSWORD:
            st.session_state.authenticated = True
            st.rerun()
        else:
            st.error("Incorrect password")

    return False

def money(x):
    try:
        return f"₹{int(x):,}"
    except Exception:
        return x
