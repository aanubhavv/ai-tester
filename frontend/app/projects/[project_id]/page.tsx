import { Activity, ShieldAlert, Layers, CheckSquare, PlaySquare, GitCompare, ExternalLink, Calendar, GitPullRequest } from "lucide-react";

async function getProject(projectId: string) {
  try {
    const res = await fetch(`http://127.0.0.1:8000/api/v1/projects/${projectId}`, { cache: 'no-store' });
    if (!res.ok) return null;
    return res.json();
  } catch (error) {
    return null;
  }
}

async function getExecutions(projectId: string) {
  try {
    const res = await fetch(`http://127.0.0.1:8000/api/v1/projects/${projectId}/executions`, { cache: 'no-store' });
    if (!res.ok) return { executions: [], total: 0 };
    return res.json();
  } catch (error) {
    return { executions: [], total: 0 };
  }
}

async function getTestCases(projectId: string) {
  try {
    const res = await fetch(`http://127.0.0.1:8000/api/v1/projects/${projectId}/test-cases`, { cache: 'no-store' });
    if (!res.ok) return [];
    return res.json();
  } catch (error) {
    return [];
  }
}

export default async function ProjectOverview(props: { params: Promise<{ project_id: string }> }) {
  const params = await props.params;
  const project = await getProject(params.project_id);
  const { executions, total: totalExecutions } = await getExecutions(params.project_id);
  const testCases = await getTestCases(params.project_id);

  if (!project) return null;

  const scansCount = executions?.filter((e: any) => e.type === "scan").length || 0;
  const comparisonsCount = executions?.filter((e: any) => e.type === "visual_comparison").length || 0;
  const testCasesCount = testCases?.length || 0;

  return (
    <div className="flex flex-col max-w-6xl mx-auto space-y-8">
      <div>
        <h2 className="text-2xl font-bold text-zinc-100">Project Overview</h2>
        <p className="text-zinc-400 mt-1">{project.description || "No description provided."}</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="rounded-xl border border-zinc-800 bg-zinc-950 p-6 shadow-sm">
          <div className="flex items-center text-sm font-medium text-zinc-400 mb-2">
            <Activity className="mr-2 h-4 w-4 text-blue-500" />
            Scans
          </div>
          <div className="text-3xl font-bold text-zinc-100">{scansCount}</div>
        </div>
        <div className="rounded-xl border border-zinc-800 bg-zinc-950 p-6 shadow-sm">
          <div className="flex items-center text-sm font-medium text-zinc-400 mb-2">
            <GitCompare className="mr-2 h-4 w-4 text-emerald-500" />
            Comparisons
          </div>
          <div className="text-3xl font-bold text-zinc-100">{comparisonsCount}</div>
        </div>
        <div className="rounded-xl border border-zinc-800 bg-zinc-950 p-6 shadow-sm">
          <div className="flex items-center text-sm font-medium text-zinc-400 mb-2">
            <CheckSquare className="mr-2 h-4 w-4 text-purple-500" />
            Test Cases
          </div>
          <div className="text-3xl font-bold text-zinc-100">{testCasesCount}</div>
        </div>
        <div className="rounded-xl border border-zinc-800 bg-zinc-950 p-6 shadow-sm">
          <div className="flex items-center text-sm font-medium text-zinc-400 mb-2">
            <PlaySquare className="mr-2 h-4 w-4 text-amber-500" />
            Executions
          </div>
          <div className="text-3xl font-bold text-zinc-100">{totalExecutions}</div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        <div className="lg:col-span-2 space-y-6">
          <div className="rounded-xl border border-zinc-800 bg-zinc-950 shadow-sm overflow-hidden">
            <div className="px-6 py-5 border-b border-zinc-800">
              <h3 className="text-lg font-semibold text-zinc-100">Recent Executions</h3>
            </div>
            <div className="divide-y divide-zinc-800">
              {executions.length === 0 ? (
                <div className="p-8 text-center text-zinc-500 text-sm">No executions found.</div>
              ) : (
                executions.slice(0, 5).map((execution: any) => (
                  <div key={execution.id || execution.execution_id} className="flex items-center justify-between p-6 hover:bg-zinc-900/50 transition-colors">
                    <div className="flex flex-col">
                      <span className="text-sm font-medium text-zinc-200">Execution {(execution.id || execution.execution_id || "").split('-')[0]}</span>
                      <span className="text-xs text-zinc-500 mt-1">{execution.status}</span>
                    </div>
                    <div className="text-xs text-zinc-400 flex items-center">
                      <Calendar className="mr-1 h-3 w-3" />
                      {new Date(execution.created_at || execution.started_at).toLocaleDateString()}
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>
        </div>

        <div className="space-y-6">
          <div className="rounded-xl border border-zinc-800 bg-zinc-950 shadow-sm p-6">
            <h3 className="text-lg font-semibold text-zinc-100 mb-4">Project Details</h3>
            <div className="space-y-4">
              <div>
                <span className="block text-xs font-medium text-zinc-500 mb-1">Project ID</span>
                <span className="text-sm text-zinc-300 font-mono bg-zinc-900 px-2 py-1 rounded">
                  {project.project_id || project.id || "Unknown ID"}
                </span>
              </div>
              <div>
                <span className="block text-xs font-medium text-zinc-500 mb-1">Primary URL</span>
                {project.primary_url && project.primary_url.trim() !== "" ? (
                  <a href={project.primary_url} target="_blank" rel="noreferrer" className="text-sm text-blue-400 hover:underline flex items-center">
                    {project.primary_url}
                    <ExternalLink className="ml-1 h-3 w-3" />
                  </a>
                ) : (
                  <span className="text-sm text-zinc-500 italic">Not configured</span>
                )}
              </div>
              <div>
                <span className="block text-xs font-medium text-zinc-500 mb-1">Created At</span>
                <span className="text-sm text-zinc-300">{new Date(project.created_at).toLocaleString()}</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
