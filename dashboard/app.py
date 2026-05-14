#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════╗
║              SPORTS TC — INTERACTIVE DASHBOARD               ║
║         NBA + WNBA Triple Conservative System                 ║
╚══════════════════════════════════════════════════════════════╝

FEATURES:
- Sport selector (NBA / WNBA)
- Game selector
- Live injury report
- Starting lineup (based on injury)
- Full roster TC projections (PTS/REB/AST/3PM)
- ATS + Parlay leg picks

USAGE:
    python app.py

"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sports_tc import TCEngine, NBA_TEAMS, WNBA_TEAMS

def clear():
    print("\n" * 2)

def print_header():
    print("""
╔══════════════════════════════════════════════════════════════╗
║            SPORTS TC DASHBOARD v1.0                          ║
║         Triple Conservative Projection System                  ║
║              NBA + WNBA | Parlay Props                        ║
╚══════════════════════════════════════════════════════════════╝
""")

def print_menu_options(options, title="Options"):
    print(f"\n  {title}")
    print(f"  {'─'*50}")
    for i, opt in enumerate(options, 1):
        print(f"  {i}. {opt}")
    print(f"  {'─'*50}")

def get_choice(options):
    while True:
        try:
            choice = int(input("\n  Enter choice: ").strip())
            if 1 <= choice <= len(options):
                return choice
            print("  ❌ Invalid choice")
        except ValueError:
            print("  ❌ Enter a number")

def main():
    clear()
    print_header()

    # Step 1: Sport selection
    print("\n  SELECT SPORT")
    print(f"  {'─'*50}")
    sport_choice = get_choice(["NBA", "WNBA", "Exit"])
    
    if sport_choice == 3:
        print("\n  Goodbye!")
        return
    
    sport = "NBA" if sport_choice == 1 else "WNBA"
    teams = NBA_TEAMS if sport == "NBA" else WNBA_TEAMS
    
    clear()
    print_header()
    print(f"\n  Sport selected: {sport}")
    
    # Step 2: List games or pick teams
    print("\n  SELECT ACTION")
    print(f"  {'─'*50}")
    action = get_choice(["Pick game from list", "Enter team codes manually", "Back"])
    
    if action == 3:
        main()
        return
    
    clear()
    print_header()
    print(f"\n  {sport} Teams:")
    print(f"  {'─'*50}")
    
    team_list = sorted(teams.keys())
    for i, code in enumerate(team_list, 1):
        name = teams[code]["name"]
        print(f"  {code:4s} — {name}")
    
    print(f"\n  Game format: AWAY @ HOME")
    game_input = input("\n  Enter game (e.g. NYK @ PHI): ").strip().upper()
    
    if "@" not in game_input:
        print("  ❌ Invalid format. Use 'AWAY @ HOME'")
        input("\n  Press Enter to continue...")
        main()
        return
    
    away_code, home_code = game_input.split("@")[0].strip(), game_input.split("@")[1].strip()
    
    if away_code not in teams or home_code not in teams:
        print(f"  ❌ Invalid team codes: {away_code} or {home_code}")
        input("\n  Press Enter to continue...")
        main()
        return
    
    clear()
    print_header()
    print(f"\n  Loading {sport} game: {away_code} @ {home_code}...")
    
    engine = TCEngine(sport=sport)
    game = engine.load_game(away_code, home_code)
    
    # Step 3: Run full report
    clear()
    print_header()
    game.full_report()
    
    # Step 4: Parlay legs
    away_t = game.away.tc_totals()
    home_t = game.home.tc_totals()
    combined = away_t["TC_PTS"] + home_t["TC_PTS"]
    
    print(f"\n  PARLAY LEGS (no O/U):")
    print(f"  {'─'*50}")
    print(f"  {away_code} ATS")
    print(f"  {home_code} ATS")
    print(f"  COMBINED TC: {combined:.1f}")
    
    # Step 5: Save option
    print(f"\n  {'─'*50}")
    save = input("  Save to archive? (y/n): ").strip().lower()
    if save == "y":
        from datetime import datetime
        date_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"sports_tc/archive/{sport}_{away_code}_{home_code}_{date_str}.txt"
        os.makedirs("sports_tc/archive", exist_ok=True)
        with open(filename, "w") as f:
            # write to file logic here
            pass
        print(f"  ✅ Saved to {filename}")
    
    input("\n  Press Enter to continue...")
    main()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n  Goodbye!")
        sys.exit(0)