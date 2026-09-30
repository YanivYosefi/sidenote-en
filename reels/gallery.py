#!/usr/bin/env python3
"""
Turn a folder of rendered reels into something a person (or another Claude)
can browse and pick from.

    python reels/gallery.py <folder>

Adds to <folder>:
  index.html      every reel in a grid, grouped by audience and format,
                  playable in place, with its post caption and a copy button
  manifest.json   the same list as data: audience, format, files, length, caption
  images/         the phrase share cards and the site's marketing stills
  EDITOR.md       what is here and what is left to do (music, voice, b-roll)
"""
import json, re, shutil, subprocess, sys
from pathlib import Path

from make import ROOT, ffmpeg

AUDIENCES = {
    'he-learning-english': 'דוברי עברית שלומדים אנגלית',
    'en-learning-languages': 'English speakers learning Spanish, French, Italian',
    'learning-hebrew': 'English speakers learning Hebrew',
}
FORMATS = {
    'expression': 'ביטוי · one expression', 'quiz': 'חידון · quiz', 'top3': 'שלושה · top 3',
    'versus': 'זה או זה · this vs that', 'demo': 'דמו · chat demo', 'pov': 'POV',
    'screen': 'מסך · laptop screen', 'literally': 'מילולית · literally / actually',
}


def duration(mp4):
    out = subprocess.run([ffmpeg(), '-i', str(mp4)], capture_output=True, text=True).stderr
    m = re.search(r'Duration: (\d+):(\d+):([\d.]+)', out)
    return round(int(m.group(1)) * 3600 + int(m.group(2)) * 60 + float(m.group(3)), 1) if m else None


