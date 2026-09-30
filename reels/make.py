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
            dict(t='POV:', cls='k'), dict(t='אתם מדברים עם Claude'), dict(t='6 שעות ביום…'),
            dict(t='והוא מלמד אתכם'), dict(t='אנגלית בלי שהרגשתם', cls='g')],
            card=dict(expr='to take the brunt of it', gloss='לספוג את עיקר העומס — החלק שחוטף הכי חזק.'), cat=''),
        dict(type='screen', mode='cli', ui='he', slug='he-7-screen-code', cat='', cwd='~/shop',
             prompt="הטסט של הצ'קאאוט נופל רק לפעמים. תבדוק למה?",
             tools=[['Read(tests/checkout.test.ts)', 'Read 84 lines'], ['Bash(npm test -- checkout)', '2 passed · 1 failed']],
             answer='מצאתי. הטסט תלוי בשעון האמיתי, אז סביב חצות התאריך מתחלף באמצע הריצה.\nהוספתי mock ל-Date, ועכשיו הוא עובר 50 פעמים ברצף.',
             note=dict(src='מתוך התשובה: “מצאתי.”', expr='to pin it down', gloss='לאתר בדיוק את מקור הבעיה.',
                       ex='It took an hour to pin down the flaky test.'),
             hook1='אתם ממילא עם Claude<br>כל היום', hook2='ובסוף כל תשובה,<br>ביטוי אחד באנגלית',
             close='אז למה שלא יצא לכם<br>מזה <em>שפה חדשה</em>?'),
        dict(type='screen', mode='app', ui='he', slug='he-8-screen-chat', cat='', cwd='',
             side=['מייל לבעל הבית', 'מתכון לשבת', 'טיול לרומא'],
             prompt='תעזור לי לכתוב לבעל הבית שהדוד לא עובד כבר שבוע',
             tools=[],
             answer='בטח. קצר ועניני, עם תאריך:\n„הדוד לא עובד מאז ה-3 בחודש. אשמח לתיקון עד יום שישי.”\nאם לא יענה עד שישי, תכתוב לו שוב.',
             note=dict(src='מתוך התשובה: “אם לא יענה עד שישי, תכתוב לו שוב.”', expr='to follow up',
                       gloss='לפנות שוב כשלא קיבלת תשובה.', ex="If he doesn't reply by Friday, follow up."),
             hook1='לא רק קוד.<br>כל שיחה עם Claude', hook2='נגמרת בביטוי אחד<br>באנגלית',
             close='אז למה שלא יצא לכם<br>מזה <em>שפה חדשה</em>?'),
        # English speakers learning another language
        dict(type='screen', mode='cli', ui='en', slug='en-0-screen-code', cat='', cwd='~/shop',
             prompt='The checkout test fails only sometimes. Can you find out why?',
             tools=[['Read(tests/checkout.test.ts)', 'Read 84 lines'], ['Bash(npm test -- checkout)', '2 passed · 1 failed']],
             answer='Found it. The test depends on the real clock, so around midnight the date flips mid-run.\nI mocked Date, and it now passes 50 times in a row.',
             note=dict(src='From the answer: “Found it.”', expr='dar con algo', gloss='to finally track something down.',
                       ex='Por fin di con el error.'),
             hook1="You're in Claude<br>all day anyway", hook2='…so every answer<br>teaches you Spanish',
             close='Why not get a new<br>language <em>out of it</em>?'),
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


