#!/usr/bin/env python3
"""
Draw the share picture for every phrase page, and point the page at it.

    python reels/og.py

Writes media/og/<slug>.jpg (1200x630) for each page in en/ and sets that
page's og:image and twitter:image to it, with a large Twitter card. Run it
again after adding a phrase page. Needs playwright and a Chromium.
"""
import os, re, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from make import expressions, ROOT, HERE  # noqa: E402

SITE = 'https://yanivyosefi.github.io/sidenote-en'
OUT = ROOT / 'media' / 'og'


def point(page_path, image_url):
    s = page_path.read_text(encoding='utf-8')
    s = re.sub(r'\n<meta property="og:image:(width|height)" content="\d+">', '', s)  # safe to re-run
    s = re.sub(r'<meta property="og:image" content="[^"]*">',
               f'<meta property="og:image" content="{image_url}">\n'
               '<meta property="og:image:width" content="1200">\n'
               '<meta property="og:image:height" content="630">', s, count=1)
    s = s.replace('<meta name="twitter:card" content="summary">', '<meta name="twitter:card" content="summary_large_image">')
    if 'twitter:image' not in s:
        s = s.replace('<meta name="twitter:card" content="summary_large_image">',
                      f'<meta name="twitter:card" content="summary_large_image">\n<meta name="twitter:image" content="{image_url}">', 1)
    else:
        s = re.sub(r'<meta name="twitter:image" content="[^"]*">', f'<meta name="twitter:image" content="{image_url}">', s)
    page_path.write_text(s, encoding='utf-8')


def main():
    from playwright.sync_api import sync_playwright
    OUT.mkdir(parents=True, exist_ok=True)
    exe = os.environ.get('CHROMIUM') or ('/opt/pw-browsers/chromium' if os.path.exists('/opt/pw-browsers/chromium') else None)
    jobs = expressions()
    with sync_playwright() as p:
        b = p.chromium.launch(**({'executable_path': exe} if exe else {}))
        pg = b.new_page(viewport={'width': 1200, 'height': 630})
        for j in jobs:
            pg.goto((HERE / 'og.html').as_uri())
            pg.evaluate('j => draw(j)', j)
            pg.screenshot(path=str(OUT / f'{j["slug"]}.jpg'), type='jpeg', quality=88)
            point(ROOT / 'en' / j['slug'] / 'index.html', f'{SITE}/media/og/{j["slug"]}.jpg')
        b.close()
    # the phrase index shares the Hebrew homepage card
    point(ROOT / 'en' / 'index.html', f'{SITE}/media/og-he.png')
    print(f'{len(jobs)} share cards in {OUT}')


if __name__ == '__main__':
    main()
