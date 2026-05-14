import streamlit as st
import pandas as pd
import subprocess
import json
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

st.set_page_config(page_title="Sports TC", page_icon="🏀", layout="wide")
st.title("🏀 Sports TC — Triple Conservative Projections")

SPORT = st.sidebar.selectbox("Sport", ["NBA", "WNBA"])
GAME = st.text_input("Game", "NYL @ POR")
INJURY = st.checkbox("Injury Report", True)

if st.button("Run Projection"):
    with st.spinner("Running TC engine..."):
        cmd = [
            sys.executable, "sports_tc.py",
            "--sport", SPORT,
            "--game", GAME
        ]
        if INJURY:
            cmd.append("--injury")
        result = subprocess.run(cmd, capture_output=True, text=True, cwd=os.path.dirname(__file__))
        output = result.stdout + result.stderr
        st.text(output)

        lines = output.strip().split("\n")
        in_table = False
        headers = []
        rows = []
        for line in lines:
            if "─" * 5 in line and ("Player" in line or "POS" in line):
                in_table = True
                continue
            if in_table:
                if line.strip() == "" or "BENCH" in line or "TEAM TOTAL" in line:
                    break
                parts = [p.strip() for p in line.split("|") if p.strip()]
                if len(parts) >= 5:
                    rows.append(parts)

        if rows and len(rows[0]) >= 4:
            st.subheader(f"{GAME} — TC Roster Projections")
            df = pd.DataFrame(rows, columns=["Player", "POS", "TC_PTS", "TC_REB", "TC_AST", "TC_3PM", "Status"] if len(rows[0]) == 7 else ["Player", "POS", "TC_PTS", "TC_REB", "TC_AST", "TC_3PM", "Status"])
            st.dataframe(df, use_container_width=True)
        else:
            st.text(output)

st.markdown("---")
st.caption("Sports TC v3.0 — TC = stat × 0.85 | Q = 0.65 | OUT = 0")