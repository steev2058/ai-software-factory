import { NextRequest, NextResponse } from 'next/server';

function unauthorized() {
  return new NextResponse('Authentication required', {
    status: 401,
    headers: {
      'WWW-Authenticate': 'Basic realm="Factory Dashboard"'
    }
  });
}

export function middleware(req: NextRequest) {
  const user = process.env.DASHBOARD_USER;
  const pass = process.env.DASHBOARD_PASS;

  if (!user || !pass) return unauthorized();

  const auth = req.headers.get('authorization');
  if (!auth?.startsWith('Basic ')) return unauthorized();

  try {
    const encoded = auth.split(' ')[1] || '';
    const decoded = atob(encoded);
    const [u, ...rest] = decoded.split(':');
    const p = rest.join(':');

    if (u === user && p === pass) return NextResponse.next();
    return unauthorized();
  } catch {
    return unauthorized();
  }
}

export const config = {
  matcher: ['/((?!_next/static|_next/image|favicon.ico).*)']
};
