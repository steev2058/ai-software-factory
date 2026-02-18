'use client';
import Link from 'next/link';
import StatusBadge from './StatusBadge';

export default function ProjectTable({ projects }: { projects: any[] }) {
  return (
    <div className="bg-white border rounded overflow-auto">
      <table className="w-full text-sm">
        <thead className="bg-slate-100 text-left">
          <tr><th className="p-2">Project</th><th>Status</th><th>Stack</th><th>Updated</th></tr>
        </thead>
        <tbody>
          {projects.map((p) => (
            <tr key={p.id} className="border-t hover:bg-slate-50">
              <td className="p-2"><Link className="text-blue-600" href={`/projects/${p.id}`}>{p.id}</Link></td>
              <td><StatusBadge status={p.status} /></td>
              <td>{p.stack || '-'}</td>
              <td>{p.updatedAt || '-'}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
