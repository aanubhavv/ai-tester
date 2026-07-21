import Link from "next/link";
import { Plus, Play, BrainCircuit, Activity, CheckCircle2, Clock } from "lucide-react";
import QuickScanButton from "./QuickScanButton";

async function getProjects() {
  try {
    const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000'}/api/v1/projects/`, { cache: 'no-store' });
    if (!res.ok) return { projects: [], total: 0 };
    return res.json();
  } catch (error) {
    console.error("Failed to fetch projects:", error);
    return { projects: [], total: 0 };
  }
}

async function getScans() {
  try {
    const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000'}/api/v1/scans/`, { cache: 'no-store' });
    if (!res.ok) return { scans: [], total: 0 };
    const data = await res.json();
    return { scans: Array.isArray(data) ? data : [], total: Array.isArray(data) ? data.length : 0 };
  } catch (error) {
    console.error("Failed to fetch scans:", error);
    return { scans: [], total: 0 };
  }
}

export default async function Dashboard() {
  const { projects } = await getProjects();
  const { scans } = await getScans();

  return (
    <div className="flex flex-col flex-1 p-8">
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-3xl font-bold tracking-tight text-zinc-100">Overview</h1>
          <p className="text-zinc-400 mt-1">Welcome back. Here's what's happening across your projects.</p>
        </div>
        <div className="flex items-center gap-3">
          <Link href="/projects?create=true" className="inline-flex items-center justify-center rounded-md text-sm font-medium transition-colors bg-blue-600 text-white hover:bg-blue-700 h-10 px-4 py-2">
            <Plus className="mr-2 h-4 w-4" />
            New Project
          </Link>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
        <div className="rounded-xl border border-zinc-800 bg-zinc-900/50 p-6 shadow-sm">
          <div className="flex items-center text-sm font-medium text-zinc-400 mb-2">
            <Activity className="mr-2 h-4 w-4 text-blue-500" />
            Total Projects
          </div>
          <div className="text-3xl font-bold text-zinc-100">{projects.length}</div>
        </div>
        <div className="rounded-xl border border-zinc-800 bg-zinc-900/50 p-6 shadow-sm">
          <div className="flex items-center text-sm font-medium text-zinc-400 mb-2">
            <Play className="mr-2 h-4 w-4 text-emerald-500" />
            Total Executions
          </div>
          <div className="text-3xl font-bold text-zinc-100">{scans.length}</div>
        </div>
        <div className="rounded-xl border border-zinc-800 bg-zinc-900/50 p-6 shadow-sm">
          <div className="flex items-center text-sm font-medium text-zinc-400 mb-2">
            <CheckCircle2 className="mr-2 h-4 w-4 text-purple-500" />
            System Health
          </div>
          <div className="text-3xl font-bold text-zinc-100">Healthy</div>
        </div>
        <div className="rounded-xl border border-zinc-800 bg-zinc-900/50 p-6 shadow-sm">
          <div className="flex items-center text-sm font-medium text-zinc-400 mb-2">
            <BrainCircuit className="mr-2 h-4 w-4 text-amber-500" />
            AI Operations
          </div>
          <div className="text-3xl font-bold text-zinc-100">Active</div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        <div className="lg:col-span-2 space-y-6">
          <div className="rounded-xl border border-zinc-800 bg-zinc-950 shadow-sm overflow-hidden">
            <div className="px-6 py-5 border-b border-zinc-800 flex items-center justify-between">
              <h2 className="text-lg font-semibold text-zinc-100">Active Projects</h2>
              <Link href="/projects" className="text-sm font-medium text-blue-500 hover:text-blue-400">View all</Link>
            </div>
            <div className="divide-y divide-zinc-800">
              {projects.length === 0 ? (
                <div className="p-8 text-center text-zinc-500 text-sm">No projects found. Create one to get started.</div>
              ) : (
                projects.map((project: any) => (
                  <Link href={`/projects/${project.project_id}`} key={project.project_id} className="flex items-center justify-between p-6 hover:bg-zinc-900/50 transition-colors">
                    <div>
                      <h3 className="text-base font-medium text-zinc-200">{project.name}</h3>
                      <p className="text-sm text-zinc-500 mt-1">{project.description || 'No description provided'}</p>
                    </div>
                    <div className="flex items-center gap-4 text-sm text-zinc-400">
                      <span className="flex items-center">
                        <Clock className="mr-1 h-3 w-3" />
                        {new Date(project.created_at).toLocaleDateString()}
                      </span>
                    </div>
                  </Link>
                ))
              )}
            </div>
          </div>
        </div>

        <div className="space-y-6">
          <div className="rounded-xl border border-zinc-800 bg-zinc-950 shadow-sm overflow-hidden">
            <div className="px-6 py-5 border-b border-zinc-800">
              <h2 className="text-lg font-semibold text-zinc-100">Quick Actions</h2>
            </div>
            <div className="p-4 space-y-2">
              <Link href="/projects?create=true" className="flex items-center w-full p-3 text-sm font-medium text-zinc-300 rounded-lg hover:bg-zinc-900 transition-colors">
                <Plus className="mr-3 h-4 w-4 text-blue-400" />
                Create New Project
              </Link>
              <QuickScanButton />
              <Link href="/ai-planning" className="flex items-center w-full p-3 text-sm font-medium text-zinc-300 rounded-lg hover:bg-zinc-900 transition-colors">
                <BrainCircuit className="mr-3 h-4 w-4 text-purple-400" />
                Generate AI Planning
              </Link>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
