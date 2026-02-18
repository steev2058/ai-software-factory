'use client';

export default function ProjectMetaCard({ project }: { project: any }) {
  const github = project.githubBranch ? `https://github.com/steev2058/ai-software-factory/tree/${project.githubBranch}` : null;
  return (
    <div className="bg-white border rounded p-4 space-y-2">
      <h2 className="font-semibold">{project.id}</h2>
      <div>Status: {project.status}</div>
      <div>Progress: {project.progress ?? 0}%</div>
      <div className="h-2 w-full bg-slate-200 rounded overflow-hidden">
        <div className="h-2 bg-blue-600" style={{ width: `${Math.max(0, Math.min(100, project.progress || 0))}%` }} />
      </div>
      <div>ETA: {project.eta || '-'}</div>
      <div>Stack: {project.stack || '-'}</div>
      <div>Updated: {project.updatedAt || '-'}</div>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-sm">
        <div>
          <div className="font-medium mb-1">Done</div>
          <ul className="list-disc pl-5 space-y-1">
            {(project.done || []).slice(0, 8).map((x: string) => <li key={x}>{x}</li>)}
            {(!project.done || !project.done.length) && <li>-</li>}
          </ul>
        </div>
        <div>
          <div className="font-medium mb-1">Pending</div>
          <ul className="list-disc pl-5 space-y-1">
            {(project.pending || []).slice(0, 8).map((x: string) => <li key={x}>{x}</li>)}
            {(!project.pending || !project.pending.length) && <li>-</li>}
          </ul>
        </div>
      </div>
      {github && (
        <div className="flex gap-2 items-center">
          <a className="text-blue-600 underline" href={github} target="_blank">GitHub Branch</a>
          <button className="text-xs border px-2 py-1 rounded" onClick={() => navigator.clipboard.writeText(github)}>Copy GitHub link</button>
        </div>
      )}
      {project.zipPath && (
        <div className="text-sm space-x-2">
          <span>ZIP: <code>{project.zipPath}</code></span>
          <a className="text-blue-600 underline" href={`/api/projects/${project.id}/zip`}>Download ZIP</a>
        </div>
      )}
    </div>
  );
}
