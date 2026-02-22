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
const PAYPAL_MODE = (process.env.PAYPAL_MODE || 'sandbox').toLowerCase();
const PAYPAL_CLIENT_ID = process.env.PAYPAL_CLIENT_ID || '';
const PAYPAL_CLIENT_SECRET = process.env.PAYPAL_CLIENT_SECRET || '';
const PAYPAL_WEBHOOK_ID = process.env.PAYPAL_WEBHOOK_ID || '';
const PAYPAL_BASE = PAYPAL_MODE === 'live' ? 'https://api-m.paypal.com' : 'https://api-m.sandbox.paypal.com';

app.use(cors());
app.use(express.json({ limit: '1mb' }));

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
CREATE TABLE IF NOT EXISTS purchases (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  provider TEXT NOT NULL,
  provider_ref TEXT NOT NULL UNIQUE,
  event_id TEXT,
  user_id TEXT,
  status TEXT,
  amount REAL,
  currency TEXT,
  credits INTEGER DEFAULT 0,
  verified INTEGER DEFAULT 0,
  raw TEXT,
  created_at TEXT,
  updated_at TEXT
);
CREATE TABLE IF NOT EXISTS grants (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id TEXT NOT NULL,
  credits INTEGER NOT NULL,
  note TEXT,
  created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS events (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  type TEXT NOT NULL,
  user_id TEXT,
  meta_json TEXT,
  created_at TEXT NOT NULL
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

function nowISO() { return new Date().toISOString(); }
function todayUTC() { return new Date().toISOString().slice(0, 10); }
function normalizeUser(user_id) { return String(user_id || '').trim(); }
function logEvent(type, user_id = null, meta = {}) {
  db.prepare('INSERT INTO events (type, user_id, meta_json, created_at) VALUES (?, ?, ?, ?)')
    .run(type, normalizeUser(user_id) || null, JSON.stringify(meta || {}), nowISO());
}

function ensureUser(user_id) {
  const uid = normalizeUser(user_id); if (!uid) return null;
  const t = todayUTC(); let row = getUser.get(uid);
  if (!row) {
    row = { user_id: uid, free_date: t, free_used: 0, paid_credits: 0, updated_at: nowISO() };
    upsertUser.run(row);
  }
  if (row.free_date !== t) {
    row.free_date = t; row.free_used = 0; row.updated_at = nowISO(); upsertUser.run(row);
  }
  return row;
}
function availableCredits(row) {
  const freeLeft = Math.max(0, 3 - (row.free_used || 0));
  const paid = Math.max(0, row.paid_credits || 0);
  return { freeLeft, paid, total: freeLeft + paid };
}

async function paypalAccessToken() {
  const basic = Buffer.from(`${PAYPAL_CLIENT_ID}:${PAYPAL_CLIENT_SECRET}`).toString('base64');
  const r = await fetch(`${PAYPAL_BASE}/v1/oauth2/token`, {
    method: 'POST', headers: { Authorization: `Basic ${basic}`, 'Content-Type': 'application/x-www-form-urlencoded' }, body: 'grant_type=client_credentials'
  });
  const data = await r.json();
  if (!r.ok || !data?.access_token) throw new Error(`paypal_oauth_failed:${r.status}`);
  return data.access_token;
}

async function verifyPaypalWebhook(headers, body) {
  if (!PAYPAL_CLIENT_ID || !PAYPAL_CLIENT_SECRET || !PAYPAL_WEBHOOK_ID) return { ok: false, reason: 'paypal_env_missing' };
  const transmission_id = headers['paypal-transmission-id'];
  const transmission_time = headers['paypal-transmission-time'];
  const cert_url = headers['paypal-cert-url'];
  const auth_algo = headers['paypal-auth-algo'];
  const transmission_sig = headers['paypal-transmission-sig'];
  if (!transmission_id || !transmission_time || !cert_url || !auth_algo || !transmission_sig) return { ok: false, reason: 'paypal_headers_missing' };
  const token = await paypalAccessToken();
  const verifyResp = await fetch(`${PAYPAL_BASE}/v1/notifications/verify-webhook-signature`, {
    method: 'POST', headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' },
    body: JSON.stringify({ transmission_id, transmission_time, cert_url, auth_algo, transmission_sig, webhook_id: PAYPAL_WEBHOOK_ID, webhook_event: body })
  });
  const verifyData = await verifyResp.json();
  const ok = verifyResp.ok && verifyData?.verification_status === 'SUCCESS';
  return { ok, reason: verifyData?.verification_status || `http_${verifyResp.status}`, raw: verifyData };
}

function extractPaypalUserId(event) {
  return normalizeUser(event?.resource?.custom_id || event?.resource?.invoice_id || event?.resource?.purchase_units?.[0]?.custom_id || event?.user_id);
}
function extractPaypalProviderRef(event) { return String(event?.resource?.id || event?.id || '').trim(); }

app.get('/health', (_req, res) => {
  res.status(200).json({ ok: true, service: 'micro-saas-template', model: OPENROUTER_MODEL, paypal_mode: PAYPAL_MODE });
});

app.get('/', (req, res) => {
  logEvent('page_view', req.query?.user || null, { ip: req.ip, ua: req.headers['user-agent'] || '' });
  res.sendFile(path.join(__dirname, 'public', 'index.html'));
});
app.use(express.static(path.join(__dirname, 'public')));

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

  let chargeType = null;
  if ((row.free_used || 0) < 3) { row.free_used += 1; chargeType = 'free'; }
  else if ((row.paid_credits || 0) > 0) { row.paid_credits -= 1; chargeType = 'paid'; }
  else return res.status(402).json({ error: 'insufficient_credits', message: 'Top up required' });

  row.updated_at = nowISO();
  upsertUser.run(row);

  let output = `Demo output for: ${prompt}`;
  if (OPENROUTER_API_KEY) {
    try {
      const rr = await fetch((process.env.OPENROUTER_BASE_URL || 'https://openrouter.ai/api/v1') + '/chat/completions', {
        method: 'POST', headers: { Authorization: `Bearer ${OPENROUTER_API_KEY}`, 'Content-Type': 'application/json' },
        body: JSON.stringify({ model: OPENROUTER_MODEL, messages: [{ role: 'system', content: 'Respond concisely.' }, { role: 'user', content: prompt }], temperature: 0.2 })
      });
      const data = await rr.json(); output = data?.choices?.[0]?.message?.content || output;
    } catch {}
  }

  logEvent('use', user_id, { mode: chargeType });
  return res.json({ ok: true, used: chargeType, credits: availableCredits(row), result: output });
});

