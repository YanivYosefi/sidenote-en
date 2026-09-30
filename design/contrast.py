#!/usr/bin/env python3
"""
Check every text/background pair the palette uses against WCAG.

    python design/contrast.py

Exits non-zero if any pair is under its minimum. Add a pair here whenever a
new text color meets a new background (see design/colors.md).
"""
import sys

PAIRS = [  # text, background, minimum
    ('#1F1E1D', '#FFFCF7', 7), ('#1F1E1D', '#F6EFE2', 7),
    ('#6B6459', '#FFFCF7', 4.5), ('#6B6459', '#F6EFE2', 4.5), ('#6B6459', '#EFE5D2', 4.5),
    ('#00796F', '#FFFCF7', 4.5), ('#00796F', '#F6EFE2', 4.5),
    ('#005A53', '#F6EFE2', 4.5), ('#005A53', '#DCEFEC', 4.5), ('#003B37', '#DCEFEC', 7),
    ('#FFFCF7', '#00796F', 4.5), ('#FFFCF7', '#005A53', 4.5),
    ('#A8451F', '#FFFCF7', 4.5), ('#A8451F', '#F6EFE2', 4.5),
    ('#8A5A00', '#FFFCF7', 4.5), ('#8A5A00', '#FDEFCB', 4.5),
    ('#141312', '#F5B83D', 4.5),
    ('#FFF6E6', '#003B37', 7), ('#E8DCC6', '#003B37', 4.5), ('#A9D6D0', '#003B37', 4.5),
    ('#F5B83D', '#04322E', 4.5), ('#E8DCC6', '#04322E', 4.5),
    ('#EEEBE4', '#2B2A28', 7), ('#C7C3BA', '#1F1E1D', 7), ('#A8A294', '#1F1E1D', 4.5),
    ('#857F73', '#171615', 4.5), ('#5FC0B4', '#1F1E1D', 4.5), ('#7FD6C9', '#1F1E1D', 4.5),
    ('#A39E93', '#141312', 4.5), ('#C7C3BA', '#141312', 4.5),
]


def lum(h):
    r, g, b = (int(h[i:i + 2], 16) / 255 for i in (1, 3, 5))
    f = lambda c: c / 12.92 if c <= .03928 else ((c + .055) / 1.055) ** 2.4
    return .2126 * f(r) + .7152 * f(g) + .0722 * f(b)


def ratio(a, b):
    x, y = sorted((lum(a), lum(b)), reverse=True)
    return (x + .05) / (y + .05)


bad = 0
for t, bg, need in PAIRS:
    r = ratio(t, bg)
    ok = r >= need
    bad += not ok
    print(f'{t} on {bg}  {r:5.2f}  {"ok" if ok else "FAIL"} (min {need})')
sys.exit(1 if bad else 0)
