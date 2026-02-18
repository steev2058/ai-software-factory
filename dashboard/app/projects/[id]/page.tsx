'use client';

import { useEffect, useState } from 'react';
import { useParams, useRouter } from 'next/navigation';
import ProjectMetaCard from '../../../components/ProjectMetaCard';
import LogViewer from '../../../components/LogViewer';

export default function ProjectDetailsPage() {
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const id = params.id;
  const [project, setProject] = useState<any>(null);
  const [logs, setLogs] = useState<string[]>([]);
  const [selectedLog, setSelectedLog] = useState<string>('');
  const [logContent, setLogContent] = useState('');
  const [loading, setLoading] = useState<'run' | 'rerun' | 'delete' | ''>('');
  const [message, setMessage] = useState('');

  const loadAll = async () => {
    const [pRes, lRes] = await Promise.all([
      fetch(`/api/projects/${id}`, { cache: 'no-store' }),
      fetch(`/api/projects/${id}/logs`, { cache: 'no-store' })
    ]);
    const p = await pRes.json();
    const l = await lRes.json();
    setProject(p);
    setLogs(l.logs || []);
    if (!selectedLog && l.logs?.length) setSelectedLog(l.logs[0]);
  };

  useEffect(() => {
    loadAll();
    const t = setInterval(loadAll, 10000);
    return () => clearInterval(t);
  }, [id]);

  useEffect(() => {
    if (!selectedLog) return;
    fetch(`/api/projects/${id}/logs/${selectedLog}`, { cache: 'no-store' })
      .then((r) => r.text())
      .then(setLogContent)
      .catch(() => setLogContent('Failed to load log'));
  }, [id, selectedLog]);

  const doAction = async (action: 'run' | 'rerun' | 'delete') => {
    setMessage('');
    setLoading(action);
    try {
      if (action === 'delete') {
        if (!confirm(`Delete project ${id}? This cannot be undone.`)) {
          setLoading('');
          return;
        }
        const resp = await fetch(`/api/projects/${id}`, { method: 'DELETE' });
        const payload = await resp.json().catch(() => ({}));
        if (!resp.ok) throw new Error(payload?.message || payload?.error || 'Delete failed');
        router.push('/dashboard');
        return;
      }

      const resp = await fetch(`/api/projects/${id}/${action}`, { method: 'POST' });
      const payload = await resp.json().catch(() => ({}));
      if (!resp.ok) throw new Error(payload?.message || payload?.error || 'Action failed');
      setProject((p: any) => ({ ...p, status: 'RUNNING' }));
      if (payload?.warning) {
        setMessage(`Warning: ${payload.warning}`);
      } else {
        setMessage(action === 'run' ? 'Run started' : 'Re-run started');
      }
      await loadAll();
    } catch (e: any) {
      setMessage(`Action failed: ${e?.message || e}`);
    } finally {
      setLoading('');
    }
  };

  if (!project) return <main className="p-4">Loading...</main>;

  return (
    <main className="p-4 grid grid-cols-1 lg:grid-cols-3 gap-4">
      <div className="space-y-4">
        <div className="bg-white border rounded p-3 flex gap-2 flex-wrap">
          <button disabled={Boolean(loading)} onClick={() => doAction('run')} className="border rounded px-3 py-2 disabled:opacity-50">▶️ Run</button>
          <button disabled={Boolean(loading)} onClick={() => doAction('rerun')} className="border rounded px-3 py-2 disabled:opacity-50">🔁 Re-run</button>
          <button disabled={Boolean(loading)} onClick={() => doAction('delete')} className="border rounded px-3 py-2 text-red-700 disabled:opacity-50">🗑 Delete</button>
          {loading && <span className="text-sm text-slate-500">{loading}...</span>}
        </div>
        {message && <div className="text-sm bg-slate-100 border rounded px-3 py-2">{message}</div>}
        <ProjectMetaCard project={project} />
        <div className="bg-white border rounded p-4">
          <h3 className="font-semibold mb-2">Spec</h3>
          <pre className="text-xs whitespace-pre-wrap max-h-64 overflow-auto">{project.spec || 'No project_spec.md'}</pre>
        </div>
      </div>
      <div className="lg:col-span-2 bg-white border rounded p-4 space-y-2">
        <div className="flex gap-2 items-center">
          <strong>Logs</strong>
          <select value={selectedLog} onChange={(e)=>setSelectedLog(e.target.value)} className="border rounded px-2 py-1">
            <option value="">Select log</option>
            {logs.map((l) => <option key={l} value={l}>{l}</option>)}
          </select>
          <button onClick={loadAll} className="border rounded px-2 py-1">Refresh</button>
        </div>
        <LogViewer content={logContent} />
      </div>
    </main>
  );
}
