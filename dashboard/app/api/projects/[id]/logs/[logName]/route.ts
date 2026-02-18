export const dynamic = 'force-dynamic';
import fs from 'fs';
import path from 'path';
import { NextRequest, NextResponse } from 'next/server';
import { PROJECTS_ROOT } from '../../../../../../lib/projects';
import { isValidProjectId, requireBasicAuth } from '../../../../../../lib/auth';

export async function GET(req: NextRequest, { params }: { params: { id: string; logName: string } }) {
  const auth = requireBasicAuth(req);
  if (!auth.ok) return auth.response;
  if (!isValidProjectId(params.id)) return new NextResponse('Invalid project id', { status: 400 });
  const safeName = params.logName.replace(/\//g, '');
  const p = path.join(PROJECTS_ROOT, params.id, 'logs', safeName);
  if (!fs.existsSync(p)) return new NextResponse('Not found', { status: 404 });
  const content = fs.readFileSync(p, 'utf-8');
  return new NextResponse(content, { headers: { 'content-type': 'text/plain; charset=utf-8' } });
}
