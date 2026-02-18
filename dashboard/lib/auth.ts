import { NextRequest } from 'next/server';

export function isValidProjectId(id: string): boolean {
  return /^[A-Za-z0-9_-]+$/.test(id);
}

export function requireBasicAuth(req: NextRequest): { ok: true } | { ok: false; response: Response } {
  const user = process.env.DASHBOARD_USER;
  const pass = process.env.DASHBOARD_PASS;

  if (!user || !pass) {
    return {
      ok: false,
      response: new Response('Server auth is not configured', { status: 500 })
    };
  }

  const auth = req.headers.get('authorization');
  if (!auth?.startsWith('Basic ')) {
    return {
      ok: false,
      response: new Response('Authentication required', {
        status: 401,
        headers: { 'WWW-Authenticate': 'Basic realm="Factory Dashboard"' }
      })
    };
  }

  try {
    const raw = Buffer.from(auth.split(' ')[1] || '', 'base64').toString('utf-8');
    const [u, ...rest] = raw.split(':');
    const p = rest.join(':');
    if (u === user && p === pass) return { ok: true };
    return {
      ok: false,
      response: new Response('Invalid credentials', {
        status: 401,
        headers: { 'WWW-Authenticate': 'Basic realm="Factory Dashboard"' }
      })
    };
  } catch {
    return {
      ok: false,
      response: new Response('Invalid authorization header', { status: 401 })
    };
  }
}
