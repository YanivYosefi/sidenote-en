# Sidenote

[![privacy](https://github.com/YanivYosefi/sidenote-en/actions/workflows/privacy.yml/badge.svg)](https://github.com/YanivYosefi/sidenote-en/actions/workflows/privacy.yml)
[![codeql](https://github.com/YanivYosefi/sidenote-en/actions/workflows/codeql.yml/badge.svg)](https://github.com/YanivYosefi/sidenote-en/actions/workflows/codeql.yml)

A Claude Code plugin that teaches you a language while you work. At the end of an answer, Claude adds one expression taken from that answer, and brings it back later so it sticks.

**Site:** https://yanivyosefi.github.io/sidenote-en/

## Install

```
claude plugin marketplace add YanivYosefi/sidenote-en
claude plugin install sidenote@sidenote
```

## What it does on your computer

The whole plugin is [`server/index.mjs`](server/index.mjs), about 500 lines. You can read it in a few minutes.

- **Imports only Node built-ins:** `node:fs`, `node:os`, `node:path`, `node:readline`, and `node:crypto` to check a supporter key's signature. No network module.
- **No dependencies.** There is no `package.json` and no `node_modules`.
- **Writes one file:** `~/.sidenote/state.json`, which holds your language, level and the expressions you have seen.
- **No account, no server, no telemetry.** It never contacts anything.
- **No hooks.** It doesn't run shell commands.

## Check it yourself

You don't have to take this README's word for it.

1. **Read the file.** [`server/index.mjs`](server/index.mjs), top to bottom.
2. **Run the same check CI runs.** It fails if the code imports anything else, mentions `fetch`, `http`, `net`, `child_process`, `eval` and the like, grows a dependency, or ships hooks:
   ```
   git clone https://github.com/YanivYosefi/sidenote-en && cd sidenote-en
   node .github/scripts/privacy-check.mjs
   ```
3. **Ask Claude.** Paste this into any Claude chat:
   > Read https://github.com/YanivYosefi/sidenote-en/blob/main/server/index.mjs and tell me whether it sends anything off my computer.

The [privacy workflow](.github/workflows/privacy.yml) runs that check on every change and weekly. [CodeQL](.github/workflows/codeql.yml), GitHub's security scanner, runs on every change to `main`. Both badges at the top are live.

## Uninstall

```
claude plugin uninstall sidenote
rm -rf ~/.sidenote
```

---

## בעברית

פלאגין ל-Claude Code שמלמד שפה תוך כדי עבודה. בסוף תשובה Claude מוסיף ביטוי אחד מתוך אותה תשובה, ומחזיר אותו מאוחר יותר כדי שיישאר.

**מה הוא עושה במחשב שלך:** כל הקוד הוא קובץ אחד, [`server/index.mjs`](server/index.mjs), כ-500 שורות. אין לו תלויות, הוא לא מתחבר לאינטרנט, והוא כותב רק לקובץ `~/.sidenote/state.json`. בדיקה אוטומטית מוודאת את זה בכל שינוי. התגיות למעלה מראות אם היא עוברת.

**לבדוק בעצמכם:** אפשר לקרוא את הקובץ, להריץ `node .github/scripts/privacy-check.mjs`, או לבקש מ-Claude:
> תקרא את https://github.com/YanivYosefi/sidenote-en/blob/main/server/index.mjs ותגיד לי אם הוא שולח משהו מהמחשב שלי החוצה.
