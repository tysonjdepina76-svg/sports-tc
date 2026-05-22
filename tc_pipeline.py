#!/usr/bin/env python3
"""
Sports TC Pipeline v6.0
=======================
Unified NBA + WNBA TC workflow. Single entry point for:
  - Roster loading (from JSON files)
  - TC player-prop floors (PTS×0.85, REB×0.80, AST×0.75, 3PM×0.70)
  - Injury reports
  - Starting lineups + bench splits
  - Full player projections table
  - Game/team raw totals (kept separate from TC)
  - Prop candidate watchlist
  - JSON output + optional report markdown

TC Rules
--------
1. TC applies ONLY to player prop categories: PTS, REB, AST, 3PM.
2. Team totals and game totals are RAW projection totals only.
   No TC line, no TC edge, no TC recommendation for team/game totals.
3. OUT players contribute 0. Questionable players: TC × 0.55.
4. Roster output always separates starters, bench, and injury notes.

Roster Data
-----------
  NBA  → /home/workspace/wnba_rosters/NBA_BACKTEST_ROSTERS.json
  WNBA → /home/workspace/wnba_rosters/WNBA_BACKTEST_ROSTERS.json

Usage
------
  python3 tc_pipeline.py --sport NBA --game "BOS @ NYK"
  python3 tc_pipeline.py --sport WNBA --game "DAL @ ATL" --total 172.5
  python3 tc_pipeline.py --sport NBA --game "BOS @ NYK" --save
  python3 tc_pipeline.py --sport WNBA --diagnostics
  python3 tc_pipeline.py --sport NBA --list-teams
"""
from __future__ import annotations

import argparse
import csv
import json
import os
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

# ── Paths ─────────────────────────────────────────────────────────────────────
ROOT            = Path(__file__).resolve().parent
WORKSPACE       = Path("/home/workspace")
NBA_JSON        = WORKSPACE / "wnba_rosters" / "NBA_BACKTEST_ROSTERS.json"
WNBA_JSON       = WORKSPACE / "wnba_rosters" / "WNBA_BACKTEST_ROSTERS.json"
REPORT_DIR      = ROOT / "reports"
DATA_DIR        = ROOT / "data"
REPORT_DIR.mkdir(exist_ok=True)
DATA_DIR.mkdir(exist_ok=True)

# ── TC Constants ─────────────────────────────────────────────────────────────
TC_FACTORS   = {"pts": 0.85, "reb": 0.80, "ast": 0.75, "tpm": 0.70}
Q_FACTOR     = 0.55       # Questionable: TC result × 0.55
OUT_FACTOR   = 0.0         # OUT: 0 contribution
LINE_FACTOR  = 0.88        # TC_line = TC_pts × 0.88 (player prop line)
DEFAULT_PROP_EDGE = {"pts": 3.0, "reb": 2.0, "ast": 1.5, "tpm": 0.5}

# ── Team Aliases ─────────────────────────────────────────────────────────────
TEAM_ALIASES = {
    "NY":  "NYK",  "NYK": "NYK",
    "LV":  "LVA",  "LVA": "LVA",
    "LA":  "LAS",  "LAS": "LAS",
    "GS":  "GSW",  "GSW": "GSW",
    "SA":  "SAS",  "SAS": "SAS",
    "BKN": "BKN",  "BK":  "BKN",
    "NO":  "NOP",  "NOP": "NOP",
    "UTH": "UTA",  "UTA": "UTA",
    "SA":  "SAS",
}


# ─────────────────────────────────────────────────────────────────────────────
# ROSTER LOADERS
# ─────────────────────────────────────────────────────────────────────────────

def norm_code(code: str) -> str:
    """Normalize a team code, expanding aliases."""
    clean = code.strip().upper()
    return TEAM_ALIASES.get(clean, clean)


def safe_float(value: Any) -> float:
    try:
        return float(value or 0)
    except Exception:
        return 0.0


