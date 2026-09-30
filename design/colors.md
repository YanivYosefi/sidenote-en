# Sidenote colors

Four colors on warm paper. Each color has one job, and a color never takes on another color's job.

The tokens live in the `:root` of every page (`index.html`, `home/*/index.html`, `en/*/index.html`, `404.html`), in `reels/template.html`, and in `reels/og.html`. When a value changes, change it everywhere. The names are the same across files.

## The four colors

| | Color | Job | Never |
|---|---|---|---|
| **Teal** `#00796F` | the brand | every action (buttons, links), every selected state, the logo, the Sidenote block | decoration for its own sake |
| **Clay** `#D97757` | Claude's orange | the Claude icon in the mockup, and the phrase being taught (as `--clay-d`) | a button, a large background, body text in its light shade |
| **Sun** `#F5B83D` | the highlight | step numbers, the highlighter under a word, the primary button on a dark section, a tag | text on a light background (use `--sun-d`) |
| **Paper and ink** | the base | backgrounds and text | pure gray, pure black, pure white as a page background |

## Proportions: 60 / 30 / 10

- **About 60%**: paper and ink. Most of the screen is light, warm background with dark text.
- **About 30%**: teal. Actions, the dark teal sections, the tints.
- **About 10%**: clay and sun together. Accents only. If clay or sun is everywhere, it stops being an accent.

## Tokens

### Paper and ink

The neutrals are warm and slightly yellow, never cool gray.

| Token | Value | Use |
|---|---|---|
| `--paper` | `#FFFCF7` | page background |
| `--sand` | `#F6EFE2` | alternate section, card header, table cell on a phone |
| `--sand-d` | `#EFE5D2` | hover on sand |
| `--line` | `#E9DFCC` | borders and dividers |
| `--card` | `#FFFFFF` | a raised card or input on top of paper. The only place pure white is allowed. |
| `--ink` | `#1F1E1D` | body text |
| `--ink-d` | `#141312` | headings, footer background, text on sun |
| `--muted` | `#6B6459` | secondary text |
| `--faint` | `#A39E93` | text on the footer only (dark background) |

### Teal

| Token | Value | Use |
|---|---|---|
| `--teal` | `#00796F` | button, link, selected state |
| `--teal-d` | `#005A53` | hover, small text on a tint |
| `--teal-dd` | `#003B37` | text on a tint that needs to be strong |
| `--teal-l` | `#2FA196` | decorative only, never text |
| `--teal-t` | `#DCEFEC` | tint: selected background, `code`, the product's column in the comparison table |
| `--teal-b` | `#A9D6D0` | border on a teal element; secondary text on deep |
| `--on-teal` | `#FFFCF7` | text on a teal button |

### Clay

| Token | Value | Use |
|---|---|---|
| `--clay` | `#D97757` | the Claude icon, the typing cursor. Graphics only. |
| `--clay-d` | `#A8451F` | text: the phrase being taught, the kicker above a heading |
| `--clay-t` | `#FBE3D9` | icon background in the rotation |

### Sun

| Token | Value | Use |
|---|---|---|
| `--sun` | `#F5B83D` | step numbers, button on a dark section, the "free" dot, the underline in reels |
| `--sun-d` | `#8A5A00` | text in sun's family (a tag, a string in code) |
| `--sun-t` | `#FDEFCB` | highlighter behind a word, tag background, icon background |

### Deep (dark teal sections)

| Token | Value | Use |
|---|---|---|
| `--deep` | `#003B37` | section background |
| `--deep-2` | `#002A27` | command box on deep |
| `--deep-card` | `#04322E` | card on deep |
| `--deep-line` | `#0B4641` | border on deep |
| `--deep-text` | `#FFF6E6` | heading and text |
| `--deep-sub` | `#E8DCC6` | secondary text |

### Night (the Claude app mockup)

The mockup uses Claude's own warm darks so it reads as Claude, not as a generic terminal.

| Token | Value | Use |
|---|---|---|
| `--night` | `#1F1E1D` | window |
| `--night-bar` | `#171615` | title bar |
| `--night-2` | `#2B2A28` | the user's message |
| `--night-line` | `#2A2927` | borders |
| `--night-edge` | `#121110` | outer edge |
| `--night-text` | `#EEEBE4` | strong text |
| `--night-body` | `#C7C3BA` | Claude's answer |
| `--night-muted` | `#A8A294` | secondary text |
| `--night-faint` | `#857F73` | the title bar's right side |
| `--note-line` / `--note-bg` / `--note-tag` / `--note-hi` | `#37413F` / teal 13% / `#5FC0B4` / `#7FD6C9` | the Sidenote block: teal, lit for a dark screen |

## Rules

1. **An action is teal.** Every button and link on a light background is teal. On a dark section, the primary button is sun with ink text, and the secondary button is an outline. There is never a second fill.
2. **Clay is Claude, and the phrase.** Clay is never a button, a large surface, or a warning.
3. **Sun is never text on light.** Use it as a fill or a highlight. Text in its family is `--sun-d`.
4. **Selected is teal.** A selected goal, the current language, the product's column in the table: teal tint with a teal border.
5. **At most three dark sections per page.** The homepage has exactly three: How it works, the check-it-yourself section, and the final call to action, plus the footer. A fourth would make the page heavy.
6. **Alternate the light sections** between `--paper` and `--sand`, so there is a boundary without a line.
7. **Icons rotate** teal, then clay, then sun (`nth-child(3n+1/3n+2/3n)`). Each icon has a tint background and a dark stroke.
8. **No pure gray, and no `#000`/`#fff` as a background.** Everything leans warm. Pure white is allowed only as `--card`.
9. **Shadows are tinted with ink** (`rgba(31,30,29,…)`), not black.
10. **Contrast before beauty.** Every pair below passes WCAG AA. Body text passes AAA.

## Contrast table

Measured with `design/contrast.py`. Minimum: 4.5 for normal text, 7 for body text, 3 for a large heading or a graphic.

| Text | Background | Ratio |
|---|---|---|
| ink `#1F1E1D` | paper | 16.3 |
| ink | sand | 14.6 |
| muted `#6B6459` | paper / sand / sand-d | 5.7 / 5.1 / 4.7 |
| teal `#00796F` | paper / sand | 5.2 / 4.6 |
| teal-d `#005A53` | sand / teal-t | 7.1 / 6.8 |
| paper | teal / teal-d | 5.2 / 7.9 |
| clay-d `#A8451F` | sand | 5.2 |
| sun-d `#8A5A00` | paper / sun-t | 5.8 / 5.2 |
| ink-d | sun | 10.4 |
| deep-text / deep-sub / teal-b | deep | 11.7 / 9.2 / 7.9 |
| night-body / night-muted | night | 9.5 / 6.6 |
| note-tag / note-hi | night | 7.7 / 9.8 |
| faint `#A39E93` | ink-d | 7.0 |

Pairs that fail and are not used: teal on teal-t (4.4, so use teal-d), and clay-d `#B4532F` on sand (4.35, which is why clay-d is `#A8451F`).
