'use client';

import { useEffect, useState } from 'react';
import { useParams } from 'next/navigation';
import ProjectMetaCard from '../../../components/ProjectMetaCard';
import LogViewer from '../../../components/LogViewer';

export default function ProjectDetailsPage() {
  const params = useParams<{ id: string }>();
  const id = params.id;
  const [project, setProject] = useState<any>(null);
  const [logs, setLogs] = useState<string[]>([]);
  const [selectedLog, setSelectedLog] = useState<string>('');
  const [logContent, setLogContent] = useState('');

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

  if (!project) return <main className="p-4">Loading...</main>;

  return (
    <main className="p-4 grid grid-cols-1 lg:grid-cols-3 gap-4">
      <div className="space-y-4">
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
