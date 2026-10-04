# Sidenote

[![privacy](https://github.com/YanivYosefi/sidenote-en/actions/workflows/privacy.yml/badge.svg)](https://github.com/YanivYosefi/sidenote-en/actions/workflows/privacy.yml)
[![codeql](https://github.com/YanivYosefi/sidenote-en/actions/workflows/codeql.yml/badge.svg)](https://github.com/YanivYosefi/sidenote-en/actions/workflows/codeql.yml)

A Claude Code plugin that teaches you a language while you work. At the end of an answer, Claude adds one expression taken from that answer, and brings it back later so it sticks.

**Site:** https://yanivyosefi.github.io/sidenote-en/

## Install

Requires Claude Code and **Node.js 18 or later**, available as `node` on your PATH.

```
claude plugin marketplace add YanivYosefi/sidenote-en
claude plugin install sidenote@sidenote
```

After installing, open a new Claude Code conversation and run `/sidenote:sidenote` to choose your language and level.

## What it does on your computer

The whole plugin is [`server/index.mjs`](server/index.mjs), about 500 lines. You can read it in a few minutes.

- **Imports only Node built-ins:** `node:fs`, `node:os`, `node:path`, `node:readline`. No network module.
- **No dependencies.** There is no `package.json` and no `node_modules`.
- **Writes one file:** `~/.sidenote/state.json`, which holds your language, level and the expressions you have seen.
- **No Sidenote account, external server or telemetry.** The local server makes no network requests.
- **Claude sees the tool results.** Your profile and vocabulary retrieved for practice enter the Claude conversation and follow your Claude privacy settings.
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

## The website is a separate thing

Everything above is about the plugin. The landing page is a static site on GitHub Pages, and a plain counter ([Abacus](https://abacus.jasoncameron.dev)) adds one each time a page opens or the install command is copied: a number only, and no cookie. The plugin stores progress locally; its tool results are shared with Claude in your conversation.

## Learning while you chat

After each answer with a natural anchor, Claude teaches one new expression. When an older expression is due, Claude adds a brief “you have seen this before” reminder and still teaches a different new expression. No quizzes or requests to practise. Showing a reminder advances its 1–3–7–16–35–90 day schedule; spontaneous use is tracked separately. Switching languages keeps each language’s vocabulary separate. Teaching depends on Claude following the plugin instructions.

## License

[MIT](LICENSE).

---

## בעברית

פלאגין ל-Claude Code שמלמד שפה תוך כדי עבודה. בסוף תשובה Claude מוסיף ביטוי אחד מתוך אותה תשובה, ומחזיר אותו מאוחר יותר כדי שיישאר.

**מה הוא עושה במחשב שלך:** כל הקוד הוא קובץ אחד, [`server/index.mjs`](server/index.mjs), כ-500 שורות. אין לו תלויות, הוא לא מתחבר לאינטרנט, והוא כותב רק לקובץ `~/.sidenote/state.json`. בדיקה אוטומטית מוודאת את זה בכל שינוי. התגיות למעלה מראות אם היא עוברת.

**דרישות:** Claude Code ו-Node.js 18 ומעלה. אחרי ההתקנה פותחים שיחה חדשה ומקלידים `/sidenote:sidenote`.

**לבדוק בעצמכם:** אפשר לקרוא את הקובץ, להריץ `node .github/scripts/privacy-check.mjs`, או לבקש מ-Claude:
> תקרא את https://github.com/YanivYosefi/sidenote-en/blob/main/server/index.mjs ותגיד לי אם הוא שולח משהו מהמחשב שלי החוצה.

**האתר הוא דבר נפרד:** דף סטטי ב-GitHub Pages, ומונה פשוט סופר בו כמה פעמים הדף נפתח וכמה פעמים הועתקה פקודת ההתקנה: מספר בלבד, בלי קוקיז. ההתקדמות נשמרת מקומית. הפרופיל והביטויים שנשלפים לתרגול מועברים ל-Claude כחלק מהשיחה, בהתאם להגדרות הפרטיות שלכם ב-Claude.

**רישיון:** [MIT](LICENSE).
