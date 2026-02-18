export const dynamic = 'force-dynamic';
import { NextRequest, NextResponse } from 'next/server';
import { computeStatus, listProjects } from '../../../lib/projects';
import { requireBasicAuth } from '../../../lib/auth';

export async function GET(req: NextRequest) {
  const auth = requireBasicAuth(req);
  if (!auth.ok) return auth.response;
  const projects = listProjects().map(computeStatus).sort((a,b)=> (b.updatedAt || '').localeCompare(a.updatedAt || ''));
  return NextResponse.json({ projects });
}
