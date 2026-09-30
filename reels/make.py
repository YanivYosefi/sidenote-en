#!/usr/bin/env python3
"""
Render vertical reels from content that already exists on the site.

    python reels/make.py                  # everything: 30 expressions + 5 demos
    python reels/make.py --only demo      # just the product walk-throughs
    python reels/make.py --id ship-it     # one expression
    python reels/make.py --limit 3        # a quick sample
    python reels/make.py --music track.mp3

Each reel lands in reels/out/<name>/ as reel.mp4 (1080x1920, 30fps, H.264),
cover.jpg and caption.txt.

Costs nothing per video: the content is the site's own expression pages and
homepage walk-throughs, the fonts ship in reels/fonts, and rendering is a
local browser plus ffmpeg. Needs: pip install playwright, a Chromium
(`playwright install chromium`), and ffmpeg on PATH.

Silent by default, with an empty audio track so every platform accepts the
upload. Adding a trending sound inside Instagram or TikTok is free and does
more for reach than any track picked here. --music mixes in a track you
have the rights to.
"""
import argparse, glob, html, json, os, re, shutil, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HERE = ROOT / 'reels'
FPS = 30


def text(s):
    return html.unescape(re.sub(r'<[^>]+>', '', s)).strip()


def expressions():
    out = []
    for p in sorted(glob.glob(str(ROOT / 'en' / '*' / 'index.html'))):
        s = open(p, encoding='utf-8').read()
        blocks = dict((text(h), b) for h, b in re.findall(r'<div class="expr-block"><h2>(.*?)</h2>(.*?)</div>(?=\s*<div class)', s, re.S))
        ex = re.search(r'<div class="example">(.*?)</div>', s, re.S)
        out.append(dict(
            kind='expr', slug=Path(p).parent.name,
            expr=text(re.search(r'<h1 class="expr-title">(.*?)</h1>', s, re.S).group(1)),
            cat=text(re.search(r'<span class="kind">(.*?)</span>', s, re.S).group(1)),
            meaning=text(blocks.get('מה זה אומר', '')),
            example=text(ex.group(1)) if ex else '',
            when=text(blocks.get('מתי להשתמש', '')),
        ))
    return out


def demos():
    s = open(ROOT / 'index.html', encoding='utf-8').read()
    xd = json.loads(re.search(r'var XD = (\[.*?\]);\n', s, re.S).group(1))
    return [dict(kind='demo', slug=f'demo-{i + 1}', **d) for i, d in enumerate(xd)]


def caption(job):
    tags = '#אנגלית #לימודאנגלית #ביטוייםבאנגלית #Claude #AI #Sidenote'
    if job['kind'] == 'demo':
        return ('ככה לומדים שפה בלי לפתוח אפליקציה: שואלים את Claude שאלה רגילה, '
                'ובסוף התשובה מקבלים ביטוי אחד מתוכה.\n\n'
                'Sidenote. חינם, קוד פתוח, בלי חשבון. הקישור בפרופיל.\n\n' + tags)
    return (f'{job["expr"]}: {job["meaning"]}\n\n'
            f'דוגמה: {job["example"]}\n\n'
            'Sidenote מלמד ביטוי אחד בכל שיחה עם Claude, מתוך התשובה שקיבלת. '
            'חינם, קוד פתוח. הקישור בפרופיל.\n\n' + tags)


def ffmpeg():
    exe = shutil.which('ffmpeg')
    if exe:
        return exe
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except ImportError:
        sys.exit('ffmpeg not found. Install it, or: pip install imageio-ffmpeg')


def render(page, job, dest, music=None):
    dest.mkdir(parents=True, exist_ok=True)
    page.goto((HERE / 'template.html').as_uri())
    payload = dict(job, kind=job['cat']) if job['kind'] == 'expr' else job
    dur = page.evaluate('j => setup(j)', payload)
    frames = int(dur * FPS)

    cmd = [ffmpeg(), '-y', '-loglevel', 'error', '-f', 'image2pipe', '-framerate', str(FPS), '-i', '-']
    if music:
        cmd += ['-i', str(music), '-filter_complex',
                f'[1:a]atrim=0:{dur},afade=t=in:d=0.6,afade=t=out:st={dur - 1.2}:d=1.2,volume=0.8[a]',
                '-map', '0:v', '-map', '[a]']
    else:
        cmd += ['-f', 'lavfi', '-i', 'anullsrc=r=44100:cl=stereo', '-map', '0:v', '-map', '1:a']
    cmd += ['-c:v', 'libx264', '-preset', 'slow', '-crf', '19', '-pix_fmt', 'yuv420p', '-r', str(FPS),
            '-c:a', 'aac', '-b:a', '128k', '-shortest', '-movflags', '+faststart', str(dest / 'reel.mp4')]
    enc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    cover_at = int((2.6 if job['kind'] == 'expr' else 10.0) * FPS)
    for f in range(frames):
        page.evaluate('t => render(t)', f / FPS)
        shot = page.screenshot(type='jpeg', quality=95)
        enc.stdin.write(shot)
        if f == cover_at:
            (dest / 'cover.jpg').write_bytes(shot)
    enc.stdin.close()
    if enc.wait():
        sys.exit(f'ffmpeg failed on {job["slug"]}')
    (dest / 'caption.txt').write_text(caption(job), encoding='utf-8')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--only', choices=['expr', 'demo'])
    ap.add_argument('--id')
    ap.add_argument('--limit', type=int)
    ap.add_argument('--music')
    ap.add_argument('--out', default=str(HERE / 'out'))
    a = ap.parse_args()

    jobs = ([] if a.only == 'demo' else expressions()) + ([] if a.only == 'expr' else demos())
    if a.id:
        jobs = [j for j in jobs if j['slug'] == a.id]
    if a.limit:
        jobs = jobs[:a.limit]
    if not jobs:
        sys.exit('nothing to render')

    from playwright.sync_api import sync_playwright
    exe = os.environ.get('CHROMIUM') or ('/opt/pw-browsers/chromium' if os.path.exists('/opt/pw-browsers/chromium') else None)
    with sync_playwright() as p:
        b = p.chromium.launch(**({'executable_path': exe} if exe else {}))
        page = b.new_page(viewport={'width': 1080, 'height': 1920}, device_scale_factor=1)
        for i, j in enumerate(jobs, 1):
            print(f'[{i}/{len(jobs)}] {j["slug"]}', flush=True)
            render(page, j, Path(a.out) / j['slug'], a.music)
        b.close()
    print(f'done: {len(jobs)} reel(s) in {a.out}')


if __name__ == '__main__':
    main()
