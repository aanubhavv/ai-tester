import { Play, PlaySquare, Calendar, Clock, AlertTriangle, CheckCircle2 } from "lucide-react";
import Link from "next/link";

async function getExecutions(projectId: string) {
  try {
    const res = await fetch(`http://127.0.0.1:8000/api/v1/projects/${projectId}/executions`, { cache: 'no-store' });
    if (!res.ok) return { executions: [] };
    return res.json();
  } catch (error) {
    return { executions: [] };
  }
}

export default async function ExecutionsTab(props: { params: Promise<{ project_id: string }> }) {
  const params = await props.params;
  const { executions } = await getExecutions(params.project_id);

  const getStatusDisplay = (status: string) => {
    switch(status?.toLowerCase()) {
      case 'completed': 
      case 'passed':
        return <span className="inline-flex items-center rounded-full bg-emerald-500/10 px-2 py-1 text-xs font-medium text-emerald-400 ring-1 ring-inset ring-emerald-500/20"><CheckCircle2 className="mr-1 h-3 w-3" /> Completed</span>;
      case 'failed':
      case 'error':
        return <span className="inline-flex items-center rounded-full bg-red-500/10 px-2 py-1 text-xs font-medium text-red-400 ring-1 ring-inset ring-red-500/20"><AlertTriangle className="mr-1 h-3 w-3" /> Failed</span>;
      case 'running':
      case 'in_progress':
        return <span className="inline-flex items-center rounded-full bg-blue-500/10 px-2 py-1 text-xs font-medium text-blue-400 ring-1 ring-inset ring-blue-500/20">Running</span>;
      default:
        return <span className="inline-flex items-center rounded-full bg-zinc-500/10 px-2 py-1 text-xs font-medium text-zinc-400 ring-1 ring-inset ring-zinc-500/20">{status || "Unknown"}</span>;
    }
  };

  return (
    <div className="flex flex-col max-w-6xl mx-auto space-y-8">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-zinc-100">Executions</h2>
          <p className="text-zinc-400 mt-1">History of test suites, scans, and pipeline runs.</p>
        </div>
        <div className="flex items-center gap-3">
          <Link href={`/projects/${params.project_id}/executions/new`} className="inline-flex items-center justify-center rounded-md text-sm font-medium transition-colors bg-blue-600 text-white hover:bg-blue-700 h-10 px-4 py-2">
            <Play className="mr-2 h-4 w-4" />
            New Execution
          </Link>
        </div>
      </div>

      <div className="rounded-xl border border-zinc-800 bg-zinc-950 shadow-sm overflow-hidden">
        <div className="divide-y divide-zinc-800">
          {(!executions || executions.length === 0) ? (
            <div className="p-12 text-center flex flex-col items-center justify-center">
              <div className="h-12 w-12 rounded-full bg-zinc-900 flex items-center justify-center mb-4">
                <PlaySquare className="h-6 w-6 text-zinc-500" />
              </div>
              <h3 className="text-lg font-medium text-zinc-200">No executions found</h3>
              <p className="text-sm text-zinc-500 mt-1 max-w-sm">Run a scan or execute a test suite to view results here.</p>
            </div>
          ) : (
            <table className="min-w-full divide-y divide-zinc-800 text-left text-sm whitespace-nowrap">
              <thead className="bg-zinc-900/50">
                <tr>
                  <th scope="col" className="px-6 py-4 font-semibold text-zinc-300">Execution ID</th>
                  <th scope="col" className="px-6 py-4 font-semibold text-zinc-300">Type</th>
                  <th scope="col" className="px-6 py-4 font-semibold text-zinc-300">Status</th>
                  <th scope="col" className="px-6 py-4 font-semibold text-zinc-300">Target</th>
                  <th scope="col" className="px-6 py-4 font-semibold text-zinc-300">Started</th>
                  <th scope="col" className="px-6 py-4 font-semibold text-zinc-300 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-zinc-800">
                {executions.map((exec: any) => (
                  <tr key={exec.id || exec.execution_id} className="hover:bg-zinc-900/50 transition-colors cursor-pointer">
                    <td className="px-6 py-4">
                      <div className="flex items-center gap-3">
                        <span className="font-mono text-zinc-300">{(exec.id || exec.execution_id).split('-')[0]}</span>
                      </div>
                    </td>
                    <td className="px-6 py-4">
                      <span className="capitalize text-zinc-400">{exec.type || "Scan"}</span>
                    </td>
                    <td className="px-6 py-4">
                      {getStatusDisplay(exec.status)}
                    </td>
                    <td className="px-6 py-4 text-zinc-400 truncate max-w-[200px]">
                      {exec.metadata?.url || "N/A"}
                    </td>
                    <td className="px-6 py-4 text-zinc-400">
                      <div className="flex items-center">
                        <Calendar className="mr-1.5 h-3 w-3" />
                        {new Date(exec.created_at).toLocaleString()}
                      </div>
                    </td>
                    <td className="px-6 py-4 text-right">
                      <button className="text-blue-400 hover:text-blue-300 font-medium">View Report</button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>
    </div>
  );
}
