#!/usr/bin/env node
/*
 * Issue supporter keys, the ones that turn Sidenote's sponsored line off.
 *
 *   node tools/supporter-keys.mjs init          once: makes the signing key pair
 *   node tools/supporter-keys.mjs issue <who>   per sale: prints a key to send them
 *
 * init keeps the private half in ~/.sidenote-issuer/private.pem, outside the
 * repo, and prints the public half. Paste that into SUPPORTER_PUBLIC_KEY in
 * server/index.mjs and ship it. Never commit the private key: anyone holding it
 * can issue keys. <who> is whatever you want to remember the sale by, such as
 * an order number. It is readable inside the key, so do not put an email in it.
 */
import { generateKeyPairSync, createPrivateKey, sign } from 'node:crypto';
import { mkdirSync, writeFileSync, readFileSync, existsSync } from 'node:fs';
import { homedir } from 'node:os';
import { join } from 'node:path';

const DIR = join(homedir(), '.sidenote-issuer');
const PRIV = join(DIR, 'private.pem');
const [cmd, who] = process.argv.slice(2);

if (cmd === 'init') {
  if (existsSync(PRIV)) {
    console.error(`${PRIV} already exists. Keys issued with it would stop working if it were replaced.`);
    process.exit(1);
  }
  const { publicKey, privateKey } = generateKeyPairSync('ed25519');
  mkdirSync(DIR, { recursive: true, mode: 0o700 });
  writeFileSync(PRIV, privateKey.export({ type: 'pkcs8', format: 'pem' }), { mode: 0o600 });
  console.log(`Private key: ${PRIV} (back it up somewhere safe)`);
  console.log(`SUPPORTER_PUBLIC_KEY = '${publicKey.export({ type: 'spki', format: 'der' }).toString('base64')}'`);
} else if (cmd === 'issue' && who) {
  const payload = Buffer.from(`${who}|${new Date().toISOString().slice(0, 10)}`);
  const sig = sign(null, payload, createPrivateKey(readFileSync(PRIV)));
  console.log(`SN1-${payload.toString('base64url')}.${sig.toString('base64url')}`);
} else {
  console.error('usage: supporter-keys.mjs init | issue <order-id>');
  process.exit(1);
}