def player_from_dict(item: Dict[str, Any], role: str) -> "PlayerProjection":
    """Convert a dict player entry to a PlayerProjection."""
    return PlayerProjection(
        name=str(item.get("name", "Unknown")),
        pos=str(item.get("pos", "")),
        ht=str(item.get("ht", "")),
        ppg=safe_float(item.get("ppg", item.get("pts", 0))),
        rpg=safe_float(item.get("rpg", item.get("reb", 0))),
        apg=safe_float(item.get("apg", item.get("ast", 0))),
        tpm=safe_float(item.get("tpm", item.get("3pm", 0))),
        status=str(item.get("status", "ACTIVE")).upper(),
        role=role,
    )


def _load_json_roster(json_path: Path, sport_label: str) -> Dict[str, Dict]:
    """Load roster JSON and return the teams dict."""
    if not json_path.exists():
        raise FileNotFoundError(
            f"{sport_label} roster JSON not found at {json_path}. "
            f"Run the NBA roster build script first."
        )
    data = json.loads(json_path.read_text())
    teams = data.get("teams", {})
    if not teams:
        raise ValueError(f"{json_path} contains no 'teams' key.")
    return teams


def load_team_from_json(
    code: str,
    sport: str,
    json_path: Path,
) -> "TeamProjection":
    """
    Load a single team from a roster JSON file.
    Determines starters vs bench from the JSON structure.
    """
    code = norm_code(code)
    teams = _load_json_roster(json_path, sport.upper())

    if code not in teams:
        available = ", ".join(sorted(teams))
        raise KeyError(
            f"{sport} team '{code}' not found in {json_path.name}. "
            f"Available: {available}"
        )

    team = teams[code]
    starters = [
        player_from_dict(p, "STARTER")
        for p in team.get("starters", [])
    ]
    bench = [
        player_from_dict(p, "BENCH")
        for p in team.get("bench", [])
    ]

    # injury_notes may be a list of strings or a single string
    raw_notes = team.get("injury_notes", [])
    if isinstance(raw_notes, str):
        injury_notes = [raw_notes] if raw_notes else []
    else:
        injury_notes = list(raw_notes)

    return TeamProjection(
        code=code,
        name=team.get("team_name", code),
        starters=starters,
        bench=bench,
        injury_notes=injury_notes,
    )


def load_nba_team(code: str) -> "TeamProjection":
    return load_team_from_json(code, "NBA", NBA_JSON)


def load_wnba_team(code: str) -> "TeamProjection":
    return load_team_from_json(code, "WNBA", WNBA_JSON)


def load_team(sport: str, code: str) -> "TeamProjection":
    sport = sport.upper()
    if sport == "WNBA":
        return load_wnba_team(code)
    return load_nba_team(code)


def list_available_teams(sport: str) -> List[Tuple[str, str]]:
    """Return sorted list of (code, team_name) for a sport."""
    sport = sport.upper()
    json_path = WNBA_JSON if sport == "WNBA" else NBA_JSON
    teams = _load_json_roster(json_path, sport)
    return sorted(
        (code, info.get("team_name", code)) for code, info in teams.items()
    )


