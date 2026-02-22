const express = require('express');
const cors = require('cors');
const Database = require('better-sqlite3');
const path = require('path');
require('dotenv').config();

const app = express();
const PORT = Number(process.env.PORT || 3000);
const ADMIN_TOKEN = process.env.ADMIN_TOKEN || '';
const OPENROUTER_API_KEY = process.env.OPENROUTER_API_KEY || '';
const OPENROUTER_MODEL = process.env.OPENROUTER_MODEL || 'openai/gpt-4o-mini';

app.use(cors());
app.use(express.json({ limit: '1mb' }));
app.use(express.static(path.join(__dirname, 'public')));

const db = new Database(path.join(__dirname, 'data.sqlite'));
db.pragma('journal_mode = WAL');
db.exec(`
CREATE TABLE IF NOT EXISTS users (
  user_id TEXT PRIMARY KEY,
  free_date TEXT,
  free_used INTEGER DEFAULT 0,
  paid_credits INTEGER DEFAULT 0,
  updated_at TEXT
);
CREATE TABLE IF NOT EXISTS payments (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id TEXT,
  source TEXT,
  amount_usd REAL,
  credits INTEGER,
  raw TEXT,
  created_at TEXT
);
`);

const getUser = db.prepare('SELECT * FROM users WHERE user_id = ?');
const upsertUser = db.prepare(`
INSERT INTO users (user_id, free_date, free_used, paid_credits, updated_at)
VALUES (@user_id, @free_date, @free_used, @paid_credits, @updated_at)
ON CONFLICT(user_id) DO UPDATE SET
free_date=excluded.free_date,
free_used=excluded.free_used,
paid_credits=excluded.paid_credits,
updated_at=excluded.updated_at
`);

function todayUTC() {
  return new Date().toISOString().slice(0, 10);
}

function normalizeUser(user_id) {
  return String(user_id || '').trim();
}

function ensureUser(user_id) {
  const uid = normalizeUser(user_id);
  if (!uid) return null;
  const now = new Date().toISOString();
  const t = todayUTC();
  let row = getUser.get(uid);
  if (!row) {
    row = { user_id: uid, free_date: t, free_used: 0, paid_credits: 0, updated_at: now };
    upsertUser.run(row);
  }
  if (row.free_date !== t) {
    row.free_date = t;
    row.free_used = 0;
    row.updated_at = now;
    upsertUser.run(row);
  }
  return row;
}

function availableCredits(row) {
  const freeLeft = Math.max(0, 3 - (row.free_used || 0));
  const paid = Math.max(0, row.paid_credits || 0);
  return { freeLeft, paid, total: freeLeft + paid };
}

app.get('/health', (_req, res) => {
  res.status(200).json({ ok: true, service: 'micro-saas-template', model: OPENROUTER_MODEL });
});

app.get('/api/credits', (req, res) => {
  const user_id = normalizeUser(req.query.user);
  if (!user_id) return res.status(400).json({ error: 'user is required' });
  const row = ensureUser(user_id);
  return res.json({ user_id, ...availableCredits(row), freeDailyLimit: 3, paidPackCredits: 100 });
});

app.post('/api/use', async (req, res) => {
  const user_id = normalizeUser(req.body?.user_id);
  const prompt = String(req.body?.prompt || 'Say hello').slice(0, 4000);
  if (!user_id) return res.status(400).json({ error: 'user_id is required' });

  const row = ensureUser(user_id);
  const now = new Date().toISOString();
  let chargeType = null;

  if ((row.free_used || 0) < 3) {
    row.free_used = (row.free_used || 0) + 1;
    chargeType = 'free';
  } else if ((row.paid_credits || 0) > 0) {
    row.paid_credits = row.paid_credits - 1;
    chargeType = 'paid';
  } else {
    return res.status(402).json({ error: 'insufficient_credits', message: 'Top up required' });
  }

  row.updated_at = now;
  upsertUser.run(row);

  let output = `Demo output for: ${prompt}`;
  if (OPENROUTER_API_KEY) {
    try {
      const rr = await fetch((process.env.OPENROUTER_BASE_URL || 'https://openrouter.ai/api/v1') + '/chat/completions', {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${OPENROUTER_API_KEY}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          model: OPENROUTER_MODEL,
          messages: [
            { role: 'system', content: 'You are a tool backend. Respond concisely.' },
            { role: 'user', content: prompt }
          ],
          temperature: 0.2
        })
      });
      const data = await rr.json();
      output = data?.choices?.[0]?.message?.content || output;
    } catch {
      // fallback keeps service alive
    }
  }

  return res.json({ ok: true, used: chargeType, credits: availableCredits(row), result: output });
});

app.post('/api/paypal/webhook', (req, res) => {
  const user_id = normalizeUser(req.body?.user_id || req.body?.resource?.custom_id);
  if (!user_id) return res.status(400).json({ error: 'user_id missing' });

  const row = ensureUser(user_id);
  row.paid_credits = (row.paid_credits || 0) + 100;
  row.updated_at = new Date().toISOString();
  upsertUser.run(row);

  db.prepare('INSERT INTO payments (user_id, source, amount_usd, credits, raw, created_at) VALUES (?, ?, ?, ?, ?, ?)')
    .run(user_id, 'paypal', 1, 100, JSON.stringify(req.body || {}), new Date().toISOString());

  return res.json({ ok: true, user_id, credited: 100, credits: availableCredits(row) });
});

app.post('/api/unlock/local', (req, res) => {
  const auth = req.headers['authorization'] || '';
  const token = auth.startsWith('Bearer ') ? auth.slice(7) : String(req.body?.admin_token || '');
  if (!ADMIN_TOKEN || token !== ADMIN_TOKEN) return res.status(401).json({ error: 'unauthorized' });

  const user_id = normalizeUser(req.body?.user_id);
  const credits = Number(req.body?.credits || 100);
  if (!user_id) return res.status(400).json({ error: 'user_id is required' });

  const row = ensureUser(user_id);
  row.paid_credits = (row.paid_credits || 0) + Math.max(0, credits);
  row.updated_at = new Date().toISOString();
  upsertUser.run(row);

  db.prepare('INSERT INTO payments (user_id, source, amount_usd, credits, raw, created_at) VALUES (?, ?, ?, ?, ?, ?)')
    .run(user_id, 'local_unlock', 0, Math.max(0, credits), JSON.stringify(req.body || {}), new Date().toISOString());

  return res.json({ ok: true, user_id, credited: Math.max(0, credits), credits: availableCredits(row) });
});

app.listen(PORT, () => {
  console.log(`micro-saas running on :${PORT}`);
});
