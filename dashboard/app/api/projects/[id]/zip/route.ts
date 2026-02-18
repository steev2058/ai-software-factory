export const dynamic = 'force-dynamic';
import fs from 'fs';
import path from 'path';
import { NextRequest } from 'next/server';
import { PROJECTS_ROOT } from '../../../../../lib/projects';
import { isValidProjectId, requireBasicAuth } from '../../../../../lib/auth';

export async function GET(req: NextRequest, { params }: { params: { id: string } }) {
  const auth = requireBasicAuth(req);
  if (!auth.ok) return auth.response;
  if (!isValidProjectId(params.id)) return new Response('Invalid project id', { status: 400 });

  const p1 = path.join(PROJECTS_ROOT, params.id, `${params.id}.zip`);
  const p2 = path.join(PROJECTS_ROOT, params.id, 'deliverables');
  let zipPath = p1;
  if (!fs.existsSync(zipPath) && fs.existsSync(p2)) {
    const z = fs.readdirSync(p2).find((f) => f.endsWith('.zip'));
    if (z) zipPath = path.join(p2, z);
  }
  if (!fs.existsSync(zipPath)) return new Response('ZIP not found', { status: 404 });

  const data = fs.readFileSync(zipPath);
  return new Response(data, {
    headers: {
      'content-type': 'application/zip',
      'content-disposition': `attachment; filename="${params.id}.zip"`
    }
  });
}
