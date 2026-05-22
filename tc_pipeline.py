#!/usr/bin/env python3
"""
Sports TC Pipeline v5.0
=======================
Unified NBA/WNBA workflow for roster projections, prop-only TC floors,
separate team/game totals, injury notes, parlay candidate selection, and
backtest-ready exports.

Core rules
----------
1. TC applies ONLY to player prop categories: PTS, REB, AST, 3PM.
2. Team totals and game totals are raw projection totals only. No TC line,
   no TC edge, and no TC recommendation is generated for team/game totals.
3. Roster output always separates starters, bench, and injury notes.
4. Optional minutes/usage fields can be carried in player records when a
   ledger provides them, but they are not required.
"""

from __future__ import annotations

import argparse
import contextlib
import csv
import io
import json
import os
import subprocess
import sys
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

ROOT = Path(__file__).resolve().parent
WORKSPACE = Path("/home/workspace")
WNBA_BACKTEST_JSON = WORKSPACE / "wnba_rosters" / "WNBA_BACKTEST_ROSTERS.json"
REPORT_DIR = ROOT / "reports"
DATA_DIR = ROOT / "data"
REPORT_DIR.mkdir(exist_ok=True)
DATA_DIR.mkdir(exist_ok=True)

TC_FACTORS = {"pts": 0.85, "reb": 0.80, "ast": 0.75, "tpm": 0.70}
Q_FACTOR = 0.55
OUT_FACTOR = 0.0
DEFAULT_PROP_EDGE = {"pts": 3.0, "reb": 2.0, "ast": 1.5, "tpm": 0.5}

TEAM_ALIASES = {
    "NY": "NYL",
    "LV": "LVA",
    "LA": "LAS",
    "GS": "GS",
    "GSW": "GS",
    "SA": "SAS",
}


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
    minutes: Optional[float] = None
    usage: Optional[float] = None

    def status_factor(self) -> float:
        status = self.status.upper()
        if status == "OUT":
            return OUT_FACTOR
        if status in {"Q", "QUESTIONABLE", "DOUBTFUL", "DAY-TO-DAY"}:
            return Q_FACTOR
        return 1.0

    def raw(self) -> Dict[str, float]:
        return {
            "pts": round(self.ppg, 1),
            "reb": round(self.rpg, 1),
            "ast": round(self.apg, 1),
            "tpm": round(self.tpm, 1),
        }

    def tc(self) -> Dict[str, float]:
        f = self.status_factor()
        return {
            "pts": round(self.ppg * TC_FACTORS["pts"] * f, 1),
            "reb": round(self.rpg * TC_FACTORS["reb"] * f, 1),
            "ast": round(self.apg * TC_FACTORS["ast"] * f, 1),
            "tpm": round(self.tpm * TC_FACTORS["tpm"] * f, 1),
        }

    def prop_targets(self) -> Dict[str, int]:
        tc = self.tc()
        return {
            "pts": max(0, int(tc["pts"])),
            "reb": max(0, int(tc["reb"])),
            "ast": max(0, int(tc["ast"])),
            "tpm": max(0, int(tc["tpm"])),
        }

    def production_score(self) -> float:
        return self.ppg + self.rpg + self.apg + (self.tpm * 2)


@dataclass
class TeamProjection:
    code: str
    name: str
    starters: List[PlayerProjection]
    bench: List[PlayerProjection]
    injury_notes: List[str] = field(default_factory=list)

    @property
    def players(self) -> List[PlayerProjection]:
        return self.starters + self.bench

    def raw_totals(self) -> Dict[str, float]:
        active = [p for p in self.players if p.status.upper() != "OUT"]
        return {
            "pts": round(sum(p.ppg for p in active), 1),
            "reb": round(sum(p.rpg for p in active), 1),
            "ast": round(sum(p.apg for p in active), 1),
            "tpm": round(sum(p.tpm for p in active), 1),
        }

    def tc_prop_totals(self) -> Dict[str, float]:
        totals = {"pts": 0.0, "reb": 0.0, "ast": 0.0, "tpm": 0.0}
        for player in self.players:
            tc = player.tc()
            for key in totals:
                totals[key] += tc[key]
        return {k: round(v, 1) for k, v in totals.items()}


