#!/usr/bin/env python3
"""Build per-week QB EPA/dropback aggregates from nflverse play-by-play.
Output: data/nfl/epa_<season>.json  ->  {"<season>": {"<week>": {"<TEAM>": {"<passer>": [epa_sum, dropbacks]}}}}
"""
import csv, gzip, io, json, os, sys, time, urllib.request, urllib.error, datetime

URL = "https://github.com/nflverse/nflverse-data/releases/download/pbp/play_by_play_{season}.csv.gz"
OUT = os.path.join(os.path.dirname(__file__), "..", "data", "nfl")

def current_season():
    t = datetime.date.today()
    return int(os.environ.get("NFL_SEASON") or (t.year if t.month >= 8 else t.year - 1))

def download(url, tries=4):
    err = None
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "nfl-epa/1.0"})
            with urllib.request.urlopen(req, timeout=180) as r:
                return r.read()
        except Exception as e:
            err = e; time.sleep(3 * (i + 1))
    sys.exit(f"download failed: {url}: {err}")

def aggregate(rows):
    out = {}
    for r in rows:
        if r.get("season_type") != "REG" or r.get("qb_dropback") not in ("1", "1.0"):
            continue
        team, passer, epa, wk = r.get("posteam"), r.get("passer"), r.get("epa"), r.get("week")
        if not (team and passer and epa not in (None, "", "NA") and wk):
            continue
        slot = out.setdefault(str(int(float(wk))), {}).setdefault(team, {}).setdefault(passer, [0.0, 0])
        slot[0] += float(epa); slot[1] += 1
    for wk in out.values():
        for t in wk.values():
            for p in t.values():
                p[0] = round(p[0], 4)
    return out

def main():
    season = current_season()
    raw = download(URL.format(season=season))
    text = gzip.decompress(raw).decode("utf-8")
    agg = aggregate(csv.DictReader(io.StringIO(text)))
    if not agg:
        sys.exit("no regular-season dropbacks found; leaving files unchanged")
    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(OUT, f"epa_{season}.json"), "w") as f:
        json.dump({str(season): agg, "updated": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                   "throughWeek": max(int(w) for w in agg)}, f, separators=(",", ":"))
    print(f"season={season} weeks={sorted(int(w) for w in agg)}")

if __name__ == "__main__":
    main()