def library():
    """Everything, filed by audience and format: the folder an editor works from.
    Each job carries 'dir' = <audience>/<format>."""
    ex = expressions()
    en = json.load(open(HERE / 'content-en.json', encoding='utf-8'))
    fo, he = en['foreign'], en['hebrew']
    S = {j['slug']: j for j in samples()}
    jobs = []
    add = lambda d, js: jobs.extend(dict(j, dir=d) for j in js)
    # Hebrew speakers learning English
    add('he-learning-english/expression', ex)
    add('he-learning-english/quiz', quizzes(ex)[::2])
    add('he-learning-english/top3', top3s(ex))
    add('he-learning-english/versus', versus(ex))
    add('he-learning-english/demo', demos())
    add('he-learning-english/pov', [S['he-6-pov']])
    add('he-learning-english/screen', [S['he-7-screen-code'], S['he-8-screen-chat']])
    # English speakers learning another language
    add('en-learning-languages/screen', [S['en-0-screen-code']])
    add('en-learning-languages/demo', [dict(d, slug=d['slug']) for d in english_demos()[:3]])
    quiz_en = []
    for i, q in enumerate(fo):
        others = [f['meaning'].split(' — ')[0] for f in fo if f is not q][:2]
        ans = i % 3
        opts = others[:]; opts.insert(ans, q['meaning'].split(' — ')[0])
        quiz_en.append(dict(type='quiz', ui='en', slug=f'quiz-{q["slug"]}', cat=q['lang'], expr=q['expr'],
                            example=q['example'], options=opts, answer=ans))
    add('en-learning-languages/quiz', quiz_en)
    hooks = {'Italian': 'Italians say it<br>before every exam', 'Spanish': 'Spanish you won’t<br>learn in class',
             'French': 'The French word<br>for Sunday mood'}
    add('en-learning-languages/literally', [dict(type='lit', ui='en', slug=f'lit-{q["slug"]}', cat='', lang=q['lang'],
        hook=hooks.get(q['lang'], 'Say it like a local'), **{k: q[k] for k in ('expr', 'lit', 'meaning', 'example', 'example_en')}) for q in fo])
    add('en-learning-languages/pov', [S['en-4-pov']])
    # English speakers learning Hebrew
    add('learning-hebrew/literally', [dict(type='lit', ui='en', slug=f'lit-{h["slug"]}', cat='slang', lang='Hebrew',
        hook='Hebrew you won’t find<br>in a textbook', **{k: h[k] for k in ('expr', 'tr', 'lit', 'meaning', 'example', 'example_en')}) for h in he])
    add('learning-hebrew/pov', [S['hebrew-2-pov']])
    return jobs


def _render_chunk(args):
    chunk, out, music = args
    from playwright.sync_api import sync_playwright
    exe = os.environ.get('CHROMIUM') or ('/opt/pw-browsers/chromium' if os.path.exists('/opt/pw-browsers/chromium') else None)
    done = []
    with sync_playwright() as p:
        b = p.chromium.launch(**({'executable_path': exe} if exe else {}))
        page = b.new_page(viewport={'width': 1080, 'height': 1920}, device_scale_factor=1)
        for j in chunk:
            dest = Path(out) / j.get('dir', '') / j['slug']
            render(page, j, dest, music)
            print(f'  done {j.get("dir", "")}/{j["slug"]}', flush=True)
            done.append(j)
        b.close()
    return done


# ---------------------------------------------------------------- stock footage
# Clips are named by what they show; fetch_broll.py downloads each from Pexels
# (portrait, by the query below) into reels/broll/<name>.mp4. A clip that is
# not there yet renders as a moving colour field, so every reel can be laid
# out and timed before any footage exists.
BROLL_DIR = HERE / 'broll'
BROLL = {
    'street-question': 'woman asking question street interview',
    'typing-night': 'person typing laptop night',
    'coffee-desk': 'coffee cup desk morning laptop',
    'desk-morning': 'working at desk morning light',
    'screen-closeup': 'laptop screen code closeup',
    'city-evening': 'city street evening walking',
    'shrug': 'man shrugging smiling',
}
FIELD = {  # fallback colour pairs, one per clip, so cuts are still visible
    'street-question': ('0x2B4C7E', '0x0E1F33'), 'typing-night': ('0x1B1F3A', '0x3A2B55'),
    'coffee-desk': ('0x6B4A2F', '0x2A1B12'), 'desk-morning': ('0xC9A26B', '0x5C4326'),
    'screen-closeup': ('0x0A6B63', '0x04413D'), 'city-evening': ('0x5A2E4F', '0x1D1330'),
    'shrug': ('0x3E5C3A', '0x1A2A19'),
}