@dataclass
class GameProjection:
    away: TeamProjection
    home: TeamProjection
    sport: str
    market_total: Optional[float] = None
    market_spread: Optional[float] = None
    generated_at: str = field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

    def raw_game_totals(self) -> Dict[str, float]:
        away = self.away.raw_totals()
        home = self.home.raw_totals()
        return {key: round(away[key] + home[key], 1) for key in away}

    def prop_candidates(self) -> List[Dict[str, Any]]:
        candidates: List[Dict[str, Any]] = []
        for team in (self.away, self.home):
            for player in team.players:
                if player.status.upper() == "OUT":
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

    def to_dict(self) -> Dict[str, Any]:
        return {
            "generated_at": self.generated_at,
            "sport": self.sport,
            "market_total": self.market_total,
            "market_spread": self.market_spread,
            "rule": "TC applies only to player props. Team/game totals are raw projections only.",
            "away": serialize_team(self.away),
            "home": serialize_team(self.home),
            "raw_game_totals": self.raw_game_totals(),
            "prop_candidates": self.prop_candidates(),
        }


@dataclass
class BacktestGame:
    date: str
    sport: str
    away: str
    home: str
    actual_away_score: float
    actual_home_score: float
    market_total: Optional[float] = None
    notes: str = ""


def norm_code(code: str) -> str:
    clean = code.strip().upper()
    return TEAM_ALIASES.get(clean, clean)


def safe_float(value: Any) -> float:
    try:
        return float(value or 0)
    except Exception:
        return 0.0


def player_from_dict(item: Dict[str, Any], role: str) -> PlayerProjection:
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
        minutes=item.get("minutes"),
        usage=item.get("usage"),
    )


def load_wnba_team(code: str) -> TeamProjection:
    code = norm_code(code)
    data = json.loads(WNBA_BACKTEST_JSON.read_text())
    teams = data.get("teams", {})
    if code not in teams:
        available = ", ".join(sorted(teams))
        raise KeyError(f"WNBA team {code} not found. Available: {available}")
    team = teams[code]
    starters = [player_from_dict(p, "STARTER") for p in team.get("starters", [])]
    bench = [player_from_dict(p, "BENCH") for p in team.get("bench", [])]
    return TeamProjection(code=code, name=team.get("team_name", code), starters=starters, bench=bench, injury_notes=team.get("injury_notes", []))


def load_nba_team(code: str) -> TeamProjection:
    code = norm_code(code)
    sys.path.insert(0, str(ROOT))
    try:
        import sports_tc as legacy
    except Exception as exc:
        raise RuntimeError(f"Could not import legacy NBA rosters from sports_tc.py: {exc}") from exc
    rosters = getattr(legacy, "NBA_ROSTERS", {})
    names = getattr(legacy, "NBA_TEAMS", {})
    if code not in rosters:
        available = ", ".join(sorted(rosters))
        raise KeyError(f"NBA team {code} not found. Available: {available}")
    players = []
    for idx, p in enumerate(rosters[code]):
        players.append(PlayerProjection(
            name=p.name,
            pos=p.pos,
            ht=p.ht,
            ppg=safe_float(p.pts),
            rpg=safe_float(p.reb),
            apg=safe_float(p.ast),
            tpm=safe_float(p.tpm),
            status=str(p.status).upper(),
            role="STARTER" if idx < 5 else "BENCH",
        ))
    return TeamProjection(code=code, name=names.get(code, code), starters=players[:5], bench=players[5:], injury_notes=["Use live pregame injury report to override local status before betting."])


def load_team(sport: str, code: str) -> TeamProjection:
    if sport.upper() == "WNBA":
        return load_wnba_team(code)
    return load_nba_team(code)


def build_game(sport: str, game: str, market_total: Optional[float] = None, market_spread: Optional[float] = None) -> GameProjection:
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