# ─────────────────────────────────────────────────────────────────────────────
# PLAYER / TEAM / GAME CLASSES
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class PlayerProjection:
    name: str
    pos: str
    ht: str
    ppg: float
    rpg: float
    apg: float
    tpm: float
    status: str = "ACTIVE"
    role: str = "BENCH"

    # ── Status ───────────────────────────────────────────────────────────────
    def status_factor(self) -> float:
        s = self.status.upper()
        if s == "OUT":
            return OUT_FACTOR
        if s in {"Q", "QUESTIONABLE", "DOUBTFUL", "DAY-TO-DAY"}:
            return Q_FACTOR
        return 1.0

    def status_icon(self) -> str:
        return "✅" if self.status == "ACTIVE" else "⚠️" if self.status in ("Q", "QUESTIONABLE") else "❌"

    def injury_tag(self) -> str:
        if self.status == "OUT":
            return " ← OUT"
        if self.status in ("Q", "QUESTIONABLE", "DOUBTFUL", "DAY-TO-DAY"):
            return " ← Q"
        return ""

    # ── Raw stats ──────────────────────────────────────────────────────────────
    def raw(self) -> Dict[str, float]:
        return {
            "pts": round(self.ppg, 1),
            "reb": round(self.rpg, 1),
            "ast": round(self.apg, 1),
            "tpm": round(self.tpm, 1),
        }

    # ── TC prop floors ─────────────────────────────────────────────────────────
    def tc(self) -> Dict[str, float]:
        f = self.status_factor()
        return {
            "pts": round(self.ppg * TC_FACTORS["pts"] * f, 1),
            "reb": round(self.rpg * TC_FACTORS["reb"] * f, 1),
            "ast": round(self.apg * TC_FACTORS["ast"] * f, 1),
            "tpm": round(self.tpm * TC_FACTORS["tpm"] * f, 1),
        }

    # ── Prop targets (whole numbers — the line you'd bet over) ───────────────────
    def prop_targets(self) -> Dict[str, int]:
        tc = self.tc()
        return {
            "pts": max(0, int(tc["pts"])),
            "reb": max(0, int(tc["reb"])),
            "ast": max(0, int(tc["ast"])),
            "tpm": max(0, int(tc["tpm"])),
        }

    # ── Production score ──────────────────────────────────────────────────────
    def production_score(self) -> float:
        return self.ppg + self.rpg + self.apg + (self.tpm * 2)


@dataclass
class TeamProjection:
    code: str
    name: str
    starters: List[PlayerProjection] = field(default_factory=list)
    bench: List[PlayerProjection] = field(default_factory=list)
    injury_notes: List[str] = field(default_factory=list)

    # ── Combined player list ──────────────────────────────────────────────────
    @property
    def players(self) -> List[PlayerProjection]:
        return self.starters + self.bench

    @property
    def active_players(self) -> List[PlayerProjection]:
        return [p for p in self.players if p.status != "OUT"]

    # ── Raw totals (no TC applied) ─────────────────────────────────────────────
    def raw_totals(self) -> Dict[str, float]:
        active = self.active_players
        return {
            "pts": round(sum(p.ppg for p in active), 1),
            "reb": round(sum(p.rpg for p in active), 1),
            "ast": round(sum(p.apg for p in active), 1),
            "tpm": round(sum(p.tpm for p in active), 1),
        }

    # ── TC totals for player props only ───────────────────────────────────────
    def tc_prop_totals(self) -> Dict[str, float]:
        totals = {"pts": 0.0, "reb": 0.0, "ast": 0.0, "tpm": 0.0}
        for player in self.players:
            tc = player.tc()
            for key in totals:
                totals[key] += tc[key]
        return {k: round(v, 1) for k, v in totals.items()}

    # ── Injury summary ────────────────────────────────────────────────────────
    def injury_summary(self) -> Dict[str, List[PlayerProjection]]:
        return {
            "out": [p for p in self.players if p.status == "OUT"],
            "q":   [p for p in self.players if p.status in ("Q", "QUESTIONABLE", "DOUBTFUL", "DAY-TO-DAY")],
            "active": [p for p in self.players if p.status == "ACTIVE"],
        }