def broll_jobs():
    """Trend formats over stock footage, in Hebrew and English."""
    def where(ui, q1, a1, q2, a2, card, slug):
        return dict(type='broll', ui=ui, slug=slug, cat='', dur=12.6, outro=10.2,
                    scenes=[('street-question', 4.2), ('typing-night', 4.0), ('coffee-desk', 4.4)],
                    items=[dict(kind='them', text=q1, t0=.4, t1=10.2), dict(kind='me', text=a1, t0=1.6, t1=10.2),
                           dict(kind='them', text=q2, t0=2.8, t1=10.2), dict(kind='me', text=a2, t0=4.0, t1=10.2),
                           dict(kind='card', t0=5.6, t1=10.2, top=1180, **card)])
    def learned(ui, title, items, slug):
        return dict(type='broll', ui=ui, slug=slug, cat='', dur=13, outro=10.6,
                    scenes=[('desk-morning', 13)],
                    items=[dict(kind='meme', text=title, t0=.2, t1=10.6)] +
                          [dict(kind='li', expr=e, gloss=g, t0=1.6 + i * 1.5, t1=10.6) for i, (e, g) in enumerate(items)])
    def day(ui, beats, card, slug):
        items, scenes = [], []
        for i, (clip, time, text) in enumerate(beats):
            a = i * 2.3
            scenes.append((clip, 2.3))
            items += [dict(kind='label', text=time, t0=a + .1, t1=a + 2.3), dict(kind='meme', text=text, t0=a + .25, t1=a + 2.3, top=410)]
        items.append(dict(kind='card', t0=2 * 2.3 + .5, t1=3 * 2.3, top=1150, **card))
        n = len(beats) * 2.3
        scenes.append((beats[-1][0], 13 - n))
        return dict(type='broll', ui=ui, slug=slug, cat='', dur=13, outro=n + .3, scenes=scenes, items=items)
    def nobody(ui, top, reply, card, slug):
        return dict(type='broll', ui=ui, slug=slug, cat='', dur=10.5, outro=8.2, chatTop=720,
                    scenes=[('typing-night', 5), ('screen-closeup', 5.5)],
                    items=[dict(kind='meme', text=top, t0=.2, t1=8.2),
                           dict(kind='claude', text=reply, t0=2.6, t1=8.2),
                           dict(kind='card', t0=4.2, t1=8.2, top=1180, **card)])
    pin = dict(expr='to pin it down', gloss='לאתר בדיוק את מקור הבעיה', ex='It took an hour to pin down the flaky test.')
    dar = dict(expr='dar con algo', gloss='to finally track something down', ex='Por fin di con el error.')
    return [
        where('he', 'איפה למדת אנגלית ככה?', 'מ-Claude.', 'מה? זה צ׳אט לקוד', 'בדיוק. בסוף כל תשובה הוא זורק לי ביטוי אחד', pin, 'broll-where-he'),
        where('en', 'wait, where did you learn Spanish??', 'Claude.', 'the coding thing??', 'yep. one expression at the end of every answer', dar, 'broll-where-en'),
        learned('en', 'Things Claude taught me\nthis week without me asking', [
            ('to pin it down', 'to find the exact cause'), ('to get it out of the way', 'to do the annoying thing first'),
            ('to take the brunt of it', 'to take the hardest hit'), ('to follow up', 'to write again when nobody answers')], 'broll-learned-en'),
        learned('he', 'דברים ש-Claude לימד אותי\nהשבוע בלי שביקשתי', [
            ('to pin it down', 'לאתר בדיוק את מקור הבעיה'), ('to get it out of the way', 'לסגור את המעיק קודם'),
            ('to take the brunt of it', 'לספוג את עיקר המכה'), ('to follow up', 'לכתוב שוב כשלא ענו')], 'broll-learned-he'),
        day('en', [('coffee-desk', '9:00', 'coffee'), ('typing-night', '9:15', 'ask Claude why the test is flaky'),
                   ('screen-closeup', '9:16', 'accidentally learn Spanish'), ('city-evening', '18:00', "still haven't opened Duolingo")],
            dar, 'broll-day-en'),
        day('he', [('coffee-desk', '9:00', 'קפה'), ('typing-night', '9:15', 'שואל את Claude למה הטסט נופל'),
                   ('screen-closeup', '9:16', 'לומד אנגלית בלי לשים לב'), ('city-evening', '18:00', 'עדיין לא פתחתי דואולינגו')],
            pin, 'broll-day-he'),
        nobody('en', 'Nobody:\n\nClaude, after fixing my bug:', 'Done, tests pass. <b>Also</b> — in Spanish you’d say…', dar, 'broll-nobody-en'),
        nobody('he', 'אף אחד:\n\nClaude, אחרי שתיקן לי באג:', 'תוקן, הטסטים עוברים. <b>ודרך אגב</b>, באנגלית אומרים…', pin, 'broll-nobody-he'),
    ]


