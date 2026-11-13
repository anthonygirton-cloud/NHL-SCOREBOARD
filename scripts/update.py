#!/usr/bin/env python3
"""Mirror NHL public API data into data/ in the layout the goalie dashboard reads.
Writes: data/seasons/<SEASON>/<TEAM>.json, data/games/<id>-boxscore.json (trimmed), data/manifest.json
"""
import json, os, sys, time, urllib.request, urllib.error

SEASON = os.environ.get("NHL_SEASON", "20262027")
BASE = "https://api-web.nhle.com/v1"
ROOT = os.path.join(os.path.dirname(__file__), "..", "data")
TEAMS = ("ANA BOS BUF CGY CAR CHI COL CBJ DAL DET EDM FLA LAK MIN MTL NSH NJD NYI NYR OTT PHI PIT SEA SJS STL TBL "
         "TOR UTA VAN VGK WSH WPG").split()
TEAMS = [("CGY" if t == "CGY" else t) for t in TEAMS]
FINAL = ("FINAL", "OFF")

def get(url, tries=4):
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "nhl-mirror/1.0"})
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None
            err = e
        except Exception as e:
            err = e
        time.sleep(2 * (i + 1))
    print("giving up:", url, err, file=sys.stderr)
    return None

def dump(path, obj):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        json.dump(obj, f, separators=(",", ":"))

def trim_box(b):
    def side(k):
        gs = (b.get("playerByGameStats", {}).get(k, {}) or {}).get("goalies", []) or []
        return {"goalies": [{"starter": g.get("starter"), "savePctg": g.get("savePctg"),
                             "toi": g.get("toi")} for g in gs]}
    return {"id": b.get("id"), "gameDate": b.get("gameDate"),
            "homeTeam": {"abbrev": b["homeTeam"]["abbrev"]},
            "awayTeam": {"abbrev": b["awayTeam"]["abbrev"]},
            "playerByGameStats": {"homeTeam": side("homeTeam"), "awayTeam": side("awayTeam")}}

def main():
    final_ids, teams_ok = set(), []
    for t in TEAMS:
        d = get(f"{BASE}/club-schedule-season/{t}/{SEASON}")
        if not d or "games" not in d:
            print("no schedule for", t, file=sys.stderr); continue
        teams_ok.append(t)
        dump(os.path.join(ROOT, "seasons", SEASON, f"{t}.json"), {"games": d["games"]})
        for g in d["games"]:
            if g.get("gameType") == 2 and g.get("gameState") in FINAL:
                final_ids.add(g["id"])
    if not teams_ok:
        sys.exit("no schedules fetched; aborting without changes")
    gdir = os.path.join(ROOT, "games"); os.makedirs(gdir, exist_ok=True)
    new = 0
    for gid in sorted(final_ids):
        p = os.path.join(gdir, f"{gid}-boxscore.json")
        if os.path.exists(p):
            continue
        b = get(f"{BASE}/gamecenter/{gid}/boxscore")
        if b and b.get("homeTeam") and b.get("playerByGameStats"):
            dump(p, trim_box(b)); new += 1
    files = {f"box:{n.split('-')[0]}": 1 for n in os.listdir(gdir) if n.endswith("-boxscore.json")}
    dump(os.path.join(ROOT, "manifest.json"),
         {"updated": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "season": SEASON,
          "seasons": {"teams": teams_ok}, "files": files})
    print(f"teams={len(teams_ok)} final_games={len(final_ids)} new_boxscores={new}")

if __name__ == "__main__":
    main()
