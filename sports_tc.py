#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════╗
║           SPORTS TC v3.0 — Triple Conservative Engine        ║
║               NBA + WNBA | pts × 0.85 | Q × 0.65             ║
╚══════════════════════════════════════════════════════════════╝

Usage:
  python sports_tc.py --sport WNBA --game "NYL @ POR"
  python sports_tc.py --sport NBA --game "NYK @ PHI"
  python sports_tc.py --list --sport WNBA
  python sports_tc.py --backtest --sport NBA
  python sports_tc.py --dashboard

Template: TC PTS | TC REB | TC AST | TC 3PM per player
"""

import sys
import os
import json
import argparse
import warnings
from datetime import datetime

warnings.filterwarnings("ignore")

# ─── CONSTANTS ────────────────────────────────────────────────
CONS   = 0.85   # conservative multiplier
Q_MULT = 0.65   # questionable multiplier
OUT_Z  = 0.0    # out = zero

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
        self.status = status   # ACTIVE | Q | OUT

    def tc(self, stat):
        if self.status == "OUT":   return 0.0
        if self.status == "Q":    return round(stat * Q_MULT, 1)
        return round(stat * CONS, 1)

    def proj(self):
        return {
            "TC_PTS": self.tc(self.pts),
            "TC_REB": self.tc(self.reb),
            "TC_AST": self.tc(self.ast),
            "TC_3PM": self.tc(self.tpm),
        }

    def __repr__(self):
        icon = "✅" if self.status == "ACTIVE" else "⚠️" if self.status == "Q" else "❌"
        return f"{self.name:25s} {self.pos:4s} {self.status:5s} {icon}"

# ─── TEAM CLASS ─────────────────────────────────────────────
class Team:
    def __init__(self, code, name, city=""):
        self.code    = code
        self.name    = name
        self.city    = city
        self.players = []

    def add(self, p):
        self.players.append(p)

    def starters(self):
        return [p for p in self.players if p.status != "OUT"][:5]

    def roster(self):
        return sorted(self.players, key=lambda x: x.pts, reverse=True)

    def totals(self):
        t = {"TC_PTS": 0, "TC_REB": 0, "TC_AST": 0, "TC_3PM": 0}
        for p in self.players:
            if p.status != "OUT":
                for k, v in p.proj().items():
                    t[k] += v
        return {k: round(v, 1) for k, v in t.items()}

    def bench(self):
        t = {"TC_PTS": 0, "TC_REB": 0, "TC_AST": 0, "TC_3PM": 0}
        for p in self.players:
            if p not in self.starters() and p.status != "OUT":
                for k, v in p.proj().items():
                    t[k] += v
        return {k: round(v, 1) for k, v in t.items()}

    def load_roster(self, roster_list):
        for p in roster_list:
            self.add(p)

# ─── NBA TEAMS ────────────────────────────────────────────────
NBA_TEAMS = {
    "NYK": "New York Knicks",    "PHI": "Philadelphia 76ers",
    "BOS": "Boston Celtics",      "CLE": "Cleveland Cavaliers",
    "OKC": "Oklahoma City Thunder","MIN": "Minnesota Timberwolves",
    "DEN": "Denver Nuggets",      "DET": "Detroit Pistons",
    "SAS": "San Antonio Spurs",   "MIA": "Miami Heat",
    "MIL": "Milwaukee Bucks",     "LAL": "Los Angeles Lakers",
    "GSW": "Golden State Warriors","LAC": "LA Clippers",
    "DAL": "Dallas Mavericks",    "PHX": "Phoenix Suns",
    "IND": "Indiana Pacers",       "HOU": "Houston Rockets",
    "ATL": "Atlanta Hawks",       "CHA": "Charlotte Hornets",
    "CHI": "Chicago Bulls",        "BKN": "Brooklyn Nets",
    "NOP": "New Orleans Pelicans","SAC": "Sacramento Kings",
    "POR": "Portland Trail Blazers","UTA": "Utah Jazz",
    "TOR": "Toronto Raptors",     "WAS": "Washington Wizards",
    "ORL": "Orlando Magic",
}

# ─── WNBA TEAMS ──────────────────────────────────────────────
WNBA_TEAMS = {
    "NYL": "New York Liberty",   "POR": "Portland Fire",
    "MIN": "Minnesota Lynx",    "DAL": "Dallas Wings",
    "LVA": "Las Vegas Aces",    "IND": "Indiana Fever",
    "PHX": "Phoenix Mercury",   "SEA": "Seattle Storm",
    "CON": "Connecticut Sun",   "CHI": "Chicago Sky",
    "ATL": "Atlanta Dream",     "WAS": "Washington Mystics",
    "LAS": "Las Vegas Aces",
}

# ─── NBA ROSTERS ─────────────────────────────────────────────
NBA_ROSTERS = {
    "NYK": [
        Player("Jalen Brunson",          "G","6-2", 20.5, 3.5, 6.5, 2.0, "ACTIVE"),
        Player("OG Anunoby",             "F","6-7", 16.0, 5.0, 2.0, 2.0, "ACTIVE"),
        Player("Julius Randle",          "F","6-4", 18.5, 9.0, 4.5, 1.8, "ACTIVE"),
        Player("Mikal Bridges",          "F","6-6", 14.5, 4.5, 3.0, 2.0, "ACTIVE"),
        Player("Donte DiVincenzo",       "G","6-4", 12.0, 4.0, 3.0, 2.5, "ACTIVE"),
        Player("Josh Hart",              "G","6-3", 10.5, 4.5, 3.5, 1.5, "ACTIVE"),
        Player("Precious Achiuwa",       "F","6-8",  7.5, 5.0, 1.0, 0.8, "ACTIVE"),
        Player("Bojan Bogdanovic",       "F","6-6",  9.5, 3.0, 1.5, 1.8, "Q"),
        Player("Mitchell Robinson",     "C","7-0",  7.0, 8.0, 1.0, 0.0, "ACTIVE"),
        Player("Jerome Robinson",        "G","6-5",  5.0, 2.0, 1.5, 0.8, "ACTIVE"),
    ],
    "PHI": [
        Player("Tyrese Maxey",           "G","6-2", 22.0, 4.0, 5.5, 2.5, "ACTIVE"),
        Player("Paul George",            "F","6-8", 18.0, 5.5, 4.0, 2.8, "ACTIVE"),
        Player("Joel Embiid",            "C","7-0", 28.5,11.0, 5.5, 1.8, "Q"),
        Player("Jared McCain",           "G","6-4", 14.0, 3.5, 3.0, 2.0, "ACTIVE"),
        Player("Guerschon Yabusele",     "F","6-8", 11.0, 5.5, 1.5, 1.2, "ACTIVE"),
        Player("Justin Edwards",         "F","6-8",  7.5, 3.5, 1.0, 0.8, "ACTIVE"),
        Player("Kelly Oubre Jr.",         "F","6-5", 13.0, 5.0, 2.0, 1.5, "ACTIVE"),
        Player("Eric Gordon",            "G","6-3",  9.0, 2.0, 2.5, 2.0, "ACTIVE"),
        Player("Kyle Lowry",             "G","6-0",  7.5, 3.0, 5.0, 1.3, "ACTIVE"),
        Player("Mo Bamba",               "C","7-0",  6.5, 5.5, 1.0, 0.8, "OUT"),
    ],
    "BOS": [
        Player("Jayson Tatum",           "F","6-8", 25.5, 8.0, 5.0, 2.8, "ACTIVE"),
        Player("Jaylen Brown",           "F","6-6", 23.0, 6.0, 4.0, 2.5, "ACTIVE"),
        Player("Kristaps Porzingis",     "C","7-1", 20.0, 7.5, 2.5, 2.0, "ACTIVE"),
        Player("Derrick White",          "G","6-4", 15.5, 4.5, 4.5, 2.2, "ACTIVE"),
        Player("Jrue Holiday",           "G","6-4", 14.5, 5.0, 6.0, 2.0, "ACTIVE"),
        Player("Al Horford",             "F","6-9", 11.0, 5.5, 3.5, 1.8, "ACTIVE"),
        Player("Payton Pritchard",       "G","6-1",  9.0, 2.5, 3.0, 2.0, "ACTIVE"),
        Player("Sam Hauser",             "F","6-5",  8.0, 3.5, 1.5, 1.8, "ACTIVE"),
        Player("Luke Kornet",            "C","7-0",  6.0, 4.0, 1.0, 0.5, "ACTIVE"),
        Player("Neemias Queta",           "C","7-0",  5.5, 4.0, 0.5, 0.0, "ACTIVE"),
    ],
    "CLE": [
        Player("Donovan Mitchell",       "G","6-1", 24.5, 5.0, 4.5, 3.0, "ACTIVE"),
        Player("Darius Garland",         "G","6-1", 20.0, 3.5, 6.0, 2.5, "ACTIVE"),
        Player("Evan Mobley",            "F","6-11",18.0, 9.0, 3.5, 1.2, "ACTIVE"),
        Player("Jarrett Allen",          "C","6-9", 14.0, 8.0, 2.0, 0.5, "ACTIVE"),
        Player("Max Strus",              "F","6-5", 12.5, 4.5, 3.5, 2.5, "ACTIVE"),
        Player("Isaac Okoro",            "G","6-5", 10.0, 3.5, 3.0, 1.2, "ACTIVE"),
        Player("Georges Niang",          "F","6-5",  9.0, 3.0, 1.5, 2.0, "ACTIVE"),
        Player("Caris LeVert",            "G","6-5", 11.5, 3.5, 3.5, 1.8, "Q"),
        Player("Tristan Thompson",        "C","6-9",  6.0, 5.5, 1.0, 0.0, "ACTIVE"),
        Player("Ty Jerome",              "G","6-5",  5.5, 2.0, 2.5, 1.0, "ACTIVE"),
    ],
    "OKC": [
        Player("Shai Gilgeous-Alexander","G","6-6",27.5, 5.5, 6.5, 2.2, "ACTIVE"),
        Player("Jalen Williams",         "F","6-5", 19.0, 4.5, 4.0, 2.0, "ACTIVE"),
        Player("Chet Holmgren",          "C","7-0", 16.0, 7.5, 2.5, 1.5, "ACTIVE"),
        Player("Lu Dort",                "G","6-4", 13.5, 4.0, 2.5, 2.5, "ACTIVE"),
        Player("Isaiah Hartenstein",      "C","6-11",12.0, 8.5, 3.5, 0.8, "ACTIVE"),
        Player("Josh Giddey",            "G","6-8", 12.5, 6.5, 5.5, 1.5, "ACTIVE"),
        Player("Jaylen Duren",           "C","6-10", 8.5, 5.5, 1.5, 0.3, "ACTIVE"),
        Player("Cason Wallace",           "G","6-4",  8.0, 2.5, 2.0, 1.5, "ACTIVE"),
        Player("Kenrich Williams",        "F","6-7",  7.0, 4.5, 2.0, 1.0, "ACTIVE"),
    ],
    "MIN": [
        Player("Anthony Edwards",        "G","6-4", 26.0, 5.5, 5.0, 3.2, "ACTIVE"),
        Player("Julius Randle",          "F","6-4", 18.5, 9.0, 4.5, 1.8, "ACTIVE"),
        Player("Rudy Gobert",            "C","7-1", 14.0,11.5, 1.5, 0.0, "ACTIVE"),
        Player("Jaden McDaniels",        "F","6-9", 12.0, 4.5, 2.0, 1.5, "ACTIVE"),
        Player("Mike Conley",            "G","6-0", 11.0, 3.0, 5.5, 2.0, "ACTIVE"),
        Player("Naz Reid",               "C","6-9", 13.5, 5.5, 2.5, 1.8, "ACTIVE"),
        Player("Nickeil Alexander-Walker","G","6-5",11.5, 3.0, 2.5, 2.0, "ACTIVE"),
        Player("Kyle Anderson",          "F","6-9",  8.5, 4.5, 3.5, 0.8, "ACTIVE"),
    ],
    "DEN": [
        Player("Nikola Jokic",           "C","6-11",26.5,12.0, 9.5, 1.8, "ACTIVE"),
        Player("Jamal Murray",           "G","6-4", 21.5, 4.5, 5.5, 2.5, "ACTIVE"),
        Player("Michael Porter Jr.",     "F","6-10",16.5, 6.5, 2.0, 2.5, "ACTIVE"),
        Player("Aaron Gordon",           "F","6-8", 14.0, 5.5, 2.5, 1.2, "ACTIVE"),
        Player("Kentavious Caldwell-Pope","G","6-5", 11.5, 3.5, 2.0, 2.0, "ACTIVE"),
        Player("Christian Braun",         "G","6-5",  8.5, 3.5, 1.5, 1.0, "ACTIVE"),
        Player("Peyton Watson",          "F","6-8",  7.5, 3.0, 1.5, 0.8, "ACTIVE"),
    ],
    "DET": [
        Player("Cade Cunningham",        "G","6-6", 22.0, 5.5, 7.5, 2.2, "ACTIVE"),
        Player("Jaden Ivey",            "G","6-4", 17.5, 4.5, 4.0, 2.0, "ACTIVE"),
        Player("Jalen Duren",           "C","6-10",13.5, 8.0, 2.0, 0.5, "ACTIVE"),
        Player("Ausar Thompson",        "F","6-7", 12.5, 5.5, 3.5, 1.2, "ACTIVE"),
        Player("Tim Hardaway Jr.",      "F","6-5", 14.0, 4.0, 2.5, 2.5, "ACTIVE"),
        Player("Marcus Sasser",         "G","6-2", 10.5, 2.5, 3.0, 1.8, "ACTIVE"),
        Player("Simone Fontecchio",      "F","6-8",  8.5, 3.5, 1.5, 1.2, "ACTIVE"),
        Player("Killian Hayes",           "G","6-5",  9.0, 3.0, 4.5, 1.2, "Q"),
    ],
    "SAS": [
        Player("Victor Wembanyama",     "C","7-4", 23.5,10.5, 4.0, 2.5, "ACTIVE"),
        Player("Chris Paul",            "G","6-0", 12.0, 4.0, 9.0, 1.8, "ACTIVE"),
        Player("Devin Vassell",         "F","6-5", 17.5, 4.5, 3.5, 2.5, "ACTIVE"),
        Player("Jeremy Sochan",         "F","6-9", 12.0, 6.0, 3.5, 1.2, "ACTIVE"),
        Player("Keldon Johnson",        "F","6-5", 15.0, 5.0, 2.5, 2.2, "ACTIVE"),
        Player("Devonte Graham",        "G","6-1",  9.5, 2.5, 4.5, 2.0, "ACTIVE"),
        Player("Zach Collins",          "C","6-11",10.0, 5.5, 2.5, 0.8, "Q"),
        Player("Sandro Mamukelashvili", "F","6-10", 8.5, 4.5, 1.5, 0.8, "ACTIVE"),
    ],
}

# ─── WNBA ROSTERS ────────────────────────────────────────────
WNBA_ROSTERS = {
    "NYL": [
        Player("Breanna Stewart",       "F","6-4", 19.5, 8.5, 4.0, 2.4, "ACTIVE"),
        Player("Sabrina Ionescu",       "G","5-11",17.5, 5.5, 7.1, 3.2, "ACTIVE"),
        Player("Jonquel Jones",         "C","6-6", 15.0, 9.0, 2.9, 1.5, "ACTIVE"),
        Player("Courtney Vandersloot",  "G","5-8", 10.9, 4.0, 6.5, 1.8, "ACTIVE"),
        Player("Betnijah Laney",        "F","6-0", 10.6, 3.0, 1.6, 1.0, "Q"),   # ankle Q
        Player("Kayla Thornton",        "F","6-2",  6.5, 4.0, 0.9, 0.8, "ACTIVE"),
        Player("Sonia",                 "G","5-9",  6.0, 2.0, 1.5, 0.5, "ACTIVE"),
        Player("Han Xu",               "C","6-11",  7.0, 4.0, 0.5, 0.3, "ACTIVE"),
    ],
    "POR": [
        Player("Te'a Cooper",          "G","5-9", 13.5, 3.5, 4.0, 1.5, "ACTIVE"),
        Player("Alexis",               "G","5-10",10.9, 2.9, 3.5, 1.2, "ACTIVE"),
        Player("Aaliyah",              "F","6-2",  9.5, 4.9, 0.9, 0.8, "ACTIVE"),
        Player("Isabelle",             "C","6-4",  8.5, 6.5, 0.5, 0.0, "ACTIVE"),
        Player("Nika",                 "F","6-3",  8.0, 5.0, 1.0, 0.0, "OUT"),  # knee OUT
        Player("Jessika",               "G","5-7",  6.0, 1.5, 2.0, 0.5, "ACTIVE"),
        Player("Kate",                 "F","6-2",  5.5, 2.9, 0.5, 0.3, "ACTIVE"),
        Player("Sami",                 "G","5-6",  4.5, 0.9, 0.9, 0.3, "ACTIVE"),
    ],
    "MIN": [
        Player("Naphessa Collier",     "F","6-0", 16.9, 5.5, 3.4, 1.8, "ACTIVE"),
        Player("Kayla McCollough",     "G","5-11",14.1, 3.5, 2.0, 1.0, "Q"),
        Player("Alana",                "C","6-4", 11.5, 7.0, 1.5, 0.5, "ACTIVE"),
        Player("Natasha",             "G","5-8", 11.0, 2.9, 5.5, 1.5, "ACTIVE"),
        Player("Diamond",              "F","6-2",  8.5, 4.0, 1.0, 0.8, "ACTIVE"),
        Player("Nele",                 "F","6-3",  6.0, 3.0, 0.5, 0.3, "ACTIVE"),
        Player("Olivia",               "G","5-7",  4.5, 1.0, 1.5, 0.4, "ACTIVE"),
        Player("Nara",                 "G","5-9",  3.5, 0.8, 0.8, 0.3, "ACTIVE"),
    ],
    "DAL": [
        Player("Arielle",              "G","5-10",16.5, 4.5, 4.5, 2.0, "ACTIVE"),
        Player("Moriah",               "G","6-0", 14.0, 4.0, 3.5, 1.3, "ACTIVE"),
        Player("Caitlin",              "F","6-3", 12.5, 6.0, 1.5, 0.8, "ACTIVE"),
        Player("Naomi",                "C","6-5", 10.5, 7.0, 1.0, 0.5, "Q"),
        Player("Satou",                "F","6-2",  9.0, 4.5, 1.5, 0.8, "ACTIVE"),
        Player("Lindsay",              "G","5-9",  7.5, 2.0, 2.5, 0.9, "ACTIVE"),
        Player("Jaiden",               "F","6-3",  5.5, 3.0, 0.5, 0.3, "ACTIVE"),
        Player("Awak",                 "G","5-8",  4.0, 1.0, 1.0, 0.3, "ACTIVE"),
    ],
    "LVA": [
        Player("A'ja Wilson",         "F","6-4", 22.5,10.0, 3.5, 1.5, "ACTIVE"),
        Player("Chelsea Gray",         "G","5-11",14.5, 4.0, 5.0, 1.8, "ACTIVE"),
        Player("Kia",                  "C","6-5", 12.5, 7.5, 1.5, 0.5, "ACTIVE"),
        Player("Jackie",              "G","5-10",11.0, 3.5, 4.0, 1.5, "ACTIVE"),
        Player("Alysha",              "F","6-2",  8.5, 4.0, 1.0, 0.8, "Q"),
        Player("Kayla",               "G","5-9",  6.5, 1.5, 2.0, 0.8, "ACTIVE"),
        Player("Sydney",               "F","6-3",  5.5, 3.0, 0.5, 0.3, "ACTIVE"),
    ],
    "IND": [
        Player("Caitlin Clark",        "G","6-0", 18.5, 5.0, 8.0, 3.5, "ACTIVE"),
        Player("Aliyah Boston",        "C","6-4", 14.0, 9.0, 2.5, 1.0, "ACTIVE"),
        Player("Kelsey Mitchell",     "G","5-10",14.5, 3.0, 2.5, 2.0, "ACTIVE"),
        Player("Grace Berger",         "G","6-0",  8.5, 2.5, 2.0, 0.8, "ACTIVE"),
        Player("Lexie Hull",           "G","5-11", 6.5, 2.5, 1.5, 0.6, "ACTIVE"),
        Player("Emma",                  "F","6-2",  6.0, 4.0, 0.8, 0.5, "Q"),
        Player("Nina",                  "F","6-3",  5.0, 3.5, 0.5, 0.3, "ACTIVE"),
    ],
    "PHX": [
        Player("Diana Taurasi",         "G","6-0", 17.0, 4.0, 4.0, 3.0, "ACTIVE"),
        Player("Brittany Griner",      "C","6-9", 15.0, 8.0, 1.5, 0.5, "ACTIVE"),
        Player("Megan",                 "F","6-3",  9.0, 4.5, 1.5, 0.8, "Q"),
        Player("Diana",                 "F","6-2",  7.5, 3.5, 1.0, 0.5, "ACTIVE"),
        Player("Sophie",               "G","5-10", 6.5, 1.5, 2.0, 0.6, "ACTIVE"),
        Player("Te'a",                  "G","5-9",  5.5, 1.5, 1.5, 0.5, "ACTIVE"),
        Player("Nneka",                "F","6-4",  8.0, 5.0, 1.0, 0.5, "ACTIVE"),
    ],
    "SEA": [
        Player("Breanna Stewart",      "F","6-4", 20.0, 8.5, 4.5, 2.5, "ACTIVE"),
        Player("Sue Bird",             "G","5-9", 14.0, 3.0, 5.5, 2.8, "ACTIVE"),
        Player("Jewel",                "C","6-5", 12.0, 8.0, 1.5, 0.5, "ACTIVE"),
        Player("Natasha Howard",      "F","6-4", 11.0, 5.5, 2.5, 1.5, "ACTIVE"),
        Player("Mercedes Russell",     "C","6-6",  7.5, 6.0, 1.0, 0.0, "Q"),
        Player("Kennedy",              "G","5-8",  5.5, 1.5, 2.0, 0.6, "ACTIVE"),
        Player("Jillian",             "F","6-2",  5.0, 3.5, 0.5, 0.3, "ACTIVE"),
    ],
    "CON": [
        Player("Alyssa Thomas",        "F","6-3", 15.5, 7.5, 6.5, 1.0, "ACTIVE"),
        Player("DeWanna Bonner",       "F","6-4", 16.0, 6.5, 3.5, 1.8, "ACTIVE"),
        Player("Brionna Jones",         "C","6-3", 12.5, 7.0, 2.0, 0.8, "ACTIVE"),
        Player("DiJonai",             "G","5-11",11.0, 3.5, 4.0, 1.5, "ACTIVE"),
        Player("Natasha",             "G","5-10", 9.0, 2.5, 3.5, 1.2, "Q"),
        Player("Julie",               "F","6-2",  6.5, 3.5, 0.8, 0.5, "ACTIVE"),
        Player("Megan",               "G","5-9",  5.5, 1.5, 1.5, 0.5, "ACTIVE"),
    ],
    "CHI": [
        Player("Kahleah Copper",       "F","6-1", 16.5, 5.5, 2.5, 1.5, "ACTIVE"),
        Player("Candace Parker",       "F","6-4", 15.0, 8.0, 5.0, 2.0, "ACTIVE"),
        Player("Rebekah",             "C","6-5", 10.0, 7.0, 1.5, 0.5, "Q"),
        Player("Dana Evans",          "G","5-6",  8.5, 2.0, 3.5, 1.2, "ACTIVE"),
        Player("Ingrid",              "F","6-3",  6.5, 4.0, 0.8, 0.5, "ACTIVE"),
        Player("Yuki",                 "G","5-9",  5.5, 1.5, 1.5, 0.5, "ACTIVE"),
        Player("Li",                   "F","6-4",  7.0, 4.5, 0.8, 0.5, "ACTIVE"),
    ],
    "ATL": [
        Player("Rhyne Howard",         "G","6-0", 15.5, 4.5, 3.5, 2.0, "ACTIVE"),
        Player("Danielle",             "F","6-3", 12.0, 6.0, 1.5, 0.8, "ACTIVE"),
        Player("Tina",                 "C","6-5", 11.5, 8.0, 1.5, 0.5, "ACTIVE"),
        Player("Shakira",             "G","5-10",10.0, 3.5, 4.5, 1.3, "ACTIVE"),
        Player("Cheyenne",            "F","6-2",  7.5, 4.0, 1.0, 0.6, "Q"),
        Player("Nia",                  "G","5-8",  6.0, 1.5, 2.0, 0.5, "ACTIVE"),
        Player("Christina",            "F","6-3",  5.5, 3.5, 0.5, 0.3, "ACTIVE"),
    ],
    "WAS": [
        Player("Elena Delle Donne",    "F","6-4", 18.0, 6.0, 3.0, 2.5, "ACTIVE"),
        Player("Ariel Atkins",         "G","5-11",14.5, 4.0, 3.0, 1.5, "ACTIVE"),
        Player("Natalie",              "C","6-5", 11.0, 7.5, 1.5, 0.5, "ACTIVE"),
        Player("Natasha Cloud",        "G","5-11", 9.5, 3.5, 5.0, 1.2, "ACTIVE"),
        Player("Shakira Austin",       "C","6-0",  8.5, 5.5, 1.5, 0.5, "Q"),
        Player("KeKe",                  "F","6-4",  7.0, 4.0, 0.8, 0.5, "ACTIVE"),
        Player("Jade",                  "G","5-8",  5.5, 1.5, 1.5, 0.5, "ACTIVE"),
    ],
}

# ─── LIVE INJURY SCRAPE ─────────────────────────────────────
def scrape_injury_report(sport="NBA"):
    url = f"https://site.api.espn.com/apis/site/v2/sports/basketball/{sport.lower()}/scoreboard"
    try:
        import urllib.request
        data = json.loads(urllib.request.urlopen(url, timeout=8).read())
        report = {}
        for event in data.get("events", []):
            for comp in event.get("competitions", [{}])[0].get("competitors", []):
                team = comp["team"]["abbreviation"]
                report[team] = []
        return report
    except Exception:
        return {}

# ─── GAME CLASS ─────────────────────────────────────────────
class Game:
    def __init__(self, away_code, home_code, sport="NBA"):
        self.away_code = away_code
        self.home_code = home_code
        self.sport = sport
        self.away = self._build_team(away_code)
        self.home = self._build_team(home_code)

    def _build_team(self, code):
        roster = NBA_ROSTERS if self.sport == "NBA" else WNBA_ROSTERS
        teams_map = NBA_TEAMS if self.sport == "NBA" else WNBA_TEAMS
        t = Team(code, teams_map.get(code, code))
        for p in roster.get(code, []):
            t.add(p)
        return t

    def injury_report(self):
        print(f"\n{'='*60}")
        print(f"  INJURY REPORT — {self.away.code} @ {self.home.code}")
        print(f"{'='*60}")
        for team in [self.away, self.home]:
            injuries = [p for p in team.players if p.status != "ACTIVE"]
            active   = [p for p in team.players if p.status == "ACTIVE"]
            print(f"\n  {team.code} — {team.name} ({len(active)} active)")
            print(f"  {'─'*50}")
            for p in team.players:
                icon = "✅" if p.status == "ACTIVE" else "⚠️" if p.status == "Q" else "❌"
                note = " ← Q (ankle)" if "Laney" in p.name else " ← Q (knee)" if "Nika" in p.name else ""
                print(f"  {icon} {p.name:25s} {p.pos:4s} | TC: {p.tc(p.pts):.1f} pts | {p.status}{note}")

    def starting_lineup(self):
        print(f"\n{'='*60}")
        print(f"  STARTING LINEUP — {self.away.code} @ {self.home.code}")
        print(f"{'='*60}")
        for team in [self.away, self.home]:
            print(f"\n  {team.code} — {team.name}")
            print(f"  {'─'*50}")
            for i, p in enumerate(team.starters(), 1):
                proj = p.proj()
                print(f"  {i}. {p.name:25s} {p.pos:4s} | TC: {proj['TC_PTS']:.1f}pts {proj['TC_REB']:.1f}reb {proj['TC_AST']:.1f}ast {proj['TC_3PM']:.1f}3pm")

    def tc_projections(self):
        print(f"\n{'='*60}")
        print(f"  TC ROSTER PROJECTIONS — {self.away.code} @ {self.home.code}")
        print(f"  TC Formula: stat × 0.85 | Q = 0.65 | OUT = 0")
        print(f"{'='*60}")
        for team in [self.away, self.home]:
            print(f"\n  {team.code} — {team.name}")
            print(f"  {'─'*72}")
            print(f"  {'Player':25s} {'POS':4s} {'TC_PTS':>7s} {'TC_REB':>7s} {'TC_AST':>7s} {'TC_3PM':>7s} {'Status':6s}")
            print(f"  {'─'*72}")
            for p in team.roster():
                proj = p.proj()
                icon = "✅" if p.status == "ACTIVE" else "⚠️" if p.status == "Q" else "❌"
                print(f"  {p.name:25s} {p.pos:4s} {proj['TC_PTS']:>7.1f} {proj['TC_REB']:>7.1f} {proj['TC_AST']:>7.1f} {proj['TC_3PM']:>7.1f} {p.status:6s} {icon}")
            b = team.bench()
            t = team.totals()
            print(f"  {'─'*72}")
            print(f"  BENCH:                  {b['TC_PTS']:>7.1f} {b['TC_REB']:>7.1f} {b['TC_AST']:>7.1f} {b['TC_3PM']:>7.1f}")
            print(f"  TEAM TOTAL:             {t['TC_PTS']:>7.1f} {t['TC_REB']:>7.1f} {t['TC_AST']:>7.1f} {t['TC_3PM']:>7.1f}")

    def summary(self):
        at = self.away.totals()
        ht = self.home.totals()
        combined = at["TC_PTS"] + ht["TC_PTS"]
        print(f"\n{'='*60}")
        print(f"  SUMMARY — {self.away.code} @ {self.home.code}")
        print(f"{'='*60}")
        print(f"  {self.away.code} TC Total:  {at['TC_PTS']:.1f} pts | {at['TC_REB']:.1f} reb | {at['TC_AST']:.1f} ast | {at['TC_3PM']:.1f} 3pm")
        print(f"  {self.home.code} TC Total:  {ht['TC_PTS']:.1f} pts | {ht['TC_REB']:.1f} reb | {ht['TC_AST']:.1f} ast | {ht['TC_3PM']:.1f} 3pm")
        print(f"  {'─'*60}")
        print(f"  COMBINED TC: {combined:.1f}")
        print(f"{'='*60}")

    def full_report(self):
        self.injury_report()
        self.starting_lineup()
        self.tc_projections()
        self.summary()

# ─── BACKTEST ────────────────────────────────────────────────
BACKTEST_SUITE = [
    # (away, home, sport, actual_combined)
    ("NYK","PHI","NBA",226),
    ("BOS","NYK","NBA",221),
    ("OKC","MIN","NBA",228),
    ("CLE","IND","NBA",215),
    ("DEN","LAC","NBA",219),
    ("MIN","SAS","NBA",222),
    ("NYL","POR","WNBA",162),
    ("LVA","IND","WNBA",169),
]

def run_backtest():
    print(f"\n{'='*60}")
    print("  TC BACKTEST RESULTS")
    print(f"{'='*60}")
    results = []
    for away, home, sport, actual in BACKTEST_SUITE:
        g = Game(away, home, sport)
        at = g.away.totals()
        ht = g.home.totals()
        tc_combined = at["TC_PTS"] + ht["TC_PTS"]
        diff = tc_combined - actual
        pct  = (diff / actual) * 100
        label = "OVER" if diff > 0 else "UNDER"
        hit  = "✅" if (diff > 0 and actual > tc_combined) or (diff < 0 and actual < tc_combined) else "❌"
        print(f"  {away}@{home} ({sport}) TC:{tc_combined:.0f} Actual:{actual:.0f} Diff:{diff:+.0f} ({pct:+.1f}%) {label} {hit}")
        results.append({"game": f"{away}@{home}", "sport": sport, "tc": tc_combined, "actual": actual, "diff": diff, "label": label})
    return results

# ─── MAIN ────────────────────────────────────────────────────
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Sports TC Engine v3.0")
    parser.add_argument("--sport",   choices=["NBA","WNBA"], default="NBA")
    parser.add_argument("--game",    help="'AWAY @ HOME'")
    parser.add_argument("--list",    action="store_true")
    parser.add_argument("--backtest",action="store_true")
    parser.add_argument("--dashboard",action="store_true")
    args = parser.parse_args()

    if args.list:
        teams = NBA_TEAMS if args.sport == "NBA" else WNBA_TEAMS
        print(f"\n{args.sport} Teams ({len(teams)}):")
        for code in sorted(teams):
            print(f"  {code}: {teams[code]}")
    elif args.backtest:
        run_backtest()
    elif args.game:
        parts = args.game.upper().split("@")
        if len(parts) == 2:
            g = Game(parts[0].strip(), parts[1].strip(), args.sport)
            g.full_report()
        else:
            print("Use format: 'TEAM @ TEAM'")
    elif args.dashboard:
        sport = input("Sport [NBA/WNBA]: ").strip() or "NBA"
        away  = input("Away code: ").strip().upper()
        home  = input("Home code: ").strip().upper()
        g = Game(away, home, sport)
        g.full_report()
    else:
        print("""
╔══════════════════════════════════════════════════════════════╗
║              SPORTS TC v3.0 — MASTER ENGINE                   ║
║         NBA + WNBA Triple Conservative System                  ║
║         TC = stat × 0.85 | Q = 0.65 | OUT = 0                 ║
╚══════════════════════════════════════════════════════════════╝

USAGE:
  python sports_tc.py --sport WNBA --game "NYL @ POR"
  python sports_tc.py --sport NBA --game "NYK @ PHI"
  python sports_tc.py --list --sport WNBA
  python sports_tc.py --backtest --sport NBA
  python sports_tc.py --dashboard
""")