@dataclass
class GameProjection:
    away: TeamProjection
    home: TeamProjection
    sport: str
    market_total: Optional[float] = None
    market_spread: Optional[float] = None
    generated_at: str = field(
        default_factory=lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    )

    # ── Raw game totals ────────────────────────────────────────────────────────
    def raw_game_totals(self) -> Dict[str, float]:
        away = self.away.raw_totals()
        home = self.home.raw_totals()
        return {key: round(away[key] + home[key], 1) for key in away}

    # ── Prop candidate watchlist ───────────────────────────────────────────────
    def prop_candidates(self) -> List[Dict[str, Any]]:
        candidates: List[Dict[str, Any]] = []
        for team in (self.away, self.home):
            for player in team.players:
                if player.status == "OUT":
                    continue
                tc = player.tc()
                raw = player.raw()
                for stat in ("pts", "reb", "ast", "tpm"):
                    gap = round(raw[stat] - tc[stat], 1)
                    if gap >= DEFAULT_PROP_EDGE[stat] and tc[stat] > 0:
                        candidates.append({
                            "team": team.code,
                            "player": player.name,
                            "role": player.role,
                            "stat": stat.upper().replace("TPM", "3PM"),
                            "raw_projection": raw[stat],
                            "tc_floor": tc[stat],
                            "target_whole_number": player.prop_targets()[stat],
                            "gap": gap,
                            "status": player.status,
                        })
        return sorted(candidates, key=lambda x: (x["gap"], x["raw_projection"]), reverse=True)

    # ── Serializable dict ─────────────────────────────────────────────────────
    def to_dict(self) -> Dict[str, Any]:
        return {
            "generated_at": self.generated_at,
            "sport": self.sport,
            "market_total": self.market_total,
            "market_spread": self.market_spread,
            "rule": (
                "TC applies only to player props (PTS×0.85, REB×0.80, AST×0.75, 3PM×0.70). "
                "Team/game totals are raw projections only."
            ),
            "away": serialize_team(self.away),
            "home": serialize_team(self.home),
            "raw_game_totals": self.raw_game_totals(),
            "prop_candidates": self.prop_candidates(),
        }


# ─────────────────────────────────────────────────────────────────────────────
# SERIALIZATION HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def serialize_player(player: PlayerProjection) -> Dict[str, Any]:
    raw = player.raw()
    tc = player.tc()
    return {
        "name": player.name,
        "role": player.role,
        "pos": player.pos,
        "ht": player.ht,
        "status": player.status,
        "raw": raw,
        "tc_prop_floor": tc,
        "prop_targets": player.prop_targets(),
    }


def serialize_team(team: TeamProjection) -> Dict[str, Any]:
    return {
        "code": team.code,
        "name": team.name,
        "injury_notes": team.injury_notes,
        "raw_totals": team.raw_totals(),
        "tc_prop_totals": team.tc_prop_totals(),
        "starters": [serialize_player(p) for p in team.starters],
        "bench": [serialize_player(p) for p in team.bench],
    }


# ─────────────────────────────────────────────────────────────────────────────
# FORMATTING
# ─────────────────────────────────────────────────────────────────────────────

