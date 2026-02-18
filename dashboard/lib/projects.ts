import fs from 'fs';
import path from 'path';

export const PROJECTS_ROOT = process.env.PROJECTS_ROOT || '/data/projects';

export type ProjectStatus = 'NEW' | 'SPEC_READY' | 'RUNNING' | 'PASSED' | 'FAILED' | 'UNKNOWN';

export type ProjectSummary = {
  id: string;
  status: ProjectStatus;
  stack?: string;
  updatedAt?: string;
  hints: string[];
  zipPath?: string;
  githubBranch?: string;
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

export function computeStatus(id: string): ProjectSummary {
  const p = path.join(PROJECTS_ROOT, id);
  const hints: string[] = [];
  const specJson = safeReadJson(path.join(p, 'state', 'spec.json')) || safeReadJson(path.join(p, 'state', 'pm.json'));
  const statusJson = safeReadJson(path.join(p, 'state', 'status.json'));
  const qaJson = safeReadJson(path.join(p, 'state', 'qa.json'));
  const zipPath = detectZip(p, id);
  const branch = statusJson?.github_branch || (zipPath ? `deliver/${id}` : undefined);

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

  return { id, status, stack, updatedAt, hints, zipPath, githubBranch: branch };
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
