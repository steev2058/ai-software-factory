export const dynamic = 'force-dynamic';
import { NextRequest, NextResponse } from 'next/server';
import { listLogs } from '../../../../../lib/projects';
import { isValidProjectId, requireBasicAuth } from '../../../../../lib/auth';

export async function GET(req: NextRequest, { params }: { params: { id: string } }) {
  const auth = requireBasicAuth(req);
  if (!auth.ok) return auth.response;
  if (!isValidProjectId(params.id)) return new NextResponse('Invalid project id', { status: 400 });
  return NextResponse.json({ logs: listLogs(params.id) });
}
