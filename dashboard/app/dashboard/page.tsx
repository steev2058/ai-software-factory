'use client';

import { useEffect, useMemo, useState } from 'react';
import ProjectTable from '../../components/ProjectTable';

export default function DashboardPage() {
  const [projects, setProjects] = useState<any[]>([]);
  const [q, setQ] = useState('');
  const [status, setStatus] = useState('ALL');

  const load = async () => {
    const res = await fetch('/api/projects', { cache: 'no-store' });
    const data = await res.json();
    setProjects(data.projects || []);
  };

  useEffect(() => {
    load();
    const t = setInterval(load, 8000);
    return () => clearInterval(t);
  }, []);

  const filtered = useMemo(() => projects.filter((p) => {
    const qq = q.toLowerCase();
    const hit = !qq || p.id.toLowerCase().includes(qq) || (p.stack || '').toLowerCase().includes(qq);
    const statusOk = status === 'ALL' || p.status === status;
    return hit && statusOk;
  }), [projects, q, status]);

  return (
    <main className="p-4 space-y-4">
      <div className="flex gap-2">
        <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Search project_id or stack" className="border rounded px-3 py-2 w-80" />
        <select value={status} onChange={(e) => setStatus(e.target.value)} className="border rounded px-3 py-2">
          {['ALL','NEW','SPEC_READY','RUNNING','PASSED','FAILED','UNKNOWN'].map((s)=><option key={s}>{s}</option>)}
        </select>
        <button onClick={load} className="border px-3 py-2 rounded bg-white">Refresh</button>
      </div>
      <ProjectTable projects={filtered} />
    </main>
  );
}
