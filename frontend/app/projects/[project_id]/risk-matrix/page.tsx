import { AlertTriangle, BrainCircuit } from "lucide-react";

async function getRisks(projectId: string) {
  try {
    const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000'}/api/v1/projects/${projectId}/planning/risks`, { cache: 'no-store' });
    if (!res.ok) return null;
    return res.json();
  } catch (error) {
    return null;
  }
}

export default async function RiskMatrixTab(props: { params: Promise<{ project_id: string }> }) {
  const params = await props.params;
  const data = await getRisks(params.project_id);
  const risks = data?.risks || [];

  return (
    <div className="flex flex-col max-w-6xl mx-auto space-y-8">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-zinc-100">Risk Matrix</h2>
          <p className="text-zinc-400 mt-1">AI-identified business and technical risks.</p>
        </div>
        <button className="inline-flex items-center justify-center rounded-md text-sm font-medium transition-colors border border-zinc-700 bg-zinc-900 text-zinc-300 hover:bg-zinc-800 h-10 px-4 py-2">
          <BrainCircuit className="mr-2 h-4 w-4 text-purple-400" />
          Regenerate Analysis
        </button>
      </div>

      <div className="rounded-xl border border-zinc-800 bg-zinc-950 shadow-sm overflow-hidden">
        {(!risks || risks.length === 0) ? (
          <div className="p-12 text-center flex flex-col items-center justify-center">
            <div className="h-12 w-12 rounded-full bg-zinc-900 flex items-center justify-center mb-4">
              <AlertTriangle className="h-6 w-6 text-zinc-500" />
            </div>
            <h3 className="text-lg font-medium text-zinc-200">No risks analyzed</h3>
            <p className="text-sm text-zinc-500 mt-1 max-w-sm">Run the AI Planner to generate a comprehensive risk matrix based on your project context.</p>
          </div>
        ) : (
          <table className="min-w-full divide-y divide-zinc-800 text-left text-sm">
            <thead className="bg-zinc-900/50">
              <tr>
                <th scope="col" className="px-6 py-4 font-semibold text-zinc-300 w-1/4">Risk Area</th>
                <th scope="col" className="px-6 py-4 font-semibold text-zinc-300 w-1/2">Impact & Probability</th>
                <th scope="col" className="px-6 py-4 font-semibold text-zinc-300 w-1/4">Mitigation</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-zinc-800">
              {risks.map((risk: any, idx: number) => (
                <tr key={idx} className="hover:bg-zinc-900/50 transition-colors">
                  <td className="px-6 py-4 align-top">
                    <span className="font-medium text-zinc-200 block">{risk.name || risk.title}</span>
                  </td>
                  <td className="px-6 py-4 align-top text-zinc-400">
                    <div className="flex flex-col gap-2">
                      <div className="flex items-center gap-2">
                        <span className="text-xs font-semibold text-zinc-500 w-20">Impact:</span>
                        <span className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium 
                          ${risk.impact?.toLowerCase() === 'high' ? 'bg-red-500/10 text-red-400 ring-1 ring-inset ring-red-500/20' : 
                            risk.impact?.toLowerCase() === 'medium' ? 'bg-amber-500/10 text-amber-400 ring-1 ring-inset ring-amber-500/20' : 
                            'bg-blue-500/10 text-blue-400 ring-1 ring-inset ring-blue-500/20'}`}>
                          {risk.impact}
                        </span>
                      </div>
                      <div className="flex items-center gap-2">
                        <span className="text-xs font-semibold text-zinc-500 w-20">Probability:</span>
                        <span className="text-sm text-zinc-300">{risk.probability}</span>
                      </div>
                      <p className="mt-2 text-sm text-zinc-400">{risk.description}</p>
                    </div>
                  </td>
                  <td className="px-6 py-4 align-top text-zinc-400">
                    {risk.mitigation || risk.mitigation_strategy}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
