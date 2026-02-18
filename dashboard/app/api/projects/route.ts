export const dynamic = 'force-dynamic';
import { NextResponse } from 'next/server';
import { computeStatus, listProjects } from '../../../lib/projects';

export async function GET() {
  const projects = listProjects().map(computeStatus).sort((a,b)=> (b.updatedAt || '').localeCompare(a.updatedAt || ''));
  return NextResponse.json({ projects });
}
