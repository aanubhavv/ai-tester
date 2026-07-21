import { GitBranch, Plus, BrainCircuit, GitPullRequest } from "lucide-react";
import AddFlowModal from "@/components/modals/AddFlowModal";

async function getFlows(projectId: string) {
  try {
    const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000'}/api/v1/projects/${projectId}/flows`, { cache: 'no-store' });
    if (!res.ok) return { flows: [] };
    return res.json();
  } catch (error) {
    return { flows: [] };
  }
}

export default async function FlowsTab(props: { params: Promise<{ project_id: string }> }) {
  const params = await props.params;
  const { flows } = await getFlows(params.project_id);

  return (
    <div className="flex flex-col max-w-6xl mx-auto space-y-8">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-zinc-100">User Flows</h2>
          <p className="text-zinc-400 mt-1">End-to-end user journeys mapped across your application.</p>
        </div>
        <div className="flex items-center gap-3">
          <button className="inline-flex items-center justify-center rounded-md text-sm font-medium transition-colors border border-zinc-700 bg-zinc-900 text-zinc-300 hover:bg-zinc-800 h-10 px-4 py-2">
            <BrainCircuit className="mr-2 h-4 w-4 text-purple-400" />
            Generate with AI
          </button>
          <AddFlowModal projectId={params.project_id} />
        </div>
      </div>

      <div className="rounded-xl border border-zinc-800 bg-zinc-950 shadow-sm overflow-hidden">
        <div className="divide-y divide-zinc-800">
          {(!flows || flows.length === 0) ? (
            <div className="p-12 text-center flex flex-col items-center justify-center">
              <div className="h-12 w-12 rounded-full bg-zinc-900 flex items-center justify-center mb-4">
                <GitPullRequest className="h-6 w-6 text-zinc-500" />
              </div>
              <h3 className="text-lg font-medium text-zinc-200">No user flows defined</h3>
              <p className="text-sm text-zinc-500 mt-1 max-w-sm">Use the AI Planner to construct logical user flows, or map them out manually.</p>
            </div>
          ) : (
            <div className="p-6 space-y-6">
              {flows.map((flow: any) => (
                <div key={flow.flow_id} className="rounded-lg border border-zinc-800 bg-zinc-900/50 p-6">
                  <div className="flex items-start justify-between mb-4">
                    <div>
                      <h3 className="text-lg font-semibold text-zinc-100">{flow.name}</h3>
                      <p className="text-sm text-zinc-400 mt-1">{flow.description}</p>
                    </div>
                  </div>
                  <div className="relative border-l border-zinc-800 ml-3 mt-6 space-y-8">
                    {flow.steps.map((step: any, index: number) => (
                      <div key={index} className="relative pl-6">
                        <div className="absolute -left-1.5 top-1 h-3 w-3 rounded-full border-2 border-zinc-900 bg-blue-500"></div>
                        <div className="flex items-center gap-3">
                          <span className="text-xs font-semibold text-zinc-500 w-6">{(index + 1).toString().padStart(2, '0')}</span>
                          <div>
                            <p className="text-sm font-medium text-zinc-200">{step.action}</p>
                            {step.description && <p className="text-xs text-zinc-500 mt-1">{step.description}</p>}
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
