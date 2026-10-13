#!/usr/bin/env node
'use strict';

/*
 * Resumable downloader for ghBrowser sessions.
 *
 *   node download.js --url <file-url> [--password pass123] [--out name.tgz]
 *
 * Logs in against the session proxy, then streams the file to disk with
 * HTTP Range requests so an interrupted transfer continues where it stopped.
 */

const fs = require('fs');
const path = require('path');
const { Readable } = require('stream');
const { pipeline } = require('stream/promises');

const args = process.argv.slice(2);
const opt = (name, fallback) => {
  const i = args.indexOf(`--${name}`);
  return i !== -1 && args[i + 1] ? args[i + 1] : fallback;
};

const PASSWORD = opt('password', process.env.GB_PASSWORD || 'pass123');
const OUT = path.resolve(opt('out', 'download.bin'));
const MAX_RETRIES = Number(opt('retries', 20));
const LOGIN_URL = opt('login-url', 'https://pursue-much-store-architectural.trycloudflare.com');

let cookie = '';

async function login() {
  const res = await fetch(`${LOGIN_URL}/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', Cookie: cookie },
    body: JSON.stringify({ password: PASSWORD }),
    redirect: 'manual',
  });

  const setCookie = res.headers.getSetCookie?.() ?? [];
  for (const c of setCookie) {
    const pair = c.split(';')[0];
    if (pair.startsWith('session=')) cookie = pair;
  }

  if (!cookie) throw new Error(`login failed (HTTP ${res.status}) — check --password`);
  console.log('logged in');
}

function localSize() {
  try {
    return fs.statSync(OUT).size;
  } catch {
    return 0;
  }
}

const fmt = (n) => {
  const u = ['B', 'KB', 'MB', 'GB', 'TB'];
  let i = 0;
  while (n >= 1024 && i < u.length - 1) {
    n /= 1024;
    i++;
  }
  return `${n.toFixed(2)} ${u[i]}`;
};

async function fetchRange(url, start) {
  const headers = { Cookie: cookie };
  if (start > 0) headers.Range = `bytes=${start}-`;

  const res = await fetch(url, { headers, redirect: 'follow' });

  if (start > 0 && res.status === 200) {
    // Server ignored the Range header: restart from scratch.
    await fs.promises.truncate(OUT, 0);
    return { res, start: 0 };
  }
  if (res.status === 416) {
    return { res, start, done: true };
  }
  if (!res.ok && res.status !== 206) {
    throw new Error(`HTTP ${res.status} ${res.statusText}`);
  }
  return { res, start };
}

async function head(url) {
  const res = await fetch(url, {
    method: 'HEAD',
    headers: { Cookie: cookie },
    redirect: 'follow',
  });
  const n = Number(res.headers.get('content-length') || 0);
  return n > 0 ? n : null;
}

async function run() {
  const url = opt('url');
  if (!url) {
    console.error('usage: node download.js --url <file-url> [--password pass123] [--out name.tgz]');
    process.exit(2);
  }

  await login();

  const known = await head(url);
  if (!known) {
    console.error('server did not report a size; is the /download route present?');
    process.exit(1);
  }
  const total = known;
  console.log(`remote size: ${fmt(total)}`);

  let lastReport = 0;

  for (let attempt = 1; attempt <= MAX_RETRIES; attempt++) {
    const start = localSize();
    if (start >= total) {
      console.log(`done -> ${OUT} (${fmt(start)})`);
      return;
    }

    const { res, start: from, done } = await fetchRange(url, start);
    if (done) break;

    // Cross-check the size the body actually claims, so a truncated or
    // wrong-file response is caught instead of silently accepted.
    const cr = res.headers.get('content-range');
    if (cr) {
      const t = Number(cr.split('/')[1]);
      if (Number.isFinite(t) && t > 0 && t !== total) {
        console.log(`\nwarning: server reports ${fmt(t)}, HEAD said ${fmt(total)}`);
      }
    }

    const out = fs.createWriteStream(OUT, from > 0 ? { flags: 'a' } : { flags: 'w' });

    let received = from;
    const ticker = setInterval(() => {
      const now = Date.now();
      if (now - lastReport < 1000) return;
      lastReport = now;
      const pct = ((received / total) * 100).toFixed(1);
      process.stdout.write(`\r${fmt(received)} / ${fmt(total)}  (${pct}%)   `);
    }, 250);

    try {
      await pipeline(Readable.fromWeb(res.body), out);
    } catch (e) {
      // Connection dropped mid-transfer: whatever landed on disk is kept and
      // the next attempt continues from there via a Range request.
      console.log(`\nconnection dropped (${e.message}); resuming from ${fmt(localSize())}...`);
    } finally {
      clearInterval(ticker);
    }

    received = localSize();
    process.stdout.write(`\r${fmt(received)} / ${fmt(total)}  (${((received / total) * 100).toFixed(1)}%)   \n`);

    if (received >= total) {
      console.log(`done -> ${OUT} (${fmt(received)})`);
      return;
    }

    if (received <= from) {
      console.log(`no progress this attempt (${fmt(received)}); backing off`);
    } else {
      console.log(`interrupted at ${fmt(received)}, resuming (attempt ${attempt}/${MAX_RETRIES})...`);
    }
    await new Promise((r) => setTimeout(r, Math.min(attempt * 2000, 15000)));
  }

  const size = localSize();
  if (size >= total) {
    console.log(`done -> ${OUT} (${fmt(size)})`);
  } else {
    console.error(`stopped at ${fmt(size)} of ${fmt(total)} — rerun the same command to resume`);
    process.exit(1);
  }
}

run().catch((e) => {
  console.error(`error: ${e.message}`);
  process.exit(1);
});
