#!/usr/bin/env python3
"""
Download the stock footage the b-roll reels are cut from.

    python reels/fetch_broll.py            # every clip in make.BROLL that is missing
    python reels/fetch_broll.py --redo     # fetch again, e.g. after changing a query
    python reels/fetch_broll.py --pick typing-night=3   # use the 3rd result instead

Reads the Pexels key from PEXELS_API_KEY, or from ~/.claude/.pexels_key. The
key is only sent to api.pexels.com and never printed. Pexels footage is free to
use; credit is kept in reels/broll/credits.json and added to each reel's caption.

For each clip: portrait results only, at least 6 seconds, and of those the one
whose largest file is closest to 1080x1920 without going under it (sharp enough,
not a 4K download for a phone screen). The other good candidates are listed in
reels/broll/candidates.json, to swap with --pick.
"""
import argparse, json, os, sys, urllib.parse, urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from make import BROLL, BROLL_DIR  # noqa: E402


def key():
    k = os.environ.get('PEXELS_API_KEY', '').strip()
    f = Path.home() / '.claude' / '.pexels_key'
    if not k and f.exists():
        k = f.read_text().strip()
    if not k:
        sys.exit('No Pexels key: set PEXELS_API_KEY or put it in ~/.claude/.pexels_key (free at pexels.com/api).')
    return k


def get(url, k):
    req = urllib.request.Request(url, headers={'Authorization': k, 'User-Agent': 'sidenote-reels'})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def best_file(video):
    files = [f for f in video.get('video_files', []) if f.get('height') and f.get('width')
             and f['height'] > f['width'] and f.get('file_type') == 'video/mp4']
    sharp = sorted((f for f in files if f['width'] >= 1080), key=lambda f: f['width'])
    return sharp[0] if sharp else (max(files, key=lambda f: f['width']) if files else None)


def candidates(query, k):
    q = urllib.parse.urlencode({'query': query, 'orientation': 'portrait', 'size': 'large', 'per_page': 15})
    out = []
    for v in get(f'https://api.pexels.com/videos/search?{q}', k).get('videos', []):
        f = best_file(v)
        if f and v.get('duration', 0) >= 6:
            out.append(dict(id=v['id'], page=v['url'], by=v['user']['name'], seconds=v['duration'],
                            width=f['width'], height=f['height'], link=f['link']))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--redo', action='store_true')
    ap.add_argument('--pick', action='append', default=[], help='name=N, the Nth candidate (1-based)')
    a = ap.parse_args()
    picks = dict((p.split('=')[0], int(p.split('=')[1])) for p in a.pick)
    k = key()
    BROLL_DIR.mkdir(exist_ok=True)
    cf, af = BROLL_DIR / 'credits.json', BROLL_DIR / 'candidates.json'
    credits = json.load(open(cf)) if cf.exists() else {}
    cands = json.load(open(af)) if af.exists() else {}
    for name, query in BROLL.items():
        dest = BROLL_DIR / f'{name}.mp4'
        if dest.exists() and not a.redo and name not in picks:
            print(f'  have  {name}')
            continue
        found = candidates(query, k)
        if not found:
            print(f'  none  {name}  ({query})')
            continue
        cands[name] = found[:8]
        c = found[min(picks.get(name, 1), len(found)) - 1]
        urllib.request.urlretrieve(c['link'], dest)
        credits[name] = c['by']
        print(f'  got   {name}: {c["width"]}x{c["height"]}, {c["seconds"]}s, by {c["by"]}')
    json.dump(credits, open(cf, 'w'), ensure_ascii=False, indent=2)
    json.dump(cands, open(af, 'w'), ensure_ascii=False, indent=2)
    print('now: python reels/make.py --broll')


if __name__ == '__main__':
    main()
