export const dynamic = 'force-dynamic';
import { NextResponse } from 'next/server';
import { listLogs } from '../../../../../lib/projects';

export async function GET(_: Request, { params }: { params: { id: string } }) {
  return NextResponse.json({ logs: listLogs(params.id) });
}
