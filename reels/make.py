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
import argparse, glob, hashlib, html, json, os, re, shutil, subprocess, sys
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
            type='expr', slug=Path(p).parent.name,
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
    return [dict(type='demo', slug=f'demo-{i + 1}', **d) for i, d in enumerate(xd)]


# ---------------------------------------------------------------- formats
# All built from the same thirty expressions, so a new phrase page feeds
# every format at once.

KINDS = {  # Hebrew category -> file-name key, top-3 title
    'צירוף מקצועי': ('meetings', 'ביטויים שתשמעו<br>בכל ישיבה באנגלית'),
    'סלנג מקצועי': ('tech', 'מילים שכל איש הייטק<br>אומר באנגלית'),
    'פועל מורכב': ('phrasal', 'פעלים מורכבים<br>שדוברי אנגלית אוהבים'),
    'ביטוי': ('idioms', 'ניבים באנגלית<br>שכדאי להכיר'),
    'הבחנה עדינה': ('pairs', 'זוגות מילים<br>שכולם מבלבלים'),
}


def seed(text):
    return int(hashlib.sha1(text.encode()).hexdigest(), 16)


def short(meaning):
    """The first sense only: an answer on a quiz card has to fit two lines."""
    return meaning.split(';')[0].strip()


def quizzes(exprs):
    out = []
    for e in exprs:
        if e['cat'] == 'הבחנה עדינה':
            continue  # "a = x; b = y" makes a poor multiple-choice answer
        others = sorted((o for o in exprs if o['cat'] == e['cat'] and o['slug'] != e['slug']),
                        key=lambda o: seed(e['slug'] + o['slug']))[:2]
        opts = [short(o['meaning']) for o in others]
        answer = seed(e['slug']) % 3
        opts.insert(answer, short(e['meaning']))
        out.append(dict(e, type='quiz', slug=f'quiz-{e["slug"]}', options=opts, answer=answer))
    return out


def top3s(exprs):
    out = []
    for cat, (key, title) in KINDS.items():
        group = [e for e in exprs if e['cat'] == cat]
        for n in range(0, len(group) - 2, 3):
            items = [dict(expr=e['expr'], meaning=e['meaning'], example=e['example']) for e in group[n:n + 3]]
            out.append(dict(type='top3', slug=f'top3-{key}-{n // 3 + 1}', cat=cat, title=title, items=items))
    return out


def versus(exprs):
    out = []
    for e in exprs:
        if e['cat'] != 'הבחנה עדינה':
            continue
        sides = dict(part.split('=', 1) for part in e['meaning'].split(';'))
        sides = {k.strip(): v.strip() for k, v in sides.items()}
        order = [w.strip() for w in re.split(r'\s+vs\.?\s+', e['expr'])]
        pair = [dict(w=w, m=sides.get(w, '')) for w in order]
        out.append(dict(e, type='vs', slug=f'vs-{e["slug"]}', pair=pair))
    return out


def english_demos():
    """The English homepage's walk-throughs: an English speaker, other targets."""
    s = open(ROOT / 'home' / 'en' / 'index.html', encoding='utf-8').read()
    xd = json.loads(re.search(r'var XD = (\[.*?\]);\n', s, re.S).group(1))
    return [dict(type='demo', ui='en', slug=f'demo-en-{i + 1}', **d) for i, d in enumerate(xd)]


def samples():
    """One reel of every format, for every audience — to choose a structure
    before rendering any volume."""
    ex = expressions()
    en = json.load(open(HERE / 'content-en.json', encoding='utf-8'))
    fo, he = en['foreign'], en['hebrew']
    pick = lambda jobs, slug: next(j for j in jobs if j['slug'] == slug)
    q = fo[0]
    others = [f['meaning'].split(' — ')[0] for f in fo[1:3]]
    opts = others[:]; opts.insert(1, q['meaning'].split(' — ')[0])
    return [
        # Hebrew speakers learning English (the site's phrase pages)
        dict(pick(ex, 'ship-it'), slug='he-1-expression'),
        dict(pick(demos(), 'demo-3'), slug='he-2-demo'),
        dict(pick(quizzes(ex), 'quiz-bikeshedding'), slug='he-3-quiz'),
        dict(pick(top3s(ex), 'top3-meetings-1'), slug='he-4-top3'),
        dict(pick(versus(ex), 'vs-imply-vs-infer'), slug='he-5-versus'),
        dict(type='pov', ui='he', slug='he-6-pov', lines=[
            dict(t='POV:', cls='k'), dict(t='אתם מדברים עם Claude'), dict(t='6 שעות ביום'),
            dict(t='…והוא מלמד אתכם'), dict(t='אנגלית בלי שהרגשתם', cls='g')],
            card=dict(expr='to take the brunt of it', gloss='לספוג את עיקר העומס — החלק שחוטף הכי חזק.'), cat=''),
        # English speakers learning another language
        dict(english_demos()[0], slug='en-1-demo'),
        dict(type='quiz', ui='en', slug='en-2-quiz', cat=q['lang'], expr=q['expr'], example=q['example'],
             options=opts, answer=1),
        dict(type='lit', ui='en', slug='en-3-literally', cat='', lang=q['lang'], hook="Italians say it<br>before every exam", **{k: q[k] for k in ('expr', 'lit', 'meaning', 'example', 'example_en')}),
        dict(type='pov', ui='en', slug='en-4-pov', cat='', lines=[
            dict(t='POV:', cls='k'), dict(t='you talk to Claude'), dict(t='6 hours a day'),
            dict(t='…and it’s secretly'), dict(t='teaching you Spanish', cls='g')],
            card=dict(expr=fo[1]['expr'], gloss=fo[1]['meaning'] + '.')),
        # English speakers learning Hebrew
        dict(type='lit', ui='en', slug='hebrew-1-literally', cat='slang', lang='Hebrew',
             hook="Hebrew you won’t find<br>in a textbook", **{k: he[0][k] for k in ('expr', 'tr', 'lit', 'meaning', 'example', 'example_en')}),
        dict(type='pov', ui='en', slug='hebrew-2-pov', cat='', lines=[
            dict(t='POV:', cls='k'), dict(t='you moved to Tel Aviv'), dict(t='and everyone says'),
            dict(t='חבל על הזמן', cls='g'), dict(t='about everything')],
            card=dict(expr=he[0]['expr'], gloss=he[0]['meaning'])),
    ]


