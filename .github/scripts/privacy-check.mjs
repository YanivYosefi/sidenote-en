/*
 * The landing page promises that nothing leaves your machine. This is the
 * promise written as a test, so it cannot quietly stop being true.
 *
 * It fails the build if the plugin:
 *   - imports anything but the four Node built-ins it needs today,
 *   - mentions a network, process or code-evaluation API anywhere,
 *   - grows a dependency (a package.json or node_modules),
 *   - ships hooks, which would let it run shell commands on its own.
 *
 * Run it yourself: node .github/scripts/privacy-check.mjs
 */
import { readFileSync, readdirSync, existsSync, statSync } from 'node:fs';
import { join } from 'node:path';

const ROOT = process.argv[2] || '.';
const ALLOWED = new Set(['node:fs', 'node:os', 'node:path', 'node:readline']);
const FORBIDDEN = [
  [/\bfetch\s*\(/, 'fetch()'],
  [/\bXMLHttpRequest\b/, 'XMLHttpRequest'],
  [/\bWebSocket\b/, 'WebSocket'],
  [/\bEventSource\b/, 'EventSource'],
  [/['"](node:)?(https?|http2|net|tls|dgram|dns|child_process|worker_threads|cluster|vm)['"]/, 'a network, process or vm module'],
  [/\bprocess\.binding\b/, 'process.binding'],
  [/\beval\s*\(/, 'eval()'],
  [/\bnew\s+Function\s*\(/, 'new Function()'],
  [/\bimport\s*\(/, 'dynamic import()'],
  [/\brequire\s*\(/, 'require()'],
];

const problems = [];
const files = [];
(function walk(dir) {
  for (const name of readdirSync(dir)) {
    const p = join(dir, name);
    if (statSync(p).isDirectory()) walk(p);
    else if (/\.(m?js|cjs|ts)$/.test(name)) files.push(p);
  }
})(join(ROOT, 'server'));

for (const f of files) {
  const src = readFileSync(f, 'utf8');
  for (const m of src.matchAll(/^\s*import\s[^'"]*['"]([^'"]+)['"]/gm)) {
    if (!ALLOWED.has(m[1])) problems.push(`${f}: imports ${m[1]}`);
  }
  src.split('\n').forEach((line, i) => {
    const code = line.replace(/\/\/.*$/, '');
    for (const [re, what] of FORBIDDEN) {
      if (re.test(code)) problems.push(`${f}:${i + 1}: uses ${what}`);
    }
  });
}

for (const p of ['package.json', 'node_modules', 'server/package.json', 'server/node_modules']) {
  if (existsSync(join(ROOT, p))) problems.push(`${p} exists — the plugin has no dependencies and must not grow one`);
}
const manifest = JSON.parse(readFileSync(join(ROOT, '.claude-plugin/plugin.json'), 'utf8'));
if (manifest.hooks || existsSync(join(ROOT, 'hooks'))) problems.push('the plugin ships hooks');

if (problems.length) {
  console.error('Privacy check FAILED:\n  ' + problems.join('\n  '));
  process.exit(1);
}
console.log(`Privacy check passed: ${files.length} file(s), only ${[...ALLOWED].join(', ')}, no network, no dependencies, no hooks.`);
