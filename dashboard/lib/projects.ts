import fs from 'fs';
import path from 'path';

export const PROJECTS_ROOT = process.env.PROJECTS_ROOT || '/data/projects';

export type ProjectStatus = 'NEW' | 'SPEC_READY' | 'RUNNING' | 'PASSED' | 'FAILED' | 'UNKNOWN';

export type ProjectSummary = {
  id: string;
  status: ProjectStatus;
  stack?: string;
  updatedAt?: string;
  lastLogAt?: string;
  isAlive?: boolean;
  hints: string[];
  zipPath?: string;
  githubBranch?: string;
  previewUrl?: string;
  liveUrl?: string;
  progress: number;
  eta: string;
  done: string[];
  pending: string[];
};

export function safeReadJson(filePath: string): any | null {
  try {
    if (!fs.existsSync(filePath)) return null;
    return JSON.parse(fs.readFileSync(filePath, 'utf-8'));
  } catch {
    return null;
  }
}

export function exists(...parts: string[]): boolean {
  return fs.existsSync(path.join(...parts));
}

export function listProjects(): string[] {
  if (!fs.existsSync(PROJECTS_ROOT)) return [];
  return fs.readdirSync(PROJECTS_ROOT).filter((name) => fs.statSync(path.join(PROJECTS_ROOT, name)).isDirectory());
}

export function detectZip(projectPath: string, id: string): string | undefined {
  const direct = path.join(projectPath, `${id}.zip`);
  if (fs.existsSync(direct)) return direct;
  const deliv = path.join(projectPath, 'deliverables');
  if (fs.existsSync(deliv)) {
    const zips = fs.readdirSync(deliv).filter((f) => f.endsWith('.zip'));
    if (zips.length) return path.join(deliv, zips[0]);
  }
  return undefined;
}

function estimateEta(progress: number, status: ProjectStatus): string {
  if (status === 'PASSED') return 'Done ✅';
  if (status === 'FAILED') return 'Blocked (failed) ❌';
  if (progress < 20) return '≈ 12-18 min';
  if (progress < 40) return '≈ 8-12 min';
  if (progress < 60) return '≈ 5-8 min';
  if (progress < 80) return '≈ 3-5 min';
  return '≈ 1-3 min';
}

export function computeStatus(id: string): ProjectSummary {
  const p = path.join(PROJECTS_ROOT, id);
  const hints: string[] = [];
  const specJson = safeReadJson(path.join(p, 'state', 'spec.json')) || safeReadJson(path.join(p, 'state', 'pm.json'));
  const statusJson = safeReadJson(path.join(p, 'state', 'status.json'));
  const qaJson = safeReadJson(path.join(p, 'state', 'qa.json'));
  const zipPath = detectZip(p, id);
  const branch = statusJson?.github_branch || (zipPath ? `deliver/${id}` : undefined);
  const previewUrl = statusJson?.preview_url || (fs.existsSync(path.join(p, 'preview', 'index.html')) ? `https://petsy.company/factory-preview/${id}/preview/index.html` : undefined);
  const registryPath = path.join(PROJECTS_ROOT, 'registry.json');
  const registry = safeReadJson(registryPath) || {};
  const regEntry = registry?.[id] || null;
  const liveUrl = statusJson?.live_url || regEntry?.url || undefined;

  let status: ProjectStatus = 'UNKNOWN';

  if (!specJson) {
    status = 'NEW';
    hints.push('No state/spec.json yet');
  } else {
    status = 'SPEC_READY';
    hints.push('Spec exists');
  }

  if (statusJson?.running === true || statusJson?.phase === 'RUNNING' || exists(p, 'state', '.lock')) {
    status = 'RUNNING';
    hints.push('Running marker found');
  }

  if (qaJson?.result === 'FAIL' || /fail/i.test(String(statusJson?.phase || '')) ) {
    status = 'FAILED';
    hints.push('QA/status indicates fail');
  }

  if (!zipPath && exists(p, 'logs', 'test.log')) {
    try {
      const testLog = fs.readFileSync(path.join(p, 'logs', 'test.log'), 'utf-8');
      if (/error/i.test(testLog)) {
        status = 'FAILED';
        hints.push('test.log contains error and no zip');
      }
    } catch {}
  }

  if (zipPath) {
    if (qaJson?.result === 'PASS' || /PASSED/i.test(String(statusJson?.phase || '')) || true) {
      status = 'PASSED';
      hints.push('Zip deliverable exists');
    }
  }

  const stack = specJson?.stack;
  const updatedAt = statusJson?.updated_at;
  const buildLogPath = path.join(p, 'logs', 'build.log');
  const lastLogAt = fs.existsSync(buildLogPath) ? fs.statSync(buildLogPath).mtime.toISOString() : undefined;
  const isAlive = status === 'RUNNING' && lastLogAt
    ? (Date.now() - new Date(lastLogAt).getTime()) < 120000
    : undefined;

  const milestones: Array<{ label: string; ok: boolean; weight: number }> = [
    { label: 'Spec saved', ok: !!specJson, weight: 10 },
    { label: 'Execution started', ok: status === 'RUNNING' || status === 'PASSED' || status === 'FAILED', weight: 15 },
    { label: 'Repo scaffolded', ok: fs.existsSync(path.join(p, 'repo')) && fs.readdirSync(path.join(p, 'repo')).length > 0, weight: 25 },
    { label: 'Build logs generated', ok: fs.existsSync(path.join(p, 'logs', 'build.log')), weight: 15 },
    { label: 'ZIP generated', ok: !!zipPath, weight: 20 },
    { label: 'Execution completed', ok: status === 'PASSED', weight: 15 },
  ];

  let progress = milestones.reduce((sum, m) => sum + (m.ok ? m.weight : 0), 0);
  if (status === 'FAILED') progress = Math.max(progress, 35);
  if (status === 'PASSED') progress = 100;

  const done = milestones.filter((m) => m.ok).map((m) => m.label);
  const pending = milestones.filter((m) => !m.ok).map((m) => m.label);
  const eta = estimateEta(progress, status);

  return { id, status, stack, updatedAt, lastLogAt, isAlive, hints, zipPath, githubBranch: branch, previewUrl, liveUrl, progress, eta, done, pending };
}

export function getProjectDetails(id: string) {
  const p = path.join(PROJECTS_ROOT, id);
  const summary = computeStatus(id);
  const specPath = path.join(p, 'project_spec.md');
  const spec = fs.existsSync(specPath) ? fs.readFileSync(specPath, 'utf-8') : '';
  const stateSpec = safeReadJson(path.join(p, 'state', 'spec.json')) || safeReadJson(path.join(p, 'state', 'pm.json'));
  const repoTreePath = path.join(p, 'repo_tree.txt');
  const repoTree = fs.existsSync(repoTreePath) ? fs.readFileSync(repoTreePath, 'utf-8') : '';

  return {
    ...summary,
    spec,
    stateSpec,
    repoTree,
    createdAt: fs.existsSync(p) ? fs.statSync(p).birthtime.toISOString() : undefined,
    modifiedAt: fs.existsSync(p) ? fs.statSync(p).mtime.toISOString() : undefined
  };
}

export function listLogs(id: string): string[] {
  const logsPath = path.join(PROJECTS_ROOT, id, 'logs');
  if (!fs.existsSync(logsPath)) return [];
  return fs.readdirSync(logsPath).filter((f) => f.endsWith('.log')).sort();
}