def format_player_table(players: Iterable[PlayerProjection]) -> List[str]:
    """Markdown table of player raw + TC stats."""
    rows = [
        "| Role | Player | POS | HT | Status | "
        "Raw PTS | Raw REB | Raw AST | Raw 3PM | "
        "TC PTS | TC REB | TC AST | TC 3PM | "
        "Target PTS | Target REB | Target AST | Target 3PM |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for p in players:
        raw = p.raw()
        tc = p.tc()
        tgt = p.prop_targets()
        rows.append(
            f"| {p.role} | {p.name} | {p.pos} | {p.ht} | {p.status} | "
            f"{raw['pts']:.1f} | {raw['reb']:.1f} | {raw['ast']:.1f} | {raw['tpm']:.1f} | "
            f"{tc['pts']:.1f} | {tc['reb']:.1f} | {tc['ast']:.1f} | {tc['tpm']:.1f} | "
            f"{tgt['pts']}+ | {tgt['reb']}+ | {tgt['ast']}+ | {tgt['tpm']}+ |"
        )
    return rows


def format_team_section(team: TeamProjection) -> List[str]:
    """All sections for one team as a list of markdown lines."""
    lines = [
        f"## {team.code} — {team.name}",
        "",
        "### Injury Notes",
    ]
    if team.injury_notes:
        lines.extend(f"- {n}" for n in team.injury_notes)
    else:
        lines.append(
            "- No injury notes available. "
            "Confirm pregame status before bet placement."
        )

    inj = team.injury_summary()
    if inj["out"]:
        lines.append(
            f"**Out:** {', '.join(p.name for p in inj['out'])}"
        )
    if inj["q"]:
        lines.append(
            f"**Questionable:** {', '.join(p.name for p in inj['q'])}"
        )

    lines.extend([
        "",
        "### Raw Team Totals — No TC Applied",
        "",
        "| PTS | REB | AST | 3PM |",
        "|---:|---:|---:|---:|",
        f"| {team.raw_totals()['pts']:.1f} | {team.raw_totals()['reb']:.1f} | "
        f"{team.raw_totals()['ast']:.1f} | {team.raw_totals()['tpm']:.1f} |",
        "",
        "### TC Prop Floors — Starters + Bench",
        "",
    ])
    lines.extend(format_player_table(team.players))
    lines.append("")
    return lines


def render_report(game: GameProjection) -> str:
    """Render a full markdown report for one game."""
    raw_game = game.raw_game_totals()
    lines = [
        f"# {game.sport} TC Report — {game.away.code} @ {game.home.code}",
        "",
        f"**Generated:** {game.generated_at}",
        "",
        "## Rules",
        "- TC applies **only to player prop categories**: "
        "PTS × 0.85, REB × 0.80, AST × 0.75, 3PM × 0.70.",
        "- Questionable players: TC result × 0.55. OUT players: 0.",
        "- **Team totals and game totals are raw projections only** — "
        "no TC applied to team or game totals.",
        "",
        "## Market / Raw Totals",
        "",
        "| Item | Value |",
        "|---|---:|",
        f"| Market Total | {game.market_total if game.market_total is not None else 'Not provided'} |",
        f"| Market Spread | {game.market_spread if game.market_spread is not None else 'Not provided'} |",
        f"| {game.away.code} Raw Team Points | {game.away.raw_totals()['pts']:.1f} |",
        f"| {game.home.code} Raw Team Points | {game.home.raw_totals()['pts']:.1f} |",
        f"| Raw Game Points Total | {raw_game['pts']:.1f} |",
        f"| Raw Game Rebounds Total | {raw_game['reb']:.1f} |",
        f"| Raw Game Assists Total | {raw_game['ast']:.1f} |",
        f"| Raw Game 3PM Total | {raw_game['tpm']:.1f} |",
        "",
    ]
    lines.extend(format_team_section(game.away))
    lines.extend(format_team_section(game.home))

    # Prop candidates
    candidates = game.prop_candidates()[:20]
    lines.extend([
        "## Prop Candidate Watchlist",
        "",
        "*Players whose TC floor is notably below their raw projection — "
        "watch for line value. Not picks until book lines are checked.*",
        "",
        "| Team | Player | Role | Stat | Raw | TC Floor | Whole # | Gap | Status |",
        "|---|---|---|---:|---:|---:|---:|---:|",
    ])
    for c in candidates:
        lines.append(
            f"| {c['team']} | {c['player']} | {c['role']} | {c['stat']} | "
            f"{c['raw_projection']:.1f} | {c['tc_floor']:.1f} | "
            f"{c['target_whole_number']}+ | {c['gap']:.1f} | {c['status']} |"
        )
    lines.append("")
    return "\n".join(lines)


# ─────────────────────────────────────────────────────────────────────────────
# CONSOLE PRINT OUTPUT (human-readable)
# ─────────────────────────────────────────────────────────────────────────────

def print_injury_report(game: GameProjection) -> None:
    raw_game = game.raw_game_totals()
    sep = "=" * 70
    print(f"\n{sep}")
    print(f"  ⚕  INJURY REPORT — {game.away.code} @ {game.home.code}")
    print(f"  TC = stat×0.85 | Q = ×0.55 | OUT = 0 | Raw game pts: {raw_game['pts']:.1f}")
    print(sep)

    for team in (game.away, game.home):
        inj = team.injury_summary()
        active_n = len(inj["active"])
        q_n = len(inj["q"])
        out_n = len(inj["out"])
        print(f"\n  {team.code} — {team.name}  ({active_n} ✅ | {q_n} ⚠️ | {out_n} ❌)")
        print(f"  {'─' * 60}")

        # Injury notes from JSON
        if team.injury_notes:
            for note in team.injury_notes:
                print(f"  📋 {note}")

        # OUT players
        if inj["out"]:
            print(f"  ❌ OUT: {', '.join(p.name for p in inj['out'])}")
        # Q players
        if inj["q"]:
            print(f"  ⚠️  Q:   {', '.join(p.name for p in inj['q'])}")

        # Active roster table
        print(f"\n  {'Player':<26s} {'POS':4s} {'TC_PTS':>7s} {'TC_REB':>7s} "
              f"{'TC_AST':>7s} {'TC_3PM':>7s} {'Status':8s}")
        print(f"  {'─' * 70}")
        for p in team.players:
            tc = p.tc()
            icon = p.status_icon()
            tag = p.injury_tag()
            status_str = f"{p.status}{tag}"
            print(
                f"  {p.name:<26s} {p.pos:4s} "
                f"{tc['pts']:>7.1f} {tc['reb']:>7.1f} "
                f"{tc['ast']:>7.1f} {tc['tpm']:>7.1f} "
                f"{status_str:8s} {icon}"
            )
        print(f"  {'─' * 70}")
        rt = team.raw_totals()
        tt = team.tc_prop_totals()
        print(
            f"  {'RAW TOTALS':26s} {rt['pts']:>7.1f} {rt['reb']:>7.1f} "
            f"{rt['ast']:>7.1f} {rt['tpm']:>7.1f}"
        )
        print(
            f"  {'TC PROPS':26s} {tt['pts']:>7.1f} {tt['reb']:>7.1f} "
            f"{tt['ast']:>7.1f} {tt['tpm']:>7.1f}"
        )
    print(f"\n{sep}\n")


def print_starting_lineup(game: GameProjection) -> None:
    sep = "=" * 70
    print(f"\n{sep}")
    print(f"  📋 STARTING LINEUP — {game.away.code} @ {game.home.code}")
    print(sep)

    for team in (game.away, game.home):
        print(f"\n  {team.code} — {team.name}")
        print(f"  {'─' * 70}")
        print(
            f"  {'#':>2} {'Player':<26s} {'POS':4s} {'TC_PTS':>7s} "
            f"{'TC_REB':>7s} {'TC_AST':>7s} {'TC_3PM':>7s} {'Status':6s}"
        )
        print(f"  {'─' * 70}")
        for i, p in enumerate(team.starters, 1):
            tc = p.tc()
            icon = p.status_icon()
            tag = p.injury_tag()
            print(
                f"  {i:2d}. {p.name:<26s} {p.pos:4s} "
                f"{tc['pts']:>7.1f} {tc['reb']:>7.1f} "
                f"{tc['ast']:>7.1f} {tc['tpm']:>7.1f} "
                f"{p.status}{tag:6s} {icon}"
            )

        # Bench
        if team.bench:
            print(f"  {'─' * 70}")
            for p in team.bench:
                tc = p.tc()
                icon = p.status_icon()
                tag = p.injury_tag()
                print(
                    f"  {'B':>2} {p.name:<26s} {p.pos:4s} "
                    f"{tc['pts']:>7.1f} {tc['reb']:>7.1f} "
                    f"{tc['ast']:>7.1f} {tc['tpm']:>7.1f} "
                    f"{p.status}{tag:6s} {icon}"
                )

        bt = team.tc_prop_totals()
        print(f"  {'─' * 70}")
        print(
            f"  {'TC PROPS TEAM TOTAL':26s} {bt['pts']:>7.1f} {bt['reb']:>7.1f} "
            f"{bt['ast']:>7.1f} {bt['tpm']:>7.1f}"
        )
    print(f"\n{sep}\n")


def print_tc_projections(game: GameProjection) -> None:
    sep = "=" * 72
    print(f"\n{sep}")
    print(
        f"  📊 TC PROJECTIONS — {game.away.code} @ {game.home.code}\n"
        f"  Formula: PTS×0.85 | REB×0.80 | AST×0.75 | 3PM×0.70 | Q×0.55 | OUT=0"
    )
    print(sep)

    for team in (game.away, game.home):
        print(f"\n  {team.code} — {team.name}")
        print(f"  {'─' * 90}")
        print(
            f"  {'Player':<26s} {'POS':4s} {'TC_PTS':>7s} {'TC_REB':>7s} "
            f"{'TC_AST':>7s} {'TC_3PM':>7s} {'Status':8s}"
        )
        print(f"  {'─' * 90}")

        # Starters
        for p in team.starters:
            tc = p.tc()
            icon = p.status_icon()
            tag = p.injury_tag()
            print(
                f"  {p.name:<26s} {p.pos:4s} "
                f"{tc['pts']:>7.1f} {tc['reb']:>7.1f} "
                f"{tc['ast']:>7.1f} {tc['tpm']:>7.1f} "
                f"{p.status}{tag:8s} {icon}"
            )

        # Bench
        print(f"  {'─' * 90}")
        for p in team.bench:
            tc = p.tc()
            icon = p.status_icon()
            tag = p.injury_tag()
            print(
                f"  {p.name:<26s} {p.pos:4s} "
                f"{tc['pts']:>7.1f} {tc['reb']:>7.1f} "
                f"{tc['ast']:>7.1f} {tc['tpm']:>7.1f} "
                f"{p.status}{tag:8s} {icon}"
            )

        bt = team.tc_prop_totals()
        rt = team.raw_totals()
        print(f"  {'─' * 90}")
        print(
            f"  {'RAW TOTALS':26s}          {rt['pts']:>7.1f} {rt['reb']:>7.1f} "
            f"{rt['ast']:>7.1f} {rt['tpm']:>7.1f}"
        )
        print(
            f"  {'TC PROPS TEAM TOTAL':26s} {bt['pts']:>7.1f} {bt['reb']:>7.1f} "
            f"{bt['ast']:>7.1f} {bt['tpm']:>7.1f}"
        )
    print(f"\n{sep}\n")


def print_console_report(game: GameProjection) -> None:
    """Print all sections to console."""
    print_injury_report(game)
    print_starting_lineup(game)
    print_tc_projections(game)


# ─────────────────────────────────────────────────────────────────────────────
# FILE I/O
# ─────────────────────────────────────────────────────────────────────────────

def save_game_outputs(game: GameProjection, stem: Optional[str] = None
) -> Tuple[Path, Path]:
    stem = stem or (
        f"{game.sport}_{game.away.code}_at_{game.home.code}_"
        f"{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    )
    md_path = REPORT_DIR / f"{stem}.md"
    json_path = DATA_DIR / f"{stem}.json"
    md_path.write_text(render_report(game))
    json_path.write_text(json.dumps(game.to_dict(), indent=2))
    return md_path, json_path


def append_backtest_seed(
    game: GameProjection, md_path: Path, json_path: Path
) -> Path:
    path = DATA_DIR / "backtest_seed_log.csv"
    exists = path.exists()
    raw = game.raw_game_totals()
    with path.open("a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "generated_at", "sport", "away", "home",
            "away_raw_pts", "home_raw_pts", "raw_game_pts",
            "market_total", "market_spread",
            "report_md", "report_json",
        ])
        if not exists:
            writer.writeheader()
        writer.writerow({
            "generated_at":  game.generated_at,
            "sport":        game.sport,
            "away":         game.away.code,
            "home":         game.home.code,
            "away_raw_pts": game.away.raw_totals()["pts"],
            "home_raw_pts": game.home.raw_totals()["pts"],
            "raw_game_pts": raw["pts"],
            "market_total": game.market_total if game.market_total is not None else "",
            "market_spread": game.market_spread if game.market_spread is not None else "",
            "report_md":    str(md_path),
            "report_json":  str(json_path),
        })
    return path


# ─────────────────────────────────────────────────────────────────────────────
# DIAGNOSTICS
# ─────────────────────────────────────────────────────────────────────────────

def run_diagnostics() -> str:
    lines = [
        "# Sports TC Pipeline Diagnostics",
        "",
        f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "",
        "| Check | Status |",
        "|---|---:|",
    ]
    checks: List[Tuple[str, bool]] = []

    checks.append(("NBA roster JSON exists", NBA_JSON.exists()))
    checks.append(("WNBA roster JSON exists", WNBA_JSON.exists()))

    try:
        nba_teams = _load_json_roster(NBA_JSON, "NBA")
        checks.append(("NBA teams loaded", len(nba_teams) >= 10))
        checks.append(("Every NBA team has starters", all(len(t.get("starters", [])) >= 5 for t in nba_teams.values())))
        checks.append(("Every NBA team has bench", all(len(t.get("bench", [])) >= 1 for t in nba_teams.values())))
        checks.append(("Every NBA team has injury_notes", all("injury_notes" in t for t in nba_teams.values())))
    except Exception as e:
        checks.append(("NBA JSON parse", False))

    try:
        game = build_game("NBA", "BOS @ NYK")
        checks.append(("Build NBA BOS @ NYK", True))
        checks.append(("No TC fields in game dict", "tc_game_total" not in json.dumps(game.to_dict()).lower()))
        checks.append(("Prop candidates generated", len(game.prop_candidates()) > 0))
    except Exception as e:
        checks.append(("Build NBA BOS @ NYK", False))

    try:
        game = build_game("WNBA", "DAL @ ATL", 172.5, -5.5)
        checks.append(("Build WNBA DAL @ ATL", True))
        checks.append(("No TC total fields in game dict", "tc_game_total" not in json.dumps(game.to_dict()).lower()))
        checks.append(("Prop candidates generated", len(game.prop_candidates()) > 0))
    except Exception as e:
        checks.append(("Build WNBA DAL @ ATL", False))

    for label, ok in checks:
        lines.append(f"| {label} | {'PASS' if ok else 'FAIL'} |")

    lines.extend([
        "",
        "## Rule Verification",
        (
            "Team and game totals are raw projection totals only. "
            "TC is only present under player prop floors and prop candidate fields."
        ),
    ])

    text = "\n".join(lines) + "\n"
    out = REPORT_DIR / "PIPELINE_DIAGNOSTICS.md"
    out.write_text(text)
    return text


# ─────────────────────────────────────────────────────────────────────────────
# GAME BUILDER
# ─────────────────────────────────────────────────────────────────────────────

def build_game(
    sport: str,
    game: str,
    market_total: Optional[float] = None,
    market_spread: Optional[float] = None,
) -> GameProjection:
    if "@" not in game:
        raise ValueError("Game must be formatted like 'DAL @ ATL'")
    away_code, home_code = [norm_code(x) for x in game.split("@", 1)]
    return GameProjection(
        away=load_team(sport, away_code),
        home=load_team(sport, home_code),
        sport=sport.upper(),
        market_total=market_total,
        market_spread=market_spread,
    )


# ─────────────────────────────────────────────────────────────────────────────
# MAIN CLI
# ─────────────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="Sports TC Pipeline v6.0")
    parser.add_argument("--sport",   choices=["NBA", "WNBA"], default="WNBA")
    parser.add_argument("--game",   default="DAL @ ATL")
    parser.add_argument("--total",  type=float, default=None)
    parser.add_argument("--spread", type=float, default=None)
    parser.add_argument("--save",   action="store_true")
    parser.add_argument("--json",   action="store_true")
    parser.add_argument("--diagnostics", action="store_true")
    parser.add_argument("--list-teams", action="store_true")
    args = parser.parse_args()

    if args.list_teams:
        teams = list_available_teams(args.sport)
        print(f"\n{args.sport} Teams ({len(teams)}):")
        for code, name in teams:
            print(f"  {code}: {name}")
        return

    if args.diagnostics:
        print(run_diagnostics())
        return

    game = build_game(args.sport, args.game, args.total, args.spread)

    if args.json:
        print(json.dumps(game.to_dict(), indent=2))
        return

    # Console report (human-readable)
    print_console_report(game)

    if args.save:
        md_path, json_path = save_game_outputs(game)
        log_path = append_backtest_seed(game, md_path, json_path)
        print(f"Report saved: {md_path}")
        print(f"Data saved:  {json_path}")
        print(f"Seed log:    {log_path}")


if __name__ == "__main__":
    main()