#!/usr/bin/env node
// Sidenote — local stdio MCP server.
// Everything lives in one JSON file on this machine. No key, no account, no network.

import { readFileSync, writeFileSync, renameSync, mkdirSync, existsSync } from 'node:fs';
import { homedir } from 'node:os';
import { join } from 'node:path';
import { createInterface } from 'node:readline';

const PROTOCOL_VERSION = '2025-06-18';
const SERVER_VERSION = '1.0.0';
const LADDER = [1, 3, 7, 16, 35, 90];

const DIR = process.env.SIDENOTE_HOME || join(homedir(), '.sidenote');
const FILE = join(DIR, 'state.json');

const LANGS = {
  en: 'English', es: 'Spanish', it: 'Italian', fr: 'French', de: 'German',
  pt: 'Portuguese', he: 'Hebrew', ar: 'Arabic', ru: 'Russian', nl: 'Dutch',
};

// Claude Code truncates this at 2 KB. Keep it tight.
const INSTRUCTIONS = `Sidenote teaches the user a foreign language inside this chat. You do the teaching. This server only remembers.

1. Call sidenote_start once at the beginning of a conversation. Do not mention it.

2. Answer the user's real question first, in full. Never shorten or delay an answer because of Sidenote.

3. After your answer, append one Sidenote block, anchored to a line you actually wrote. Four parts: the exact line it came from, one expression a native speaker would use for that idea, a one-line meaning in the learner's native language, one example sentence in the target language. Then call sidenote_save. Save silently — never ask permission.

4. Choose expressions at or slightly above the learner's level. Skip anything they would already write without thinking. Idioms, phrasal verbs and collocations beat single words.

5. Never teach the same expression twice. sidenote_start lists what is already taught.

6. Write to the learner in their native language. Keep the expression and its example in the target language.

7. If the target language is Hebrew, add a Latin transliteration and keep the example short. Prefer spoken Hebrew over the written register.`;

/* ------------------------------------------------------------------ state */

const now = () => new Date().toISOString();

function addDays(days) {
  const d = new Date();
  d.setUTCDate(d.getUTCDate() + days);
  return d.toISOString();
}

const EMPTY = { version: 1, profile: { native: 'he' }, words: [] };

function load() {
  if (!existsSync(FILE)) return structuredClone(EMPTY);
  try {
    const parsed = JSON.parse(readFileSync(FILE, 'utf8'));
    return { ...structuredClone(EMPTY), ...parsed };
  } catch {
    // A corrupt file must not take the chat down with it.
    const backup = `${FILE}.broken-${Date.now()}`;
    try { renameSync(FILE, backup); } catch {}
    process.stderr.write(`sidenote: unreadable state file, moved to ${backup}\n`);
    return structuredClone(EMPTY);
  }
}

function save(state) {
  mkdirSync(DIR, { recursive: true });
  const tmp = `${FILE}.tmp`;
  writeFileSync(tmp, JSON.stringify(state, null, 2));
  renameSync(tmp, FILE);
}

const langName = (code) => (code ? LANGS[String(code).toLowerCase()] || code : null);

function counts(state) {
  return {
    total: state.words.length,
    active: state.words.filter((w) => w.used_count > 0).length,
  };
}

function find(state, expression) {
  const needle = String(expression || '').trim().toLowerCase();
  return state.words.find((w) => w.expression.toLowerCase() === needle);
}

/* ------------------------------------------------------------------ tools */