def main(folder):
    root = Path(folder)
    items = []
    for mp4 in sorted(root.glob('*/*/*/reel.mp4')):
        d = mp4.parent
        aud, fmt, slug = d.parts[-3], d.parts[-2], d.parts[-1]
        items.append(dict(audience=aud, format=fmt, slug=slug,
                          video=str(mp4.relative_to(root)), cover=str((d / 'cover.jpg').relative_to(root)),
                          caption_file=str((d / 'caption.txt').relative_to(root)),
                          seconds=duration(mp4), caption=(d / 'caption.txt').read_text(encoding='utf-8')))
    (root / 'manifest.json').write_text(json.dumps(items, ensure_ascii=False, indent=2), encoding='utf-8')

    img = root / 'images'
    (img / 'share-cards').mkdir(parents=True, exist_ok=True)
    for f in (ROOT / 'media' / 'og').glob('*.jpg'):
        shutil.copy(f, img / 'share-cards' / f.name)
    (img / 'site').mkdir(exist_ok=True)
    for pat in ('og-*.png', 'goal-*-square.jpg', 'sidenote-social-*.png', 'social-3-days.png', 'film2-poster*.jpg', 'icon-512.png'):
        for f in (ROOT / 'media').glob(pat):
            shutil.copy(f, img / 'site' / f.name)

    esc = lambda s: s.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;').replace('"', '&quot;')
    sections = []
    for aud, aname in AUDIENCES.items():
        mine = [i for i in items if i['audience'] == aud]
        if not mine:
            continue
        blocks = []
        for fmt, fname in FORMATS.items():
            group = [i for i in mine if i['format'] == fmt]
            if not group:
                continue
            cards = ''.join(f'''
      <figure>
        <video src="{i['video']}" poster="{i['cover']}" controls preload="none" playsinline></video>
        <figcaption><b>{esc(i['slug'])}</b> <span>{i['seconds']}s</span>
          <details><summary>caption</summary><pre dir="auto">{esc(i['caption'])}</pre>
          <button type="button" data-t="{esc(i['caption'])}">copy</button></details></figcaption>
      </figure>''' for i in group)
            blocks.append(f'<h3>{fname} <small>{len(group)}</small></h3><div class="grid">{cards}</div>')
        sections.append(f'<section><h2>{aname} <small>{len(mine)}</small></h2>{"".join(blocks)}</section>')

    (root / 'index.html').write_text(f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Sidenote reels</title>
<style>
  :root{{--teal:#00857C;--ink:#1F2A29;--gray:#5E6B69;--line:#D9E7E4;--wash:#EDF6F4}}
  body{{margin:0;background:var(--wash);font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Arial,sans-serif;color:var(--ink)}}
  header{{padding:28px 24px 8px}} h1{{margin:0 0 6px;font-size:28px}} header p{{margin:0;color:var(--gray)}}
  section{{padding:10px 24px 30px}} h2{{border-bottom:2px solid var(--teal);padding-bottom:6px}}
  h3{{margin:24px 0 10px;color:var(--teal)}} small{{color:var(--gray);font-weight:400}}
  .grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(200px,1fr));gap:16px}}
  figure{{margin:0;background:#fff;border:1px solid var(--line);border-radius:12px;overflow:hidden}}
  video{{width:100%;aspect-ratio:9/16;display:block;background:#000}}
  figcaption{{padding:8px 10px;font-size:13px}} figcaption span{{color:var(--gray)}}
  pre{{white-space:pre-wrap;font-size:12px;background:var(--wash);padding:8px;border-radius:6px}}
  button{{border:1px solid var(--teal);background:#fff;color:var(--teal);border-radius:6px;padding:4px 10px;cursor:pointer}}
</style></head><body>
<header><h1>Sidenote reels <small>{len(items)}</small></h1>
<p>1080×1920 · 30fps · H.264 · silent audio track. Every reel has a cover and a ready caption. See EDITOR.md.</p></header>
{"".join(sections)}
<script>document.querySelectorAll('button[data-t]').forEach(b=>b.onclick=()=>{{navigator.clipboard.writeText(b.dataset.t);b.textContent='copied'}})</script>
</body></html>''', encoding='utf-8')

    counts = {}
    for i in items:
        counts.setdefault(i['audience'], {}).setdefault(i['format'], 0)
        counts[i['audience']][i['format']] += 1
    table = '\n'.join(f'| `{a}/{f}` | {n} |' for a, fs in counts.items() for f, n in fs.items())
    (root / 'EDITOR.md').write_text(f'''# Sidenote reels: editor's brief

{len(items)} vertical reels, rendered from the Sidenote site's own content by `reels/make.py` in the
sidenote-en repository. Open `index.html` to watch them all in one page. `manifest.json` is the same list as data.

## What is here

| folder | reels |
|---|---|
{table}

Each reel folder holds `reel.mp4` (1080×1920, 30fps, H.264, silent AAC track), `cover.jpg`
(the frame to use as the cover) and `caption.txt` (post text with hashtags).

`images/share-cards/` has the 1200×630 card of every phrase page; `images/site/` has the site's
existing marketing stills (link previews, goal photos, social squares).

## Audiences

- **he-learning-english**: Hebrew speakers learning English. The bulk; all text in Hebrew.
- **en-learning-languages**: English speakers learning Spanish, French or Italian. English interface.
- **learning-hebrew**: English speakers learning Hebrew. English interface, Hebrew expressions.

The English-audience content comes from `reels/content-en.json`: a small hand-written sample. Check it
before publishing.

## What is left to do

1. **Pick.** The owner has not chosen formats yet. Start from one of each and find what works.
2. **Sound.** The reels are silent on purpose. A trending sound added inside Instagram or TikTok is
   free and helps reach. For a fixed track, use one you hold the rights to:
   `python reels/make.py --music track.mp3 ...`, or mix it over the mp4 directly.
3. **Voice.** Nothing is narrated. The on-screen text carries the story, so a voice-over is optional.
4. **B-roll.** `pov` and `screen` would take real footage well: a person at a desk before the laptop
   shot, a street for the travel lines.
5. **Subtitles.** All text is already drawn into the picture. No separate subtitle file is needed
   unless you add a voice.

## Changing a reel instead of editing the video

The text, the timing and the look live in `reels/template.html`; the content in the site's phrase
pages and `reels/content-en.json`. Change those and re-render: that keeps every reel consistent.

    python reels/make.py --id <slug>          # one reel
    python reels/make.py --library --workers 4 --out <folder> && python reels/gallery.py <folder>
''', encoding='utf-8')
    print(f'{len(items)} reels indexed in {root}')


if __name__ == '__main__':
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    main(sys.argv[1] if len(sys.argv) > 1 else str(Path(__file__).resolve().parent / 'out'))
