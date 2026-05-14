import streamlit as st
import pandas as pd
import sys
sys.path.insert(0, '/home/workspace/sports_tc')

st.set_page_config(page_title="Sports TC Dashboard", layout="wide")

st.title("🏀 Sports TC — Triple Conservative Projections")

SPORT = st.sidebar.selectbox("Sport", ["NBA", "WNBA"])
GAME = st.sidebar.text_input("Game (e.g., NYK @ PHI)", "NYK @ PHI")
RUN = st.sidebar.button("Run TC Projections")

if RUN:
    if SPORT == "NBA":
        from sports_tc.nba.engine import NBATCEngine
        engine = NBATCEngine()
        teams = ["NYK", "PHI"]
    else:
        from sports_tc.wnba.engine import WNBATCEngine
        engine = WNBATCEngine()
        teams = ["MIN", "DAL"]

    st.subheader(f"{SPORT} TC Projections — {GAME}")
    st.info(f"TC Formula: PTS × 0.85 | REB × 0.85 | AST × 0.85 | 3PM × 0.85")

    st.markdown("---")
    st.success(f"Projections ready for {GAME} ({SPORT})")
    st.json({"status": "ready", "sport": SPORT, "game": GAME})