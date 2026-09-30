/*
 * What this counts, and what it does not.
 *
 * `claude plugin marketplace add YanivYosefi/sidenote-en` is a git clone.
 * There is no install callback anywhere in Sidenote and there is not going
 * to be one — the landing page promises nothing leaves your machine, and a
 * counter is not worth breaking that over. So the only honest signal is the
 * clone count GitHub already collects on its own.
 *
 * That signal is a proxy, not a number of people. CI runners, mirrors and
 * scrapers clone too, one person on two machines counts twice, and a clone
 * says nothing about whether the plugin was ever run. `uniques` is the
 * closest of the two to a human, so that is what the site shows.
 *
 * GitHub keeps only the last 14 days. This runs daily and merges each pull
 * into a CSV that is committed back, so the history survives past the
 * window. Days are keyed by date and overwritten on each run, because the
 * most recent day is still incrementing when we read it.
 */
import { readFileSync, writeFileSync, existsSync, mkdirSync } from 'node:fs';

const REPO = process.env.GITHUB_REPOSITORY;
const TOKEN = process.env.TRAFFIC_TOKEN;
const CSV = 'data/installs.csv';
const JSON_OUT = 'data/installs.json';

if (!TOKEN) {
  console.error('TRAFFIC_TOKEN is not set. The traffic API needs a PAT with');
  console.error('Administration: read — the default GITHUB_TOKEN cannot read it.');
  process.exit(1);
}

const res = await fetch(`https://api.github.com/repos/${REPO}/traffic/clones?per=day`, {
  headers: {
    authorization: `Bearer ${TOKEN}`,
    accept: 'application/vnd.github+json',
    'x-github-api-version': '2022-11-28',
    'user-agent': 'sidenote-installs',
  },
});

if (!res.ok) {
  console.error(`traffic API ${res.status}: ${await res.text()}`);
  process.exit(1);
}

const { clones = [] } = await res.json();

/* date -> [clones, uniques] */
const rows = new Map();
if (existsSync(CSV)) {
  for (const line of readFileSync(CSV, 'utf8').trim().split('\n').slice(1)) {
    if (!line) continue;
    const [date, c, u] = line.split(',');
    rows.set(date, [Number(c), Number(u)]);
  }
}
for (const day of clones) {
  rows.set(day.timestamp.slice(0, 10), [day.count, day.uniques]);
}

const dates = [...rows.keys()].sort();
mkdirSync('data', { recursive: true });
writeFileSync(CSV,
  'date,clones,unique_cloners\n' +
  dates.map((d) => `${d},${rows.get(d)[0]},${rows.get(d)[1]}`).join('\n') + '\n');

const total = dates.reduce((a, d) => a + rows.get(d)[1], 0);
const gross = dates.reduce((a, d) => a + rows.get(d)[0], 0);

writeFileSync(JSON_OUT, JSON.stringify({
  installs: total,
  clones: gross,
  since: dates[0] || null,
  updated: new Date().toISOString().slice(0, 10),
  note: 'Unique git cloners, GitHub traffic API. A proxy for installs, not a headcount.',
}, null, 2) + '\n');

console.log(`${dates.length} days, ${total} unique cloners, ${gross} clones total`);
