export const dynamic = 'force-dynamic';
import fs from 'fs';
import path from 'path';
import { NextRequest, NextResponse } from 'next/server';
import { getProjectDetails, PROJECTS_ROOT } from '../../../../lib/projects';
import { isValidProjectId, requireBasicAuth } from '../../../../lib/auth';

export async function GET(req: NextRequest, { params }: { params: { id: string } }) {
  const auth = requireBasicAuth(req);
  if (!auth.ok) return auth.response;
  if (!isValidProjectId(params.id)) return new NextResponse('Invalid project id', { status: 400 });
  return NextResponse.json(getProjectDetails(params.id));
}

export async function DELETE(req: NextRequest, { params }: { params: { id: string } }) {
  const auth = requireBasicAuth(req);
  if (!auth.ok) return auth.response;
  if (!isValidProjectId(params.id)) return new NextResponse('Invalid project id', { status: 400 });

  const projectPath = path.join(PROJECTS_ROOT, params.id);
  if (!fs.existsSync(projectPath)) return new NextResponse('Project not found', { status: 404 });

  fs.rmSync(projectPath, { recursive: true, force: true });
  return NextResponse.json({ status: 'deleted', id: params.id });
}