def background(job, out_mp4):
    """The picture under the text: the named clips cut to length, or colour."""
    ins, parts = [], []
    for i, (clip, dur) in enumerate(job['scenes']):
        f = BROLL_DIR / f'{clip}.mp4'
        if f.exists():
            ins += ['-stream_loop', '-1', '-t', f'{dur}', '-i', str(f)]
            parts.append(f'[{i}:v]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,setsar=1,fps={FPS},'
                         f'eq=brightness=-0.04:saturation=1.05,trim=0:{dur},setpts=PTS-STARTPTS[s{i}]')
        else:
            c0, c1 = FIELD.get(clip, ('0x0A6B63', '0x04413D'))
            ins += ['-f', 'lavfi', '-t', f'{dur}', '-i', f'gradients=s=1080x1920:c0={c0}ff:c1={c1}ff:speed=0.012:r={FPS}']
            parts.append(f'[{i}:v]setsar=1,trim=0:{dur},setpts=PTS-STARTPTS[s{i}]')
    n = len(job['scenes'])
    graph = ';'.join(parts) + ';' + ''.join(f'[s{i}]' for i in range(n)) + f'concat=n={n}:v=1:a=0[v]'
    subprocess.run([ffmpeg(), '-y', '-loglevel', 'error', *ins, '-filter_complex', graph, '-map', '[v]',
                    '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '16', '-pix_fmt', 'yuv420p', str(out_mp4)], check=True)


def render_broll(page, job, dest, music=None):
    dest.mkdir(parents=True, exist_ok=True)
    bg = dest / '_bg.mp4'
    background(job, bg)
    page.goto((HERE / 'template.html').as_uri())
    dur = page.evaluate('j => setup(j)', dict(job, kind=''))
    frames = int(dur * FPS)
    cmd = [ffmpeg(), '-y', '-loglevel', 'error', '-i', str(bg), '-f', 'image2pipe', '-framerate', str(FPS), '-c:v', 'png', '-i', '-']
    if music:
        cmd += ['-i', str(music), '-filter_complex',
                f'[0:v][1:v]overlay=format=auto,format=yuv420p[v];[2:a]atrim=0:{dur},afade=t=in:d=0.6,afade=t=out:st={dur - 1.2}:d=1.2[a]',
                '-map', '[v]', '-map', '[a]']
    else:
        cmd += ['-f', 'lavfi', '-i', 'anullsrc=r=44100:cl=stereo', '-filter_complex',
                '[0:v][1:v]overlay=format=auto,format=yuv420p[v]', '-map', '[v]', '-map', '2:a']
    cmd += ['-c:v', 'libx264', '-preset', 'slow', '-crf', '19', '-r', str(FPS), '-c:a', 'aac', '-b:a', '128k',
            '-t', f'{dur}', '-movflags', '+faststart', str(dest / 'reel.mp4')]
    enc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    cover_at = int(job.get('cover', job['outro'] - 1.5) * FPS)
    for f in range(frames):
        page.evaluate('t => render(t)', f / FPS)
        shot = page.screenshot(type='png', omit_background=True)
        enc.stdin.write(shot)
        if f == cover_at:
            (dest / '_cover.png').write_bytes(shot)
    enc.stdin.close()
    if enc.wait():
        sys.exit(f'ffmpeg failed on {job["slug"]}')
    # the cover is the finished picture at that moment, footage included
    subprocess.run([ffmpeg(), '-y', '-loglevel', 'error', '-ss', f'{cover_at / FPS}', '-i', str(dest / 'reel.mp4'),
                    '-frames:v', '1', '-q:v', '3', str(dest / 'cover.jpg')], check=True)
    (dest / '_cover.png').unlink(missing_ok=True)
    bg.unlink(missing_ok=True)
    have = [c for c, _ in job['scenes'] if (BROLL_DIR / f'{c}.mp4').exists()]
    credits = ''
    cf = BROLL_DIR / 'credits.json'
    if have and cf.exists():
        cr = json.load(open(cf, encoding='utf-8'))
        credits = '\n\nFootage: ' + ', '.join(sorted({cr[c] for c in have if c in cr})) + ' (Pexels)'
    (dest / 'caption.txt').write_text(caption(job) + credits, encoding='utf-8')


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
        if t == 'broll':
            return f'You are in Claude all day anyway. Might as well pick up a language.\n\n{end_en}\n\n{tags_en}'
        if t == 'screen':
            return f'You are in Claude all day anyway. Why not get a new language out of it?\n\nToday: {job["note"]["expr"]}, {job["note"]["gloss"]}\n\n{end_en}\n\n{tags_en}'
        if t == 'lit':
            return f'{job["expr"]}. Literally: "{job["lit"]}". Actually: {job["meaning"]}.\n\n{job["example"]}\n{job["example_en"]}\n\n{end_en}\n\n{tags_en}'
        return f'You are in Claude for hours anyway. So after every answer, one expression from it.\n\n{end_en}\n\n{tags_en}'
    if t == 'broll':
        return 'אתם ממילא עם Claude כל היום. אז שייצא לכם מזה גם שפה.\n\n' + end + '\n\n' + tags
    if t == 'screen':
        return ('אתם ממילא עם Claude כל היום. אז למה שלא יצא לכם מזה שפה חדשה?\n\n'
                f'היום: {job["note"]["expr"]}, {job["note"]["gloss"]}\n\n' + end + '\n\n' + tags)
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
    if job.get('type') == 'broll':
        return render_broll(page, job, dest, music)
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
    cover_at = int({'expr': 2.6, 'demo': 3.9, 'quiz': 2.9, 'top3': 1.2, 'vs': 4.2, 'lit': 3.2, 'pov': 4.4, 'screen': 7.5}[job['type']] * FPS)
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
    ap.add_argument('--library', action='store_true', help='everything, filed by audience and format')
    ap.add_argument('--broll', action='store_true', help='the stock-footage trend formats')
    ap.add_argument('--workers', type=int, default=1, help='render in parallel, one browser each')
    ap.add_argument('--out', default=str(HERE / 'out'))
    a = ap.parse_args()

    ex = expressions()
    jobs = broll_jobs() if a.broll else library() if a.library else samples() if a.samples else ex + demos() + quizzes(ex) + top3s(ex) + versus(ex)
    if a.only:
        jobs = [j for j in jobs if j['type'] == a.only]
    if a.id:
        jobs = [j for j in jobs if j['slug'] == a.id]
    if a.limit:
        jobs = jobs[:a.limit]
    if not jobs:
        sys.exit('nothing to render')

    if a.workers > 1:
        from concurrent.futures import ProcessPoolExecutor
        chunks = [jobs[i::a.workers] for i in range(a.workers)]
        with ProcessPoolExecutor(a.workers) as pool:
            list(pool.map(_render_chunk, [(c, a.out, a.music) for c in chunks if c]))
    else:
        for i, j in enumerate(jobs, 1):
            print(f'[{i}/{len(jobs)}] {j["slug"]}', flush=True)
        _render_chunk((jobs, a.out, a.music))
    print(f'done: {len(jobs)} reel(s) in {a.out}')


if __name__ == '__main__':
    main()
