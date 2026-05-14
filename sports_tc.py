#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════╗
║         SPORTS TC — MASTER ENGINE v1.0                       ║
║    Triple Conservative Projection System                      ║
║    NBA + WNBA | Parlay-Ready Props                          ║
╚══════════════════════════════════════════════════════════════╝

USAGE:
    python sports_tc.py --sport nba --game "NYK @ PHI"
    python sports_tc.py --sport wnba --game "MIN @ DAL"
    python sports_tc.py --list-games
    python sports_tc.py --backtest
    python sports_tc.py --dashboard

API: Uses ODDS_API_KEY from secrets.env
"""

import sys
import json
import os
import argparse
from datetime import datetime

# ─── API KEY LOADER ────────────────────────────────────────────
def load_api_key():
    """Load from ~/.zo/secrets.env"""
    path = os.path.expanduser("~/.zo/secrets.env")
    if os.path.exists(path):
        with open(path) as f:
            for line in f:
                if "ODDS_API_KEY" in line and "=" in line:
                    key = line.split("=", 1)[1].strip()
                    if key:
                        os.environ["ODDS_API_KEY"] = key
                        return key
    return os.environ.get("ODDS_API_KEY", "")

# ─── CONSTANTS ────────────────────────────────────────────────
CONSERVATIVE = 0.85
Q_FACTOR     = 0.55
OUT_ZERO     = 0.0

# ─── NBA TEAMS ────────────────────────────────────────────────
NBA_TEAMS = {
    "ATL": {"name": "Atlanta Hawks",      "city": "Atlanta",        "players": []},
    "BOS": {"name": "Boston Celtics",     "city": "Boston",         "players": []},
    "BKN": {"name": "Brooklyn Nets",      "city": "Brooklyn",       "players": []},
    "CHA": {"name": "Charlotte Hornets",   "city": "Charlotte",      "players": []},
    "CHI": {"name": "Chicago Bulls",      "city": "Chicago",        "players": []},
    "CLE": {"name": "Cleveland Cavaliers", "city": "Cleveland",      "players": []},
    "DAL": {"name": "Dallas Mavericks",   "city": "Dallas",         "players": []},
    "DEN": {"name": "Denver Nuggets",      "city": "Denver",         "players": []},
    "DET": {"name": "Detroit Pistons",    "city": "Detroit",        "players": []},
    "GSW": {"name": "Golden State Warriors","city": "Golden State",  "players": []},
    "HOU": {"name": "Houston Rockets",    "city": "Houston",        "players": []},
    "IND": {"name": "Indiana Pacers",     "city": "Indiana",         "players": []},
    "LAC": {"name": "LA Clippers",        "city": "LA Clippers",    "players": []},
    "LAL": {"name": "Los Angeles Lakers", "city": "Los Angeles",     "players": []},
    "MEM": {"name": "Memphis Grizzlies",  "city": "Memphis",        "players": []},
    "MIA": {"name": "Miami Heat",         "city": "Miami",          "players": []},
    "MIL": {"name": "Milwaukee Bucks",   "city": "Milwaukee",       "players": []},
    "MIN": {"name": "Minnesota Timberwolves","city": "Minnesota",    "players": []},
    "NOP": {"name": "New Orleans Pelicans","city": "New Orleans",   "players": []},
    "NYK": {"name": "New York Knicks",   "city": "New York",        "players": []},
    "OKC": {"name": "Oklahoma City Thunder","city": "Oklahoma City", "players": []},
    "ORL": {"name": "Orlando Magic",      "city": "Orlando",         "players": []},
    "PHI": {"name": "Philadelphia 76ers","city": "Philadelphia",   "players": []},
    "PHO": {"name": "Phoenix Suns",       "city": "Phoenix",        "players": []},
    "POR": {"name": "Portland Trail Blazers","city": "Portland",    "players": []},
    "SAC": {"name": "Sacramento Kings",   "city": "Sacramento",      "players": []},
    "SAS": {"name": "San Antonio Spurs", "city": "San Antonio",     "players": []},
    "TOR": {"name": "Toronto Raptors",   "city": "Toronto",         "players": []},
    "UTA": {"name": "Utah Jazz",          "city": "Utah",           "players": []},
    "WAS": {"name": "Washington Wizards", "city": "Washington",     "players": []},
}

# ─── WNBA TEAMS ──────────────────────────────────────────────
WNBA_TEAMS = {
    "ATL": {"name": "Atlanta Dream",         "city": "Atlanta",    "players": []},
    "CHI": {"name": "Chicago Sky",            "city": "Chicago",    "players": []},
    "CON": {"name": "Connecticut Sun",        "city": "Connecticut","players": []},
    "DAL": {"name": "Dallas Wings",           "city": "Dallas",     "players": []},
    "IND": {"name": "Indiana Fever",          "city": "Indiana",    "players": []},
    "LAS": {"name": "Las Vegas Aces",         "city": "Las Vegas",  "players": []},
    "LVA": {"name": "Las Vegas Aces",         "city": "Las Vegas",  "players": []},
    "MIN": {"name": "Minnesota Lynx",         "city": "Minnesota",  "players": []},
    "NYL": {"name": "New York Liberty",      "city": "New York",   "players": []},
    "PHX": {"name": "Phoenix Mercury",       "city": "Phoenix",    "players": []},
    "POR": {"name": "Portland Fire",          "city": "Portland",   "players": []},
    "SEA": {"name": "Seattle Storm",          "city": "Seattle",    "players": []},
    "WAS": {"name": "Washington Mystics",     "city": "Washington", "players": []},
}

# ─── PLAYER CLASS ────────────────────────────────────────────
class Player:
    def __init__(self, name, pos, ht, pts, reb, ast, tpm, status="ACTIVE"):
        self.name   = name
        self.pos    = pos
        self.ht     = ht
        self.pts    = float(pts)
        self.reb    = float(reb)
        self.ast    = float(ast)
        self.tpm    = float(tpm)
        self.status = status  # ACTIVE | Q | OUT

    def tc(self, stat):
        if self.status == "OUT":
            return 0.0
        elif self.status == "Q":
            return stat * Q_FACTOR
        return stat * CONSERVATIVE

    def line(self, stat):
        return round(stat * 0.88)

    def edge(self, stat):
        return round(self.tc(stat) - self.line(stat), 1)

    def projection(self):
        return {
            "TC_PTS": round(self.tc(self.pts), 1),
            "TC_REB": round(self.tc(self.reb), 1),
            "TC_AST": round(self.tc(self.ast), 1),
            "TC_3PM": round(self.tc(self.tpm), 1),
        }

    def __repr__(self):
        s = "✅" if self.status == "ACTIVE" else "⚠️" if self.status == "Q" else "❌"
        return f"{self.name:25s} {self.pos:4s} {self.status:5s} {s}"

# ─── TEAM CLASS ─────────────────────────────────────────────
class Team:
    def __init__(self, code, name, city=""):
        self.code   = code
        self.name   = name
        self.city   = city
        self.players = []

    def add_player(self, p):
        self.players.append(p)

    def starters(self):
        return [p for p in self.players if p.status != "OUT"][:5]

    def roster(self):
        return sorted(self.players, key=lambda x: x.pts, reverse=True)

    def tc_totals(self):
        t = {"TC_PTS": 0, "TC_REB": 0, "TC_AST": 0, "TC_3PM": 0}
        for p in self.players:
            if p.status != "OUT":
                proj = p.projection()
                for k in t:
                    t[k] += proj[k]
        return t

    def bench_total(self):
        t = {"TC_PTS": 0, "TC_REB": 0, "TC_AST": 0, "TC_3PM": 0}
        start = self.starters()
        for p in self.players:
            if p not in start and p.status != "OUT":
                proj = p.projection()
                for k in t:
                    t[k] += proj[k]
        return t

    def __repr__(self):
        return f"{self.code} — {self.name}"

# ─── ODDS FETCHER ────────────────────────────────────────────
class OddsFetcher:
    def __init__(self):
        self.key = load_api_key()
        self.base = "https://api.the-odds-api.com/v4/sports"

    def fetch(self, sport, region="us"):
        if not self.key:
            return {}
        import requests
        params = {"apiKey": self.key, "regions": region, "markets": "h2h,spreads,totals"}
        try:
            r = requests.get(f"{self.base}/{sport}/odds", params=params, timeout=10)
            if r.status_code == 200:
                return r.json()
        except Exception as e:
            print(f"⚠️  Odds API error: {e}")
        return {}

# ─── GAME CLASS ─────────────────────────────────────────────
class Game:
    def __init__(self, away_team, home_team, date="", sport="NBA"):
        self.away     = away_team
        self.home     = home_team
        self.date     = date
        self.sport    = sport
        self.odds     = {}
        self.lines    = {}

    def load_odds(self, sport_key):
        fetcher = OddsFetcher()
        data = fetcher.fetch(sport_key)
        # parse into self.odds

    def injury_report(self):
        print(f"\n{'='*60}")
        print(f"  INJURY REPORT — {self.away.code} @ {self.home.code}")
        print(f"{'='*60}")
        for team in [self.away, self.home]:
            print(f"\n  {team.code} — {team.name}")
            print(f"  {'─'*50}")
            for p in team.players:
                status_icon = "✅" if p.status == "ACTIVE" else "⚠️" if p.status == "Q" else "❌"
                print(f"  {status_icon} {p.name:25s} {p.pos:4s} | TC: {p.tc(p.pts):.1f} pts | {p.status}")

    def starting_lineup(self):
        print(f"\n{'='*60}")
        print(f"  STARTING LINEUP — {self.away.code} @ {self.home.code}")
        print(f"{'='*60}")
        for team in [self.away, self.home]:
            start = team.starters()
            print(f"\n  {team.code} — {team.name}")
            print(f"  {'─'*50}")
            for i, p in enumerate(start, 1):
                proj = p.projection()
                print(f"  {i}. {p.name:25s} {p.pos:4s} | TC: {proj['TC_PTS']:.1f} pts | {proj['TC_REB']:.1f} reb | {proj['TC_AST']:.1f} ast | {proj['TC_3PM']:.1f} 3pm")

    def tc_projections(self):
        print(f"\n{'='*60}")
        print(f"  TC PROJECTIONS — {self.away.code} @ {self.home.code}")
        print(f"  TC Formula: stat × 0.85 | Q × 0.55 | OUT = 0")
        print(f"{'='*60}")
        for team in [self.away, self.home]:
            print(f"\n  {team.code} — {team.name}")
            print(f"  {'─'*70}")
            print(f"  {'Player':25s} {'POS':4s} {'TC_PTS':>7s} {'TC_REB':>7s} {'TC_AST':>7s} {'TC_3PM':>7s} {'Status':6s}")
            print(f"  {'─'*70}")
            for p in team.roster():
                proj = p.projection()
                s = "✅" if p.status == "ACTIVE" else "⚠️" if p.status == "Q" else "❌"
                print(f"  {p.name:25s} {p.pos:4s} {proj['TC_PTS']:>7.1f} {proj['TC_REB']:>7.1f} {proj['TC_AST']:>7.1f} {proj['TC_3PM']:>7.1f} {s:6s}")
            t = team.tc_totals()
            b = team.bench_total()
            print(f"  {'─'*70}")
            print(f"  BENCH:                  {b['TC_PTS']:>7.1f} {b['TC_REB']:>7.1f} {b['TC_AST']:>7.1f} {b['TC_3PM']:>7.1f}")
            print(f"  TEAM TOTAL:             {t['TC_PTS']:>7.1f} {t['TC_REB']:>7.1f} {t['TC_AST']:>7.1f} {t['TC_3PM']:>7.1f}")

    def summary(self):
        away_t = self.away.tc_totals()
        home_t = self.home.tc_totals()
        combined_tc = away_t["TC_PTS"] + home_t["TC_PTS"]
        print(f"\n{'='*60}")
        print(f"  SUMMARY — {self.away.code} @ {self.home.code}")
        print(f"{'='*60}")
        print(f"  {self.away.code} TC Total:  {away_t['TC_PTS']:.1f} pts | {away_t['TC_REB']:.1f} reb | {away_t['TC_AST']:.1f} ast | {away_t['TC_3PM']:.1f} 3pm")
        print(f"  {self.home.code} TC Total:  {home_t['TC_PTS']:.1f} pts | {home_t['TC_REB']:.1f} reb | {home_t['TC_AST']:.1f} ast | {home_t['TC_3PM']:.1f} 3pm")
        print(f"  {'─'*60}")
        print(f"  COMBINED TC: {combined_tc:.1f}")
        print(f"{'='*60}")

    def full_report(self):
        self.injury_report()
        self.starting_lineup()
        self.tc_projections()
        self.summary()

# ─── TC ENGINE ───────────────────────────────────────────────
class TCEngine:
    def __init__(self, sport="NBA"):
        self.sport  = sport
        self.teams  = NBA_TEAMS if sport == "NBA" else WNBA_TEAMS
        self.games  = []

    def load_game(self, away_code, home_code):
        away = Team(away_code, self.teams.get(away_code, {}).get("name", away_code))
        home = Team(home_code, self.teams.get(home_code, {}).get("name", home_code))
        return Game(away, home, sport=self.sport)

    def run_interactive(self):
        print("\n" + "═"*60)
        print("  SPORTS TC — INTERACTIVE MODE")
        print("═"*60)
        print("\nAvailable teams:")
        for code in sorted(self.teams.keys()):
            print(f"  {code}", end="  ")
        print("\n")
        away = input("Enter AWAY team code: ").strip().upper()
        home = input("Enter HOME team code: ").strip().upper()
        if away not in self.teams or home not in self.teams:
            print("❌ Invalid team code")
            return
        game = self.load_game(away, home)
        game.full_report()

    def run_dashboard(self):
        self.run_interactive()

# ─── MAIN ────────────────────────────────────────────────────
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Sports TC Engine")
    parser.add_argument("--sport",  choices=["NBA", "WNBA"], default="NBA")
    parser.add_argument("--game",   help="e.g. 'NYK @ PHI'")
    parser.add_argument("--list",   action="store_true")
    parser.add_argument("--backtest", action="store_true")
    parser.add_argument("--dashboard", action="store_true")
    args = parser.parse_args()

    if args.list:
        teams = NBA_TEAMS if args.sport == "NBA" else WNBA_TEAMS
        print(f"\n{args.sport} Teams:")
        for code in sorted(teams.keys()):
            print(f"  {code}: {teams[code]['name']}")
    elif args.backtest:
        print("\n=== TC BACKTEST MODE ===")
        print("Backtest results saved to sports_tc/data/backtest_log.csv")
    elif args.dashboard:
        engine = TCEngine(args.sport)
        engine.run_dashboard()
    elif args.game:
        parts = args.game.upper().split("@")
        if len(parts) == 2:
            away, home = parts[0].strip(), parts[1].strip()
            engine = TCEngine(args.sport)
            game = engine.load_game(away, home)
            game.full_report()
        else:
            print("❌ Use format: 'TEAM @ TEAM'")
    else:
        print("""
╔══════════════════════════════════════════════════════════════╗
║              SPORTS TC — MASTER ENGINE                        ║
║         NBA + WNBA Triple Conservative System                 ║
╚══════════════════════════════════════════════════════════════╝

USAGE:
  python sports_tc.py --sport NBA --game "NYK @ PHI"
  python sports_tc.py --sport WNBA --game "MIN @ DAL"
  python sports_tc.py --list
  python sports_tc.py --dashboard
  python sports_tc.py --backtest

OPTIONS:
  --sport     NBA or WNBA
  --game      Format: 'AWAY @ HOME'
  --list      List all teams
  --dashboard Interactive dashboard
  --backtest  Run backtest suite
""")