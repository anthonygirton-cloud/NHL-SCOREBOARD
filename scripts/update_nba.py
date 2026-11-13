#!/usr/bin/env python3
"""Save NBA regular-season schedule/results from the NBA's public static schedule file.
Output: data/nba/games.json -> {"updated":..., "games":[{"id","date","utc","home","away","hs","as","final"}]}
"""
import datetime, json, os, sys, time, urllib.request

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
    print(f"NBA CDN failed: {err}", file=sys.stderr)
    return None

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

ESPN = "https://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard?dates={d}&limit=100"
FIX = {"GS": "GSW", "NY": "NYK", "SA": "SAS", "NO": "NOP", "WSH": "WAS", "UTAH": "UTA", "PHO": "PHX"}
SEASON_START = datetime.date(2026, 10, 18)

def espn_day(d):
    for i in range(3):
        try:
            req = urllib.request.Request(ESPN.format(d=d.strftime("%Y%m%d")), headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.load(r).get("events", [])
        except Exception as e:
            err = e; time.sleep(2 * (i + 1))
    print(f"ESPN failed for {d}: {err}", file=sys.stderr)
    return None

def from_espn():
    path = os.path.join(OUT, "games.json")
    old = {}
    if os.path.exists(path):
        try:
            old = {g["id"]: g for g in json.load(open(path))["games"]}
        except Exception:
            old = {}
    finals = [g["date"] for g in old.values() if g.get("final")]
    start = SEASON_START
    if finals:
        start = max(start, datetime.date.fromisoformat(max(finals)) - datetime.timedelta(days=3))
    day, today = start, datetime.date.today() + datetime.timedelta(days=1)
    got = 0
    while day <= today:
        evs = espn_day(day)
        if evs is None:
            day += datetime.timedelta(days=1); continue
        for e in evs:
            try:
                if (e.get("season") or {}).get("type") != 2:
                    continue
                c = e["competitions"][0]
                t = {x["homeAway"]: x for x in c["competitors"]}
                fin = bool(c["status"]["type"].get("completed"))
                ab = lambda x: FIX.get(x["team"]["abbreviation"], x["team"]["abbreviation"])
                old["e" + str(e["id"])] = {"id": "e" + str(e["id"]), "date": day.isoformat(), "utc": e.get("date"),
                    "home": ab(t["home"]), "away": ab(t["away"]),
                    "hs": int(t["home"]["score"]) if fin else None, "as": int(t["away"]["score"]) if fin else None, "final": fin}
                got += 1
            except Exception as ex:
                print("skip event:", ex, file=sys.stderr)
        day += datetime.timedelta(days=1); time.sleep(0.3)
    print("espn events parsed:", got)
    return sorted(old.values(), key=lambda g: (g["date"], g["id"]))

def main():
    games = []
    d = get()
    if d:
        try:
            games = extract(d)
        except Exception as e:
            print(f"NBA CDN parse failed: {e}", file=sys.stderr)
    if not games:
        print("falling back to ESPN scoreboard")
        games = from_espn()
    if not games:
        sys.exit("no games parsed; leaving files unchanged")
    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(OUT, "games.json"), "w") as f:
        json.dump({"updated": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "games": games}, f, separators=(",", ":"))
    print(f"games={len(games)} final={sum(g['final'] for g in games)}")

if __name__ == "__main__":
    main()
