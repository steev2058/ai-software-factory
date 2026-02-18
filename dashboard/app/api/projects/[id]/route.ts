export const dynamic = 'force-dynamic';
import { NextResponse } from 'next/server';
import { getProjectDetails } from '../../../../lib/projects';

export async function GET(_: Request, { params }: { params: { id: string } }) {
  return NextResponse.json(getProjectDetails(params.id));
}