app.post('/api/paypal/webhook', async (req, res) => {
  try {
    const event = req.body || {};
    const providerRef = extractPaypalProviderRef(event);
    const eventId = String(event?.id || '').trim();
    if (!providerRef) return res.status(400).json({ ok: false, error: 'provider_ref_missing' });

    const verified = await verifyPaypalWebhook(req.headers, event);
    if (!verified.ok) {
      db.prepare('INSERT OR IGNORE INTO purchases (provider, provider_ref, event_id, status, verified, raw, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)')
        .run('paypal', providerRef, eventId || null, `rejected:${verified.reason}`, 0, JSON.stringify({ event, verify: verified.raw || null }), nowISO(), nowISO());
      return res.status(400).json({ ok: false, error: 'verification_failed', reason: verified.reason });
    }

    const eventType = String(event?.event_type || '');
    if (eventType !== 'PAYMENT.CAPTURE.COMPLETED' && eventType !== 'CHECKOUT.ORDER.APPROVED') {
      db.prepare('INSERT OR IGNORE INTO purchases (provider, provider_ref, event_id, status, verified, raw, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)')
        .run('paypal', providerRef, eventId || null, `ignored:${eventType}`, 1, JSON.stringify(event), nowISO(), nowISO());
      return res.json({ ok: true, ignored: true, event_type: eventType });
    }

    const existing = db.prepare('SELECT id FROM purchases WHERE provider = ? AND provider_ref = ?').get('paypal', providerRef);
    if (existing) return res.json({ ok: true, duplicate: true, provider_ref: providerRef });

    const user_id = extractPaypalUserId(event);
    if (!user_id) return res.status(400).json({ ok: false, error: 'user_id_missing_in_event' });

    const row = ensureUser(user_id);
    row.paid_credits += 100; row.updated_at = nowISO(); upsertUser.run(row);

    const amount = Number(event?.resource?.amount?.value || 1);
    const currency = String(event?.resource?.amount?.currency_code || 'USD');
    db.prepare('INSERT INTO purchases (provider, provider_ref, event_id, user_id, status, amount, currency, credits, verified, raw, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)')
      .run('paypal', providerRef, eventId || null, user_id, 'credited', amount, currency, 100, 1, JSON.stringify(event), nowISO(), nowISO());
    db.prepare('INSERT INTO payments (user_id, source, amount_usd, credits, raw, created_at) VALUES (?, ?, ?, ?, ?, ?)')
      .run(user_id, 'paypal_verified', amount, 100, JSON.stringify(event), nowISO());
    logEvent('purchase_verified', user_id, { provider_ref: providerRef, amount, currency, credits: 100 });

    return res.json({ ok: true, user_id, credited: 100, credits: availableCredits(row), provider_ref: providerRef });
  } catch (e) {
    return res.status(500).json({ ok: false, error: 'paypal_webhook_error', message: String(e?.message || e) });
  }
});