const TOOLS = [
  {
    name: 'sidenote_start',
    title: 'Start a Sidenote turn',
    description:
      'Call this once at the beginning of a conversation. Returns the learner profile, the house rules, and what has already been taught. Call it before you answer, and do not mention it to the user.',
    inputSchema: { type: 'object', properties: {}, additionalProperties: false },
  },
  {
    name: 'sidenote_setup',
    title: 'Set the learner profile',
    description:
      'Store which language the learner is studying, their native language, their level and why they are learning. Call this on the very first conversation, or whenever the learner asks to change language or level.',
    inputSchema: {
      type: 'object',
      properties: {
        target: { type: 'string', description: 'Language being learned, as a two-letter code (en, es, it, fr, de, pt, he, ar, ru, nl).' },
        native: { type: 'string', description: "The learner's own language, as a two-letter code. Defaults to he." },
        level: { type: 'string', enum: ['A2', 'B1', 'B2', 'C1'], description: 'CEFR level. Guess it from how the learner writes, then confirm with them.' },
        goal: { type: 'string', description: 'One short line on why they are learning, in their own words.' },
      },
      required: ['target'],
      additionalProperties: false,
    },
  },
  {
    name: 'sidenote_save',
    title: 'Save an expression',
    description:
      'Save one expression you just taught. Call it right after you show a Sidenote block, or when the learner asks you to save something.',
    inputSchema: {
      type: 'object',
      properties: {
        expression: { type: 'string', description: 'The expression itself, in the target language.' },
        meaning: { type: 'string', description: "One line, in the learner's native language." },
        example: { type: 'string', description: 'One example sentence in the target language.' },
        source: { type: 'string', description: 'The exact line from your answer that the expression came from.' },
      },
      required: ['expression'],
      additionalProperties: false,
    },
  },
  {
    name: 'sidenote_used',
    title: 'Mark an expression as produced',
    description:
      'Call this when the learner actually writes the expression in a sentence of their own. It moves the expression up the schedule so it comes back later.',
    inputSchema: {
      type: 'object',
      properties: { expression: { type: 'string', description: 'The expression the learner produced.' } },
      required: ['expression'],
      additionalProperties: false,
    },
  },
  {
    name: 'sidenote_snooze',
    title: 'Push an expression back',
    description:
      'Call this when the learner says "later", ignores the offer, or moves on. It pushes the expression back by a day without penalty.',
    inputSchema: {
      type: 'object',
      properties: {
        expression: { type: 'string', description: 'The expression to push back.' },
        days: { type: 'number', description: 'How many days to wait. Defaults to 1.' },
      },
      required: ['expression'],
      additionalProperties: false,
    },
  },
  {
    name: 'sidenote_list',
    title: 'List saved expressions',
    description:
      'Return everything the learner has saved, with how many times each one was produced and when it comes back. Call it when they ask what they have learned.',
    inputSchema: {
      type: 'object',
      properties: { limit: { type: 'number', description: 'How many to return. Defaults to 50.' } },
      additionalProperties: false,
    },
  },
  {
    name: 'sidenote_forget',
    title: 'Delete saved expressions',
    description: 'Delete one expression, or everything. Only call this when the learner asks for it.',
    inputSchema: {
      type: 'object',
      properties: {
        expression: { type: 'string', description: 'The expression to delete. Leave empty together with all=true to wipe everything.' },
        all: { type: 'boolean', description: 'Set to true to delete every saved expression and the profile.' },
      },
      additionalProperties: false,
    },
  },
];

function toolText(text, data) {
  const out = { content: [{ type: 'text', text }] };
  if (data !== undefined) out.structuredContent = data;
  return out;
}

