import Link from "next/link";
import { FolderGit2, Settings } from "lucide-react";

async function getProject(projectId: string) {
  try {
    const res = await fetch(`http://127.0.0.1:8000/api/v1/projects/${projectId}`, { cache: 'no-store' });
    if (!res.ok) return null;
    return res.json();
  } catch (error) {
    return null;
  }
}

export default async function ProjectLayout(props: {
  children: React.ReactNode;
  params: Promise<{ project_id: string }>;
}) {
  const { children } = props;
  const params = await props.params;
  const project = await getProject(params.project_id);

  if (!project) {
    return (
      <div className="flex flex-1 items-center justify-center p-8 text-zinc-400">
        Project not found or failed to load.
      </div>
    );
  }

  const tabs = [
    { name: 'Knowledge', href: `/projects/${project.project_id}/knowledge` },
    { name: 'Test Cases', href: `/projects/${project.project_id}/test-cases` },
    { name: 'Scans', href: `/projects/${project.project_id}/scans` },
    { name: 'Comparisons', href: `/projects/${project.project_id}/comparisons` },
    { name: 'Executions', href: `/projects/${project.project_id}/executions` },
  ];

  return (
    <div className="flex flex-col min-h-full">
      {/* Project Header */}
      <div className="bg-zinc-950 border-b border-zinc-800 pt-8 px-8">
        <div className="flex items-center justify-between pb-4">
          <div className="flex items-center gap-3">
            <div className="flex items-center justify-center h-10 w-10 rounded-lg bg-zinc-800 border border-zinc-700">
              <FolderGit2 className="h-5 w-5 text-blue-400" />
            </div>
            <div>
              <h1 className="text-2xl font-bold text-zinc-100">{project.name}</h1>
              <p className="text-sm text-zinc-400">{project.primary_url || "No URL provided"}</p>
            </div>
          </div>
          <div>
            <Link href={`/projects/${project.project_id}/settings`} className="inline-flex items-center justify-center rounded-md text-sm font-medium transition-colors border border-zinc-800 bg-zinc-900 text-zinc-300 hover:bg-zinc-800 h-9 px-4 py-2">
              <Settings className="mr-2 h-4 w-4" />
              Settings
            </Link>
          </div>
        </div>

        {/* Tabs */}
        <div className="flex overflow-x-auto mt-4 hide-scrollbar">
          <nav className="flex space-x-1" aria-label="Tabs">
            {tabs.map((tab) => (
              <Link
                key={tab.name}
                href={tab.href}
                className="whitespace-nowrap py-3 px-4 text-sm font-medium text-zinc-400 hover:text-zinc-200 border-b-2 border-transparent hover:border-zinc-700 transition-colors"
              >
                {tab.name}
              </Link>
            ))}
          </nav>
        </div>
      </div>

      {/* Content Area */}
      <div className="flex-1 p-8">
        {children}
      </div>
    </div>
  );
}
