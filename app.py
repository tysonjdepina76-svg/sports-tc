import streamlit as st
import pandas as pd
import subprocess
import json
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

st.set_page_config(page_title="Sports TC", page_icon="🏀", layout="wide")

# ── Sidebar controls ──
st.sidebar.title("🏀 Sports TC")
sport = st.sidebar.selectbox("Sport", ["WNBA", "NBA"], index=0)
game = st.sidebar.text_input("Game", "NYL @ POR")
show_injury = st.sidebar.checkbox("Injury Adjustments", value=True)
refresh = st.sidebar.button("↻ Refresh")

# ── Header ──
st.title("Sports TC — Triple Conservative Projections")
st.markdown(f"**Sport:** {sport} | **Game:** {game} | **Injury Adj:** {'Yes' if show_injury else 'No'}")

# ── Run the TC engine ──
with st.spinner("Running TC engine..."):
    cmd = [
        sys.executable, "sports_tc.py",
        "--sport", sport,
        "--game", game
    ]
    if show_injury:
        cmd.append("--injury")
    
    result = subprocess.run(cmd, capture_output=True, text=True, cwd=os.path.dirname(__file__))
    output = result.stdout + result.stderr

# ── Parse roster table ──
def parse_roster(output):
    lines = output.strip().split("\n")
    in_table = False
    rows = []
    for line in lines:
        if "─" * 3 in line and ("Player" in line or "POS" in line):
            in_table = True
            continue
        if in_table:
            if line.strip() == "" or "BENCH" in line or "TEAM TOTAL" in line or "=" in line:
                if rows:
                    break
                continue
            parts = [p.strip() for p in line.split("|") if p.strip()]
            if len(parts) >= 6:
                rows.append(parts)
    return rows

# ── Team totals header ──
st.markdown("---")

# Split output into sections
sections = output.split("═" * 30)
for section in sections:
    lines = section.strip().split("\n")
    if not lines:
        continue
    
    # Look for game headers
    game_lines = [l for l in lines if "@" in l or "TC ROSTER" in l or "SLATE" in l]
    team_lines = [l for l in lines if any(t in l for t in ["NYL","POR","LVA","IND","MIN","DAL","CON","CHI","ATL","SEA","NBA"])]
    
    # Show game header
    for gl in game_lines[:2]:
        if gl.strip():
            st.subheader(f"🏀 {gl.strip()}")
    
    # Parse and display roster
    roster_rows = parse_roster(section)
    if roster_rows:
        cols = ["Player", "POS", "TC_PTS", "TC_REB", "TC_AST", "TC_3PM", "Status"]
        df = pd.DataFrame(roster_rows, columns=cols[:len(roster_rows[0])])
        st.dataframe(df, use_container_width=True)
    
    # Show team totals
    for line in lines:
        if "TEAM TOTAL" in line or "BENCH" in line:
            st.markdown(f"`{line.strip()}`")

# ── Raw output fallback ──
if "Player" not in output:
    st.text_area("TC Output", output, height=400)

st.markdown("---")
st.caption("Sports TC v3.0 | TC = stat × 0.85 | Q = 0.65 | OUT = 0")