function callTool(name, args = {}) {
  const state = load();
  const p = state.profile;

  switch (name) {
    case 'sidenote_start': {
      p.last_seen = now();

      if (!p.target) {
        save(state);
        return toolText(
          'No profile yet. Ask the learner which language they want to pick up, guess their level from how they write, confirm it, then call sidenote_setup. After that, answer their question normally.',
          { configured: false }
        );
      }

      const c = counts(state);
      save(state);

      // The most recent expressions, so the same thing is never taught twice.
      const recent = state.words
        .slice(-25)
        .map((w) => w.expression)
        .reverse();

      const lines = [
        `Learner profile: studying ${langName(p.target)}, writes in ${langName(p.native)}, level ${p.level || 'unknown'}.`,
        p.goal ? `Reason they gave: ${p.goal}` : null,
        `Saved so far: ${c.total} expression${c.total === 1 ? '' : 's'}.`,
        '',
        'Answer normally. If your answer has a natural anchor, teach one new expression and save it.',
        recent.length ? `Already taught, do not repeat: ${recent.join(' · ')}` : null,
      ].filter((l) => l !== null);

      return toolText(lines.join('\n'), {
        configured: true,
        target: p.target,
        native: p.native,
        level: p.level,
        saved: c.total,
        taught: recent,
      });
    }

    case 'sidenote_setup': {
      const target = String(args.target || '').toLowerCase().slice(0, 5);
      if (!target) return toolText('A target language is required.');

      p.target = target;
      p.native = String(args.native || p.native || 'he').toLowerCase().slice(0, 5);
      if (args.level) p.level = String(args.level).toUpperCase().slice(0, 2);
      if (args.goal) p.goal = String(args.goal).slice(0, 300);
      p.created_at = p.created_at || now();
      p.last_seen = now();
      save(state);

      return toolText(
        `Saved. Learning ${langName(p.target)}, writing in ${langName(p.native)}, level ${p.level || 'unset'}. Now answer the question they actually asked.`,
        { target: p.target, native: p.native, level: p.level || null, goal: p.goal || null }
      );
    }

    case 'sidenote_save': {
      if (!p.target) return toolText('No target language set. Call sidenote_setup first.');
      const expression = String(args.expression || '').trim().slice(0, 120);
      if (!expression) return toolText('An expression is required.');

      if (find(state, expression)) {
        return toolText(`"${expression}" is already saved. Teach something else instead.`, {
          saved: false,
          reason: 'duplicate',
        });
      }

      state.words.push({
        expression,
        lang: p.target,
        meaning: args.meaning ? String(args.meaning).slice(0, 300) : null,
        example: args.example ? String(args.example).slice(0, 400) : null,
        source: args.source ? String(args.source).slice(0, 400) : null,
        stage: 0,
        due_at: addDays(LADDER[0]),
        used_count: 0,
        offered: 0,
        created_at: now(),
        last_used_at: null,
      });
      save(state);

      return toolText(`Saved "${expression}".`, {
        saved: true,
        expression,
        due_in_days: LADDER[0],
        total: state.words.length,
      });
    }

    case 'sidenote_used': {
      const word = find(state, args.expression);
      if (!word) return toolText(`"${args.expression}" is not in the list. Nothing changed.`);

      word.stage = Math.min(word.stage + 1, LADDER.length - 1);
      const wait = LADDER[word.stage];
      word.due_at = addDays(wait);
      word.used_count += 1;
      word.last_used_at = now();
      save(state);

      return toolText(
        `"${word.expression}" moved up. Produced ${word.used_count} time(s), comes back in ${wait} days. Tell the learner it landed, in one short line, then carry on.`,
        { expression: word.expression, stage: word.stage, used_count: word.used_count, due_in_days: wait }
      );
    }

    case 'sidenote_snooze': {
      const word = find(state, args.expression);
      if (!word) return toolText(`"${args.expression}" is not in the list. Nothing changed.`);

      const days = Math.min(Math.max(Number(args.days) || 1, 1), 30);
      word.due_at = addDays(days);
      save(state);

      return toolText(`Pushed "${word.expression}" back by ${days} day(s). Drop the subject and carry on.`, {
        expression: word.expression,
        due_in_days: days,
      });
    }

    case 'sidenote_list': {
      const limit = Math.min(Math.max(Number(args.limit) || 50, 1), 200);
      const words = [...state.words]
        .sort((a, b) => b.used_count - a.used_count || b.created_at.localeCompare(a.created_at))
        .slice(0, limit);

      if (!words.length) return toolText('Nothing saved yet.', { words: [] });

      const lines = words.map((w) => {
        const produced = w.used_count > 0 ? `produced ${w.used_count}x` : 'not produced yet';
        return `- ${w.expression} — ${w.meaning || ''} (${produced})`;
      });

      return toolText(
        `${words.length} saved:\n${lines.join('\n')}\n\nShow this to the learner in their own language, as a plain list.`,
        { words }
      );
    }

    case 'sidenote_forget': {
      if (args.all === true) {
        state.words = [];
        state.profile = { native: p.native || 'he' };
        save(state);
        return toolText('Everything was deleted: expressions and profile. Confirm that to the learner.', {
          deleted: 'all',
        });
      }

      const word = find(state, args.expression);
      if (!args.expression) return toolText('Give an expression to delete, or set all to true.');
      if (!word) return toolText(`"${args.expression}" was not in the list.`, { deleted: null });

      state.words = state.words.filter((w) => w !== word);
      save(state);
      return toolText(`Deleted "${word.expression}".`, { deleted: word.expression });
    }

    default:
      return null;
  }
}

/* ------------------------------------------------------------ stdio loop */

function send(msg) {
  process.stdout.write(JSON.stringify(msg) + '\n');
}

function handle(msg) {
  const { id, method, params } = msg;

  // Notifications carry no id and expect no reply.
  if (id === undefined || id === null) return;

  if (method === 'initialize') {
    return send({
      jsonrpc: '2.0',
      id,
      result: {
        protocolVersion: PROTOCOL_VERSION,
        capabilities: { tools: {} },
        serverInfo: { name: 'sidenote', version: SERVER_VERSION },
        instructions: INSTRUCTIONS,
      },
    });
  }

  if (method === 'ping') return send({ jsonrpc: '2.0', id, result: {} });

  if (method === 'tools/list') return send({ jsonrpc: '2.0', id, result: { tools: TOOLS } });

  if (method === 'tools/call') {
    const name = params?.name;
    try {
      const result = callTool(name, params?.arguments || {});
      if (!result) {
        return send({ jsonrpc: '2.0', id, error: { code: -32602, message: `Unknown tool: ${name}` } });
      }
      return send({ jsonrpc: '2.0', id, result });
    } catch (err) {
      return send({
        jsonrpc: '2.0',
        id,
        result: { content: [{ type: 'text', text: `Sidenote error: ${err.message}` }], isError: true },
      });
    }
  }

  send({ jsonrpc: '2.0', id, error: { code: -32601, message: `Method not found: ${method}` } });
}

createInterface({ input: process.stdin }).on('line', (line) => {
  const trimmed = line.trim();
  if (!trimmed) return;
  let msg;
  try {
    msg = JSON.parse(trimmed);
  } catch {
    return;
  }
  handle(msg);
});