def caption(job):
    tags = '#אנגלית #לימודאנגלית #ביטוייםבאנגלית #Claude #AI #Sidenote'
    end = 'Sidenote מלמד ביטוי אחד בכל שיחה עם Claude, מתוך התשובה שקיבלת. חינם, קוד פתוח. הקישור בפרופיל.'
    t = job['type']
    if job.get('ui') == 'en':
        tags_en = '#learnlanguages #languagelearning #Claude #AI #Sidenote'
        end_en = 'Sidenote teaches you one expression in every Claude chat, taken from the answer you got. Free and open source. Link in bio.'
        if t == 'quiz':
            abc = '\n'.join(f'{l}. {o}' for l, o in zip('ABC', job['options']))
            return f'What does "{job["expr"]}" mean?\n\n{abc}\n\nComment A, B or C before the video answers 👇\n\n{end_en}\n\n{tags_en}'
        if t == 'lit':
            return f'{job["expr"]}. Literally: "{job["lit"]}". Actually: {job["meaning"]}.\n\n{job["example"]}\n{job["example_en"]}\n\n{end_en}\n\n{tags_en}'
        return f'You are in Claude for hours anyway. So after every answer, one expression from it.\n\n{end_en}\n\n{tags_en}'
    if t == 'pov':
        return 'אתם ממילא מדברים עם Claude שעות. אז שילמד אתכם בדרך.\n\n' + end + '\n\n' + tags
    if t == 'demo':
        return ('אתם ממילא פה שעות כל יום. אז בסוף כל תשובה של Claude, ביטוי אחד מתוכה.\n\n'
                'Sidenote. חינם, קוד פתוח, בלי חשבון. הקישור בפרופיל.\n\n' + tags)
    if t == 'quiz':
        abc = '\n'.join(f'{l}. {o}' for l, o in zip('אבג', job['options']))
        return (f'מה זה אומר: {job["expr"]}?\n\n{abc}\n\n'
                'כתבו בתגובות א, ב או ג לפני שהסרטון עונה 👇\n\n' + end + '\n\n' + tags)
    if t == 'top3':
        title = job['title'].replace('<br>', ' ')
        items = '\n'.join(f'{i + 1}. {it["expr"]}: {it["meaning"]}' for i, it in enumerate(job['items']))
        return f'3 {title}\n\n{items}\n\nשמרו לפעם הבאה 🔖\n\n{end}\n\n{tags}'
    if t == 'vs':
        a, b = job['pair']
        return (f'{a["w"]} או {b["w"]}?\n\n{a["w"]} = {a["m"]}\n{b["w"]} = {b["m"]}\n\n'
                f'דוגמה: {job["example"]}\n\n{end}\n\n{tags}')
    return (f'{job["expr"]}: {job["meaning"]}\n\n'
            f'דוגמה: {job["example"]}\n\n' + end + '\n\n' + tags)


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
    payload = dict(job, kind=job.get('cat', ''))
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
    cover_at = int({'expr': 2.6, 'demo': 3.9, 'quiz': 2.9, 'top3': 1.2, 'vs': 4.2, 'lit': 3.2, 'pov': 4.4}[job['type']] * FPS)
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
    ap.add_argument('--only', choices=['expr', 'demo', 'quiz', 'top3', 'vs'])
    ap.add_argument('--id')
    ap.add_argument('--limit', type=int)
    ap.add_argument('--music')
    ap.add_argument('--samples', action='store_true', help='one reel of every format, for every audience')
    ap.add_argument('--out', default=str(HERE / 'out'))
    a = ap.parse_args()

    ex = expressions()
    jobs = samples() if a.samples else ex + demos() + quizzes(ex) + top3s(ex) + versus(ex)
    if a.only:
        jobs = [j for j in jobs if j['type'] == a.only]
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
