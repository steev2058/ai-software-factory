'use client';
import Link from 'next/link';
import { useMemo, useState } from 'react';
import StatusBadge from './StatusBadge';
import ConfirmModal from './ConfirmModal';

export default function ProjectTable({ projects, onRefresh }: { projects: any[]; onRefresh?: () => void }) {
  const [loadingAction, setLoadingAction] = useState<Record<string, string>>({});
  const [overrideStatus, setOverrideStatus] = useState<Record<string, string>>({});
  const [hidden, setHidden] = useState<Record<string, boolean>>({});
  const [error, setError] = useState<string>('');
  const [deleteId, setDeleteId] = useState<string>('');

  const shownProjects = useMemo(
    () => projects.filter((p) => !hidden[p.id]).map((p) => ({ ...p, status: overrideStatus[p.id] || p.status })),
    [projects, hidden, overrideStatus]
  );

  const call = async (id: string, action: 'run' | 'rerun' | 'delete') => {
    setError('');
    setLoadingAction((s) => ({ ...s, [id]: action }));

    try {
      const method = action === 'delete' ? 'DELETE' : 'POST';
      const route = action === 'delete' ? `/api/projects/${id}` : `/api/projects/${id}/${action}`;
      const resp = await fetch(route, { method });
      const payload = await resp.json().catch(() => ({}));
      if (!resp.ok) {
        const text = payload?.message || payload?.error || `Request failed: ${resp.status}`;
        throw new Error(text);
      }

      if (action === 'delete') {
        setHidden((s) => ({ ...s, [id]: true }));
      } else {
        setOverrideStatus((s) => ({ ...s, [id]: 'RUNNING' }));
        if (payload?.warning) setError(`Warning: ${payload.warning}`);
      }

      onRefresh?.();
    } catch (e: any) {
      setError(e?.message || 'Action failed');
    } finally {
      setLoadingAction((s) => ({ ...s, [id]: '' }));
    }
  };

  return (
    <>
      {error && <div className="bg-red-100 border border-red-200 text-red-800 px-3 py-2 rounded mb-2 text-sm">{error}</div>}
      <div className="bg-white border rounded overflow-auto">
        <table className="w-full text-sm">
          <thead className="bg-slate-100 text-left">
            <tr>
              <th className="p-2">Project</th>
              <th>Status</th>
              <th>Progress</th>
              <th>ETA</th>
              <th>Stack</th>
              <th>Updated</th>
              <th className="p-2">Actions</th>
            </tr>
          </thead>
          <tbody>
            {shownProjects.map((p) => {
              const busy = Boolean(loadingAction[p.id]);
              return (
                <tr key={p.id} className="border-t hover:bg-slate-50">
                  <td className="p-2"><Link className="text-blue-600" href={`/projects/${p.id}`}>{p.id}</Link></td>
                  <td><StatusBadge status={p.status} /></td>
                  <td className="min-w-[180px] pr-2">
                    <div className="h-2 w-full bg-slate-200 rounded overflow-hidden">
                      <div className="h-2 bg-blue-600" style={{ width: `${Math.max(0, Math.min(100, p.progress || 0))}%` }} />
                    </div>
                    <div className="text-xs text-slate-600 mt-1">{p.progress ?? 0}%</div>
                  </td>
                  <td className="text-xs text-slate-700">{p.eta || '-'}</td>
                  <td>{p.stack || '-'}</td>
                  <td>{p.updatedAt || '-'}</td>
                  <td className="p-2 space-x-1">
                    <button disabled={busy} className="border rounded px-2 py-1 disabled:opacity-50" onClick={() => call(p.id, 'run')}>▶️ Run</button>
                    <button disabled={busy} className="border rounded px-2 py-1 disabled:opacity-50" onClick={() => call(p.id, 'rerun')}>🔁 Re-run</button>
                    <button disabled={busy} className="border rounded px-2 py-1 text-red-700 disabled:opacity-50" onClick={() => setDeleteId(p.id)}>🗑 Delete</button>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      <ConfirmModal
        open={Boolean(deleteId)}
        title="Delete project"
        message={deleteId ? `Are you sure you want to delete ${deleteId}? This cannot be undone.` : ''}
        loading={Boolean(deleteId && loadingAction[deleteId])}
        onCancel={() => setDeleteId('')}
        onConfirm={async () => {
          if (!deleteId) return;
          await call(deleteId, 'delete');
          setDeleteId('');
        }}
      />
    </>
  );
}
