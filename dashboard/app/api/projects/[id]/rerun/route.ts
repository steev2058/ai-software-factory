export const dynamic = 'force-dynamic';
import fs from 'fs';
import path from 'path';
import { NextRequest, NextResponse } from 'next/server';
import { PROJECTS_ROOT } from '../../../../../lib/projects';
import { isValidProjectId, requireBasicAuth } from '../../../../../lib/auth';

function rmIfExists(p: string) {
  if (fs.existsSync(p)) fs.rmSync(p, { recursive: true, force: true });
}

export async function POST(req: NextRequest, { params }: { params: { id: string } }) {
  const auth = requireBasicAuth(req);
  if (!auth.ok) return auth.response;

  const id = params.id;
  if (!isValidProjectId(id)) return new NextResponse('Invalid project id', { status: 400 });

  const projectPath = path.join(PROJECTS_ROOT, id);
  if (!fs.existsSync(projectPath)) return new NextResponse('Project not found', { status: 404 });

  rmIfExists(path.join(projectPath, 'repo'));
  rmIfExists(path.join(projectPath, 'logs'));
  fs.mkdirSync(path.join(projectPath, 'repo'), { recursive: true });
  fs.mkdirSync(path.join(projectPath, 'logs'), { recursive: true });
  fs.mkdirSync(path.join(projectPath, 'state'), { recursive: true });
  fs.mkdirSync(path.join(projectPath, 'tasks'), { recursive: true });
  [projectPath, 'state', 'logs', 'repo', 'tasks'].forEach((x) => {
    const p = x === projectPath ? projectPath : path.join(projectPath, x);
    try { fs.chmodSync(p, 0o777); } catch {}
  });

  const statusPath = path.join(projectPath, 'state', 'status.json');
  fs.writeFileSync(
    statusPath,
    JSON.stringify({ phase: 'RUNNING', running: true, rerun: true, updated_at: new Date().toISOString() }, null, 2)
  );
  try { fs.chmodSync(statusPath, 0o666); } catch {}

  const webhook = process.env.N8N_WEBHOOK_URL || 'http://asf-n8n:5678/webhook/run-project';

  try {
    const resp = await fetch(webhook, {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify({ project_id: id })
    });

    if (!resp.ok) {
      return NextResponse.json({ status: 'started', mode: 'rerun', warning: 'n8n webhook returned non-200', code: resp.status, id });
    }

    return NextResponse.json({ status: 'started', mode: 'rerun', id });
  } catch (e: any) {
    return NextResponse.json({ status: 'started', mode: 'rerun', warning: 'n8n unreachable', error: String(e?.message || e), id });
  }
}
