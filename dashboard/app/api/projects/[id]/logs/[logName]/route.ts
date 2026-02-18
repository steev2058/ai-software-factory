export const dynamic = 'force-dynamic';
import fs from 'fs';
import path from 'path';
import { NextResponse } from 'next/server';
import { PROJECTS_ROOT } from '../../../../../../lib/projects';

export async function GET(_: Request, { params }: { params: { id: string; logName: string } }) {
  const safeName = params.logName.replace(/\//g, '');
  const p = path.join(PROJECTS_ROOT, params.id, 'logs', safeName);
  if (!fs.existsSync(p)) return new NextResponse('Not found', { status: 404 });
  const content = fs.readFileSync(p, 'utf-8');
  return new NextResponse(content, { headers: { 'content-type': 'text/plain; charset=utf-8' } });
}