app.post('/api/unlock/local', (req, res) => {
  const auth = req.headers['authorization'] || '';
  const token = auth.startsWith('Bearer ') ? auth.slice(7) : String(req.body?.admin_token || '');
  if (!ADMIN_TOKEN || token !== ADMIN_TOKEN) return res.status(401).json({ error: 'unauthorized' });

  const user_id = normalizeUser(req.body?.user_id);
  const credits = Math.max(0, Number(req.body?.credits || 100));
  const note = String(req.body?.note || '').slice(0, 500);
  if (!user_id) return res.status(400).json({ error: 'user_id is required' });

  const row = ensureUser(user_id);
  row.paid_credits += credits; row.updated_at = nowISO(); upsertUser.run(row);

  db.prepare('INSERT INTO payments (user_id, source, amount_usd, credits, raw, created_at) VALUES (?, ?, ?, ?, ?, ?)')
    .run(user_id, 'local_unlock', 0, credits, JSON.stringify(req.body || {}), nowISO());
  db.prepare('INSERT INTO grants (user_id, credits, note, created_at) VALUES (?, ?, ?, ?)')
    .run(user_id, credits, note, nowISO());
  logEvent('local_grant', user_id, { credits, note });

  return res.json({ ok: true, user_id, credited: credits, credits: availableCredits(row) });
});

app.get('/admin/stats', (req, res) => {
  if (!ADMIN_TOKEN || String(req.query.token || '') !== ADMIN_TOKEN) return res.status(401).json({ error: 'unauthorized' });

  const dauToday = db.prepare("SELECT COUNT(DISTINCT user_id) as n FROM events WHERE date(created_at)=date('now') AND user_id IS NOT NULL AND user_id <> ''").get().n || 0;
  const usesToday = db.prepare("SELECT COUNT(*) as n FROM events WHERE type='use' AND date(created_at)=date('now')").get().n || 0;
  const purchasesTotal = db.prepare("SELECT COUNT(*) as n FROM purchases WHERE status='credited'").get().n || 0;
  const purchasesToday = db.prepare("SELECT COUNT(*) as n FROM purchases WHERE status='credited' AND date(created_at)=date('now')").get().n || 0;
  const localGrantsTotal = db.prepare("SELECT COUNT(*) as n FROM grants").get().n || 0;
  const localGrantsToday = db.prepare("SELECT COUNT(*) as n FROM grants WHERE date(created_at)=date('now')").get().n || 0;

  return res.json({
    dau_today: dauToday,
    uses_today: usesToday,
    purchases: { total: purchasesTotal, today: purchasesToday },
    local_grants: { total: localGrantsTotal, today: localGrantsToday }
  });
});

app.listen(PORT, () => console.log(`micro-saas running on :${PORT}`));
