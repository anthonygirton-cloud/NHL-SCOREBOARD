#!/usr/bin/env python3
"""Save NBA regular-season schedule/results from the NBA's public static schedule file.
Output: data/nba/games.json -> {"updated":..., "games":[{"id","date","utc","home","away","hs","as","final"}]}
"""
import json, os, sys, time, urllib.request

URL = "https://cdn.nba.com/static/json/staticData/scheduleLeagueV2.json"
OUT = os.path.join(os.path.dirname(__file__), "..", "data", "nba")

def get(tries=4):
    err = None
    for i in range(tries):
        try:
            req = urllib.request.Request(URL, headers={"User-Agent": "Mozilla/5.0", "Accept": "application/json"})
            with urllib.request.urlopen(req, timeout=60) as r:
                return json.load(r)
        except Exception as e:
            err = e; time.sleep(3 * (i + 1))
    sys.exit(f"download failed: {err}")

def extract(d):
    games = []
    for day in d["leagueSchedule"]["gameDates"]:
        for g in day.get("games", []):
            gid = str(g.get("gameId", ""))
            if not gid.startswith("002"):   # regular season (incl. NBA Cup group games)
                continue
            h, a = g["homeTeam"], g["awayTeam"]
            final = g.get("gameStatus") == 3
            games.append({
                "id": gid,
                "date": (g.get("gameDateEst") or g.get("gameDateTimeEst") or "")[:10],
                "utc": g.get("gameDateTimeUTC"),
                "home": h.get("teamTricode"), "away": a.get("teamTricode"),
                "hs": h.get("score") if final else None, "as": a.get("score") if final else None,
                "final": final})
    return games

def main():
    games = extract(get())
    if not games:
        sys.exit("no games parsed; leaving files unchanged")
    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(OUT, "games.json"), "w") as f:
        json.dump({"updated": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "games": games}, f, separators=(",", ":"))
    print(f"games={len(games)} final={sum(g['final'] for g in games)}")

if __name__ == "__main__":
    main()
