import { test } from 'node:test';
import assert from 'node:assert/strict';
import { spawn } from 'node:child_process';
import { mkdtempSync, readFileSync, writeFileSync, readdirSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { createInterface } from 'node:readline';

async function session(t) {
  const dir = mkdtempSync(join(tmpdir(), 'sidenote-test-'));
  const child = spawn(process.execPath, [process.env.SIDENOTE_SERVER || 'server/index.mjs'], {
    env: { ...process.env, SIDENOTE_HOME: dir }, stdio: ['pipe', 'pipe', 'pipe'],
  });
  const waiting = new Map();
  let id = 0;
  createInterface({ input: child.stdout }).on('line', (line) => {
    const response = JSON.parse(line);
    waiting.get(response.id)?.(response);
    waiting.delete(response.id);
  });
  t.after(() => { child.kill(); rmSync(dir, { recursive: true, force: true }); });
  const request = (method, params = {}) => new Promise((resolve, reject) => {
    const current = ++id;
    const timeout = setTimeout(() => reject(new Error(`Timeout: ${method}`)), 5000);
    waiting.set(current, (response) => { clearTimeout(timeout); resolve(response); });
    child.stdin.write(JSON.stringify({ jsonrpc: '2.0', id: current, method, params }) + '\n');
  });
  const call = async (name, args = {}) => {
    const response = await request('tools/call', { name, arguments: args });
    assert.equal(response.error, undefined);
    assert.notEqual(response.result.isError, true, response.result.content?.[0]?.text);
    return response.result;
  };
  return { dir, request, call, read: () => JSON.parse(readFileSync(join(dir, 'state.json'), 'utf8')),
    write: (state) => writeFileSync(join(dir, 'state.json'), JSON.stringify(state)) };
}

test('MCP initialization, onboarding and version agree with the manifest', async (t) => {
  const s = await session(t);
  const init = await s.request('initialize', { protocolVersion: '2025-06-18', capabilities: {}, clientInfo: { name: 'test', version: '1' } });
  assert.equal(init.result.serverInfo.version, JSON.parse(readFileSync('.claude-plugin/plugin.json')).version);
  assert.ok(Buffer.byteLength(init.result.instructions) < 2048);
  assert.equal((await s.request('tools/list')).result.tools.length, 7);
  assert.equal((await s.call('sidenote_start')).structuredContent.configured, false);
  await s.call('sidenote_setup', { target: 'en', native: 'he', level: 'B2' });
  assert.equal((await s.call('sidenote_start')).structuredContent.target, 'en');
  assert.equal((await s.request('tools/call', { name: 'unknown' })).error.code, -32602);
});

test('one overdue reminder, postponement and the complete spaced ladder', async (t) => {
  const s = await session(t);
  await s.call('sidenote_setup', { target: 'en' });
  for (const expression of ['ship it', 'circle back']) await s.call('sidenote_save', { expression, meaning: 'meaning', example: 'example' });
  assert.equal((await s.call('sidenote_start')).structuredContent.reminder, null);
  const state = s.read();
  state.words[0].due_at = '2000-01-01T00:00:00.000Z';
  state.words[1].due_at = '2001-01-01T00:00:00.000Z';
  s.write(state);
  const start = (await s.call('sidenote_start')).structuredContent;
  assert.equal(start.reminder.expression, 'ship it');
  assert.equal(start.reminder.example, 'example');
  assert.equal(Array.isArray(start.reminder), false);
  await s.call('sidenote_snooze', { expression: 'ship it' });
  assert.ok(Date.parse(s.read().words[0].due_at) > Date.now());
  assert.equal(s.read().words[0].stage, 0);
  for (const days of [3, 7, 16, 35, 90, 90]) {
    const result = (await s.call('sidenote_used', { expression: 'ship it' })).structuredContent;
    assert.equal(result.due_in_days, days);
  }
  assert.equal(s.read().words[0].used_count, 6);
});

test('language switching isolates reminders, duplicate detection, use and deletion', async (t) => {
  const s = await session(t);
  await s.call('sidenote_setup', { target: 'en', native: 'he' });
  await s.call('sidenote_save', { expression: 'same expression' });
  assert.equal((await s.call('sidenote_save', { expression: ' SAME EXPRESSION ' })).structuredContent.saved, false);
  const state = s.read(); state.words[0].due_at = '2000-01-01T00:00:00.000Z'; s.write(state);
  await s.call('sidenote_setup', { target: 'es' });
  assert.equal((await s.call('sidenote_start')).structuredContent.reminder, null);
  assert.equal((await s.call('sidenote_list')).structuredContent.words.length, 0);
  assert.equal((await s.call('sidenote_save', { expression: 'same expression' })).structuredContent.saved, true);
  await s.call('sidenote_used', { expression: 'same expression' });
  assert.equal(s.read().words[0].used_count, 0);
  await s.call('sidenote_forget', { expression: 'same expression' });
  assert.equal(s.read().words.length, 1);
  await s.call('sidenote_setup', { target: 'en' });
  assert.equal((await s.call('sidenote_start')).structuredContent.reminder.expression, 'same expression');
  await s.call('sidenote_forget', { all: true });
  assert.deepEqual(s.read().profile, {});
  assert.deepEqual(s.read().words, []);
});

test('older vocabulary remains visible and malformed state is backed up', async (t) => {
  const s = await session(t);
  await s.call('sidenote_setup', { target: 'ja' });
  for (let i = 0; i < 30; i++) await s.call('sidenote_save', { expression: `expression ${i}` });
  assert.equal((await s.call('sidenote_start')).structuredContent.taught.length, 30);
  const original = s.read();
  for (const broken of ['{invalid', JSON.stringify({ profile: null, words: null }), JSON.stringify({ profile: {}, words: [null] })]) {
    writeFileSync(join(s.dir, 'state.json'), broken);
    assert.equal((await s.call('sidenote_start')).structuredContent.configured, false);
    assert.ok(readdirSync(s.dir).some((name) => name.startsWith('state.json.broken-') && readFileSync(join(s.dir, name), 'utf8') === broken));
  }
  s.write(original);
  assert.equal((await s.call('sidenote_start')).structuredContent.saved, 30);
});


test('a due reminder accompanies new learning and advances without requiring learner production', async (t) => {
  const s = await session(t);
  await s.call('sidenote_setup', { target: 'en' });
  await s.call('sidenote_save', { expression: 'ship it' });
  for (const [i, days] of [3, 7, 16, 35, 90, 90].entries()) {
    const state = s.read(); state.words[0].due_at = '2000-01-01T00:00:00.000Z'; s.write(state);
    const start = await s.call('sidenote_start');
    assert.equal(start.structuredContent.reminder.expression, 'ship it');
    assert.match(start.content[0].text, /DIFFERENT NEW expression/);
    assert.equal(s.read().words[0].stage, Math.min(i, 5));
    const saved = await s.call('sidenote_save', { expression: `new expression ${i}`, recalled_expression: 'ship it' });
    assert.equal(saved.structuredContent.saved, true);
    assert.equal(saved.structuredContent.recalled, 'ship it');
    const word = s.read().words[0];
    assert.equal(word.used_count, 0);
    assert.equal(word.reminded_count, i + 1);
    assert.ok(Math.abs((Date.parse(word.due_at) - Date.now()) / 864e5 - days) < 0.01);
    assert.equal((await s.call('sidenote_start')).structuredContent.reminder, null);
  }
  const before = s.read().words[0];
  await s.call('sidenote_save', { expression: 'future reminder ignored', recalled_expression: 'ship it' });
  assert.deepEqual(s.read().words[0], before);
  await s.call('sidenote_setup', { target: 'es' });
  await s.call('sidenote_save', { expression: 'nuevo', recalled_expression: 'ship it' });
  assert.deepEqual(s.read().words[0], before);
});

test('sidenote_start tells Claude what the learner\'s level rules out', async (t) => {
  const s = await session(t);
  await s.call('sidenote_setup', { target: 'en', native: 'he', level: 'C1' });
  const c1 = (await s.call('sidenote_start')).content[0].text;
  assert.match(c1, /Level C1:/);
  assert.match(c1, /Never a basic phrase/);
  await s.call('sidenote_setup', { target: 'en', native: 'he', level: 'A2' });
  const a2 = (await s.call('sidenote_start')).content[0].text;
  assert.match(a2, /Level A2:/);
  assert.match(a2, /No idioms/);
});
