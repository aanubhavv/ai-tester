import { Play, PlaySquare, Calendar, Clock, AlertTriangle, CheckCircle2 } from "lucide-react";
import Link from "next/link";
import ClientExecutionsTable from "./ClientExecutionsTable";

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

  // Removed getStatusDisplay since it's now in ClientExecutionsTable

  return (
    <div className="flex flex-col max-w-6xl mx-auto space-y-8">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-zinc-100">Executions</h2>
          <p className="text-zinc-400 mt-1">History of test suites, scans, and pipeline runs.</p>
        </div>
      </div>

      <ClientExecutionsTable projectId={params.project_id} initialExecutions={executions} />
    </div>
  );
}
