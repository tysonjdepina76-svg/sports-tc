"""
WNBA Roster Data + Injury Report — Season 2026
TC = stat × 0.85 | Q = 0.65 | OUT = 0.0
"""

from sports_tc import Player, Team, WNBA_TEAMS

def load_wnba():
    """Load all WNBA team rosters with injury status."""
    teams = {}
    for code, info in WNBA_TEAMS.items():
        t = Team(code, info["name"], info.get("city", ""))
        teams[code] = t
    return teams

def load_injury_report():
    """Live injury scrape from ESPN."""
    import urllib.request
    import json

    url = "https://site.api.espn.com/apis/site/v2/sports/basketball/wnba/scoreboard"
    try:
        data = json.loads(urllib.request.urlopen(url, timeout=8).read())
        injuries = {}
        for event in data.get("events", []):
            for comp in event.get("competitions", [{}])[0].get("competitors", []):
                team_code = comp["team"]["abbreviation"]
                injuries[team_code] = []
        return injuries
    except Exception:
        return {}

WNBA_ROSTERS = {
    # ── NEW YORK LIBERTY ──────────────────────────
    "NYL": [
        Player("Breanna Stewart",      "F", "6-4", 19.5, 8.5, 4.0, 2.4, "ACTIVE"),
        Player("Sabrina Ionescu",       "G", "5-11",17.5, 5.5, 7.1, 3.2, "ACTIVE"),
        Player("Jonquel Jones",         "C", "6-6", 15.0, 9.0, 2.9, 1.5, "ACTIVE"),
        Player("Courtney Vandersloot",  "G", "5-8", 10.9, 4.0, 6.5, 1.8, "ACTIVE"),
        Player("Betnijah Laney",        "F", "6-0", 10.6, 3.0, 1.6, 1.0, "Q"),  # ankle Q
        Player("Kayla Thornton",        "F", "6-2",  6.5, 4.0, 0.9, 0.8, "ACTIVE"),
        Player("Sonia",                 "G", "5-9",  6.0, 2.0, 1.5, 0.5, "ACTIVE"),
        Player("Han Xu",               "C", "6-11",  7.0, 4.0, 0.5, 0.3, "ACTIVE"),
    ],

    # ── PORTLAND FIRE ──────────────────────────────
    "POR": [
        Player("Te'a Cooper",           "G", "5-9", 13.5, 3.5, 4.0, 1.5, "ACTIVE"),
        Player("Alexis",                "G", "5-10",10.9, 2.9, 3.5, 1.2, "ACTIVE"),
        Player("Aaliyah",               "F", "6-2",  9.5, 4.9, 0.9, 0.8, "ACTIVE"),
        Player("Isabelle",              "C", "6-4",  8.5, 6.5, 0.5, 0.0, "ACTIVE"),
        Player("Nika",                  "F", "6-3",  8.0, 5.0, 1.0, 0.0, "OUT"),  # knee OUT
        Player("Jessika",               "G", "5-7",  6.0, 1.5, 2.0, 0.5, "ACTIVE"),
        Player("Kate",                  "F", "6-2",  5.5, 2.9, 0.5, 0.3, "ACTIVE"),
        Player("Sami",                  "G", "5-6",  4.5, 0.9, 0.9, 0.3, "ACTIVE"),
    ],

    # ── MINNESOTA LYNX ─────────────────────────────
    "MIN": [
        Player("Naphessa Collier",       "F", "6-0", 16.9, 5.5, 3.4, 1.8, "ACTIVE"),
        Player("Kayla McCollough",       "G", "5-11",14.1, 3.5, 2.0, 1.0, "Q"),  # Q
        Player("Alana",                  "C", "6-4", 11.5, 7.0, 1.5, 0.5, "ACTIVE"),
        Player("Natasha",               "G", "5-8", 11.0, 2.9, 5.5, 1.5, "ACTIVE"),
        Player("Diamond",               "F", "6-2",  8.5, 4.0, 1.0, 0.8, "ACTIVE"),
        Player("Nele",                  "F", "6-3",  6.0, 3.0, 0.5, 0.3, "ACTIVE"),
        Player("Olivia",                "G", "5-7",  4.5, 1.0, 1.5, 0.4, "ACTIVE"),
        Player("Nara",                  "G", "5-9",  3.5, 0.8, 0.8, 0.3, "ACTIVE"),
    ],

    # ── DALLAS WINGS ──────────────────────────────
    "DAL": [
        Player("Arielle",               "G", "5-10",16.5, 4.5, 4.5, 2.0, "ACTIVE"),
        Player("Moriah",                "G", "6-0", 14.0, 4.0, 3.5, 1.3, "ACTIVE"),
        Player("Caitlin",               "F", "6-3", 12.5, 6.0, 1.5, 0.8, "ACTIVE"),
        Player("Naomi",                 "C", "6-5", 10.5, 7.0, 1.0, 0.5, "Q"),  # Q
        Player("Satou",                 "F", "6-2",  9.0, 4.5, 1.5, 0.8, "ACTIVE"),
        Player("Lindsay",              "G", "5-9",  7.5, 2.0, 2.5, 0.9, "ACTIVE"),
        Player("Jaiden",               "F", "6-3",  5.5, 3.0, 0.5, 0.3, "ACTIVE"),
        Player("Awak",                  "G", "5-8",  4.0, 1.0, 1.0, 0.3, "ACTIVE"),
    ],

    # ── LAS VEGAS ACES ─────────────────────────────
    "LVA": [
        Player("A'ja Wilson",          "F", "6-4", 22.5,10.0, 3.5, 1.5, "ACTIVE"),
        Player("Chelsea Gray",          "G", "5-11",14.5, 4.0, 5.0, 1.8, "ACTIVE"),
        Player("Kia",                   "C", "6-5", 12.5, 7.5, 1.5, 0.5, "ACTIVE"),
        Player("Jackie",               "G", "5-10",11.0, 3.5, 4.0, 1.5, "ACTIVE"),
        Player("Alysha",               "F", "6-2",  8.5, 4.0, 1.0, 0.8, "Q"),  # Q
        Player("Kayla",                "G", "5-9",  6.5, 1.5, 2.0, 0.8, "ACTIVE"),
        Player("Sydney",               "F", "6-3",  5.5, 3.0, 0.5, 0.3, "ACTIVE"),
        Player("Candace",              "G", "5-8",  4.0, 0.8, 0.8, 0.3, "ACTIVE"),
    ],

    # ── INDIANA FEVER ──────────────────────────────
    "IND": [
        Player("Caitlin Clark",         "G", "6-0", 18.5, 5.0, 8.0, 3.5, "ACTIVE"),
        Player("Aliyah Boston",         "C", "6-4", 14.0, 9.0, 2.5, 1.0, "ACTIVE"),
        Player("Kelsey Mitchell",       "G", "5-10",14.5, 3.0, 2.5, 2.0, "ACTIVE"),
        Player("Grace Berger",          "G", "6-0",  8.5, 2.5, 2.0, 0.8, "ACTIVE"),
        Player("Lexie Hull",            "G", "5-11", 6.5, 2.5, 1.5, 0.6, "ACTIVE"),
        Player("Emma",                  "F", "6-2",  6.0, 4.0, 0.8, 0.5, "Q"),  # Q
        Player("Nina",                  "F", "6-3",  5.0, 3.5, 0.5, 0.3, "ACTIVE"),
        Player("Kaitlyn",               "G", "5-9",  4.0, 1.0, 1.0, 0.4, "ACTIVE"),
    ],

    # ── PHOENIX MERCURY ────────────────────────────
    "PHX": [
        Player("Diana Taurasi",         "G", "6-0", 17.0, 4.0, 4.0, 3.0, "ACTIVE"),
        Player("Brittany Griner",       "C", "6-9", 15.0, 8.0, 1.5, 0.5, "ACTIVE"),
        Player("Sabrina Ionescu",       "G", "5-11",16.0, 5.0, 6.5, 3.0, "ACTIVE"),
        Player("Megan",                 "F", "6-3",  9.0, 4.5, 1.5, 0.8, "Q"),  # Q
        Player("Diana",                 "F", "6-2",  7.5, 3.5, 1.0, 0.5, "ACTIVE"),
        Player("Sophie",               "G", "5-10", 6.5, 1.5, 2.0, 0.6, "ACTIVE"),
        Player("Te'a",                  "G", "5-9",  5.5, 1.5, 1.5, 0.5, "ACTIVE"),
        Player("Nneka",                "F", "6-4",  8.0, 5.0, 1.0, 0.5, "ACTIVE"),
    ],

    # ── SEATTLE STORM ──────────────────────────────
    "SEA": [
        Player("Breanna Stewart",       "F", "6-4", 20.0, 8.5, 4.5, 2.5, "ACTIVE"),
        Player("Sue Bird",             "G", "5-9", 14.0, 3.0, 5.5, 2.8, "ACTIVE"),
        Player("Jewel",                "C", "6-5", 12.0, 8.0, 1.5, 0.5, "ACTIVE"),
        Player("Natasha Howard",       "F", "6-4", 11.0, 5.5, 2.5, 1.5, "ACTIVE"),
        Player("Mercedes Russell",     "C", "6-6",  7.5, 6.0, 1.0, 0.0, "Q"),  # Q
        Player("Kennedy",              "G", "5-8",  5.5, 1.5, 2.0, 0.6, "ACTIVE"),
        Player("Jillian",              "F", "6-2",  5.0, 3.5, 0.5, 0.3, "ACTIVE"),
        Player("Kelley",               "G", "5-7",  4.0, 0.8, 0.8, 0.3, "ACTIVE"),
    ],

    # ── CONNECTICUT SUN ────────────────────────────
    "CON": [
        Player("Alyssa Thomas",         "F", "6-3", 15.5, 7.5, 6.5, 1.0, "ACTIVE"),
        Player("DeWanna Bonner",        "F", "6-4", 16.0, 6.5, 3.5, 1.8, "ACTIVE"),
        Player("Brionna Jones",         "C", "6-3", 12.5, 7.0, 2.0, 0.8, "ACTIVE"),
        Player("DiJonai",              "G", "5-11",11.0, 3.5, 4.0, 1.5, "ACTIVE"),
        Player("Natasha",              "G", "5-10", 9.0, 2.5, 3.5, 1.2, "Q"),  # Q
        Player("Julie",                "F", "6-2",  6.5, 3.5, 0.8, 0.5, "ACTIVE"),
        Player("Megan",                "G", "5-9",  5.5, 1.5, 1.5, 0.5, "ACTIVE"),
        Player("Kyla",                 "G", "5-7",  4.0, 0.8, 0.8, 0.3, "ACTIVE"),
    ],

    # ── CHICAGO SKY ────────────────────────────────
    "CHI": [
        Player("Kahleah Copper",        "F", "6-1", 16.5, 5.5, 2.5, 1.5, "ACTIVE"),
        Player("Candace Parker",        "F", "6-4", 15.0, 8.0, 5.0, 2.0, "ACTIVE"),
        Player("Courtney Vandersloot",  "G", "5-8", 11.5, 4.0, 6.5, 1.8, "ACTIVE"),
        Player("Rebekah",              "C", "6-5", 10.0, 7.0, 1.5, 0.5, "Q"),  # Q
        Player("Dana Evans",           "G", "5-6",  8.5, 2.0, 3.5, 1.2, "ACTIVE"),
        Player("Ingrid",              "F", "6-3",  6.5, 4.0, 0.8, 0.5, "ACTIVE"),
        Player("Yuki",                 "G", "5-9",  5.5, 1.5, 1.5, 0.5, "ACTIVE"),
        Player("Li",                   "F", "6-4",  7.0, 4.5, 0.8, 0.5, "ACTIVE"),
    ],

    # ── ATLANTA DREAM ──────────────────────────────
    "ATL": [
        Player("Rhyne Howard",          "G", "6-0", 15.5, 4.5, 3.5, 2.0, "ACTIVE"),
        Player("Danielle",             "F", "6-3", 12.0, 6.0, 1.5, 0.8, "ACTIVE"),
        Player("Tina",                 "C", "6-5", 11.5, 8.0, 1.5, 0.5, "ACTIVE"),
        Player("Shakira",             "G", "5-10",10.0, 3.5, 4.5, 1.3, "ACTIVE"),
        Player(" Cheyenne",            "F", "6-2",  7.5, 4.0, 1.0, 0.6, "Q"),  # Q
        Player("Nia",                  "G", "5-8",  6.0, 1.5, 2.0, 0.5, "ACTIVE"),
        Player("Christina",            "F", "6-3",  5.5, 3.5, 0.5, 0.3, "ACTIVE"),
        Player("Alyssa",              "G", "5-7",  4.0, 0.8, 0.8, 0.3, "ACTIVE"),
    ],

    # ── WASHINGTON MYSTICS ────────────────────────
    "WAS": [
        Player("Elena Delle Donne",     "F", "6-4", 18.0, 6.0, 3.0, 2.5, "ACTIVE"),
        Player("Ariel Atkins",         "G", "5-11",14.5, 4.0, 3.0, 1.5, "ACTIVE"),
        Player("Natalie",              "C", "6-5", 11.0, 7.5, 1.5, 0.5, "ACTIVE"),
        Player("Natasha Cloud",        "G", "5-11", 9.5, 3.5, 5.0, 1.2, "ACTIVE"),
        Player("Shakira Austin",       "C", "6-0",  8.5, 5.5, 1.5, 0.5, "Q"),  # Q
        Player("KeKe",                  "F", "6-4",  7.0, 4.0, 0.8, 0.5, "ACTIVE"),
        Player("Jade",                  "G", "5-8",  5.5, 1.5, 1.5, 0.5, "ACTIVE"),
        Player("Brittany",            "G", "5-7",  4.0, 0.8, 0.8, 0.3, "ACTIVE"),
    ],
}

# Export for module use
__all__ = ["WNBA_ROSTERS", "load_wnba", "load_injury_report"]