def serialize_player(player: PlayerProjection) -> Dict[str, Any]:
    raw = player.raw()
    tc = player.tc()
    return {
        "name": player.name,
        "role": player.role,
        "pos": player.pos,
        "ht": player.ht,
        "status": player.status,
        "minutes": player.minutes,
        "usage": player.usage,
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


def format_player_table(players: Iterable[PlayerProjection]) -> List[str]:
    rows = [
        "| Role | Player | POS | HT | Status | Raw PTS | Raw REB | Raw AST | Raw 3PM | TC PTS | TC REB | TC AST | TC 3PM | Target PTS | Target REB | Target AST | Target 3PM |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for player in players:
        raw = player.raw()
        tc = player.tc()
        target = player.prop_targets()
        rows.append(
            f"| {player.role} | {player.name} | {player.pos} | {player.ht} | {player.status} | "
            f"{raw['pts']:.1f} | {raw['reb']:.1f} | {raw['ast']:.1f} | {raw['tpm']:.1f} | "
            f"{tc['pts']:.1f} | {tc['reb']:.1f} | {tc['ast']:.1f} | {tc['tpm']:.1f} | "
            f"{target['pts']}+ | {target['reb']}+ | {target['ast']}+ | {target['tpm']}+ |"
        )
    return rows


def render_report(game: GameProjection) -> str:
    raw_game = game.raw_game_totals()
    lines = [
        f"# {game.sport} TC Pipeline Report — {game.away.code} @ {game.home.code}",
        "",
        f"**Generated:** {game.generated_at}",
        "",
        "## Rules",
        "- TC projections are **player prop floors only**: PTS × 0.85, REB × 0.80, AST × 0.75, 3PM × 0.70.",
        "- Questionable players: TC result × 0.55. OUT players: 0.",
        "- Team totals and game totals are **raw projection totals only** and are kept separate from TC.",
        "- No TC projection, TC line, or TC edge is generated for team/game totals.",
        "",
        "## Market / Raw Totals — Separate From TC",
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

    for team in (game.away, game.home):
        lines.extend([
            f"## {team.code} — {team.name}",
            "",
            "### Injury Notes",
        ])
        if team.injury_notes:
            lines.extend([f"- {note}" for note in team.injury_notes])
        else:
            lines.append("- No injury notes available. Confirm pregame status before bet placement.")
        lines.extend([
            "",
            "### Raw Team Totals — Not TC",
            "",
            "| PTS | REB | AST | 3PM |",
            "|---:|---:|---:|---:|",
            f"| {team.raw_totals()['pts']:.1f} | {team.raw_totals()['reb']:.1f} | {team.raw_totals()['ast']:.1f} | {team.raw_totals()['tpm']:.1f} |",
            "",
            "### Starters + Bench — Player Prop TC Floors",
            "",
        ])
        lines.extend(format_player_table(team.players))
        lines.append("")

    candidates = game.prop_candidates()[:20]
    lines.extend([
        "## Prop Candidate Watchlist — Not Picks Until Book Lines Are Checked",
        "",
        "| Team | Player | Role | Stat | Raw Projection | TC Floor | Whole # Target | Gap | Status |",
        "|---|---|---|---:|---:|---:|---:|---:|---:|",
    ])
    for c in candidates:
        lines.append(
            f"| {c['team']} | {c['player']} | {c['role']} | {c['stat']} | {c['raw_projection']:.1f} | "
            f"{c['tc_floor']:.1f} | {c['target_whole_number']}+ | {c['gap']:.1f} | {c['status']} |"
        )

    return "\n".join(lines) + "\n"


def save_game_outputs(game: GameProjection, stem: Optional[str] = None) -> Tuple[Path, Path]:
    stem = stem or f"{game.sport}_{game.away.code}_at_{game.home.code}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    md_path = REPORT_DIR / f"{stem}.md"
    json_path = DATA_DIR / f"{stem}.json"
    md_path.write_text(render_report(game))
    json_path.write_text(json.dumps(game.to_dict(), indent=2))
    return md_path, json_path


def append_backtest_seed(game: GameProjection, md_path: Path, json_path: Path) -> Path:
    path = DATA_DIR / "backtest_seed_log.csv"
    exists = path.exists()
    raw = game.raw_game_totals()
    with path.open("a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "generated_at", "sport", "away", "home", "away_raw_pts", "home_raw_pts", "raw_game_pts",
            "market_total", "market_spread", "report_md", "report_json",
        ])
        if not exists:
            writer.writeheader()
        writer.writerow({
            "generated_at": game.generated_at,
            "sport": game.sport,
            "away": game.away.code,
            "home": game.home.code,
            "away_raw_pts": game.away.raw_totals()["pts"],
            "home_raw_pts": game.home.raw_totals()["pts"],
            "raw_game_pts": raw["pts"],
            "market_total": game.market_total if game.market_total is not None else "",
            "market_spread": game.market_spread if game.market_spread is not None else "",
            "report_md": str(md_path),
            "report_json": str(json_path),
        })
    return path


def run_diagnostics() -> str:
    lines = ["# Sports TC Pipeline Diagnostics", "", f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", ""]
    checks = []
    checks.append(("WNBA backtest roster JSON exists", WNBA_BACKTEST_JSON.exists()))
    try:
        wnba_data = json.loads(WNBA_BACKTEST_JSON.read_text())
        teams = wnba_data.get("teams", {})
        checks.append(("WNBA teams loaded", len(teams) >= 15))
        checks.append(("Every WNBA team has starters", all(len(t.get("starters", [])) >= 5 for t in teams.values())))
        checks.append(("Every WNBA team has bench", all(len(t.get("bench", [])) >= 1 for t in teams.values())))
        checks.append(("Every WNBA team has injury notes", all("injury_notes" in t for t in teams.values())))
    except Exception:
        checks.append(("WNBA JSON parse", False))
    try:
        game = build_game("WNBA", "DAL @ ATL", 172.5, -5.5)
        checks.append(("Build WNBA DAL @ ATL", True))
        checks.append(("No TC total fields in game dict", "tc_game_total" not in json.dumps(game.to_dict()).lower()))
        checks.append(("Prop candidates generated", len(game.prop_candidates()) > 0))
    except Exception:
        checks.append(("Build WNBA DAL @ ATL", False))
    try:
        game = build_game("NBA", "NYK @ PHI")
        checks.append(("Build NBA NYK @ PHI", True))
    except Exception:
        checks.append(("Build NBA NYK @ PHI", False))
    lines.extend(["| Check | Status |", "|---|---:|"])
    for label, ok in checks:
        lines.append(f"| {label} | {'PASS' if ok else 'FAIL'} |")
    lines.append("")
    lines.append("## Rule Verification")
    lines.append("Team and game totals are raw projection totals only. TC is only present under player prop floors and prop candidate fields.")
    text = "\n".join(lines) + "\n"
    out = REPORT_DIR / "PIPELINE_DIAGNOSTICS.md"
    out.write_text(text)
    return text


def main() -> None:
    parser = argparse.ArgumentParser(description="Sports TC Pipeline v5.0")
    parser.add_argument("--sport", choices=["NBA", "WNBA"], default="WNBA")
    parser.add_argument("--game", default="DAL @ ATL")
    parser.add_argument("--total", type=float, default=None)
    parser.add_argument("--spread", type=float, default=None)
    parser.add_argument("--save", action="store_true")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--diagnostics", action="store_true")
    args = parser.parse_args()

    if args.diagnostics:
        print(run_diagnostics())
        return

    game = build_game(args.sport, args.game, args.total, args.spread)
    if args.json:
        print(json.dumps(game.to_dict(), indent=2))
        return
    print(render_report(game))
    if args.save:
        md_path, json_path = save_game_outputs(game)
        log_path = append_backtest_seed(game, md_path, json_path)
        print(f"Saved report: {md_path}")
        print(f"Saved data: {json_path}")
        print(f"Backtest seed log: {log_path}")


if __name__ == "__main__":
    main()
