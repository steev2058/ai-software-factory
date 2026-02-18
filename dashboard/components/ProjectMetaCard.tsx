'use client';

export default function ProjectMetaCard({ project }: { project: any }) {
  const github = project.githubBranch ? `https://github.com/steev2058/ai-software-factory/tree/${project.githubBranch}` : null;
  return (
    <div className="bg-white border rounded p-4 space-y-2">
      <h2 className="font-semibold">{project.id}</h2>
      <div>Status: {project.status}</div>
      <div>Stack: {project.stack || '-'}</div>
      <div>Updated: {project.updatedAt || '-'}</div>
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
