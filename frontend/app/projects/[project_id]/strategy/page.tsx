import { Target, BrainCircuit, ShieldCheck, Zap } from "lucide-react";

async function getStrategy(projectId: string) {
  try {
    const res = await fetch(`http://127.0.0.1:8000/api/v1/projects/${projectId}/planning/strategy`, { cache: 'no-store' });
    if (!res.ok) return null;
    return res.json();
  } catch (error) {
    return null;
  }
}

export default async function StrategyTab(props: { params: Promise<{ project_id: string }> }) {
  const params = await props.params;
  const data = await getStrategy(params.project_id);
  const strategy = data?.strategy || data || null;

  return (
    <div className="flex flex-col max-w-6xl mx-auto space-y-8">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-zinc-100">Testing Strategy</h2>
          <p className="text-zinc-400 mt-1">High-level test approach and focus areas recommended by AI.</p>
        </div>
        <button className="inline-flex items-center justify-center rounded-md text-sm font-medium transition-colors border border-zinc-700 bg-zinc-900 text-zinc-300 hover:bg-zinc-800 h-10 px-4 py-2">
          <BrainCircuit className="mr-2 h-4 w-4 text-purple-400" />
          Regenerate Strategy
        </button>
      </div>

      <div className="rounded-xl border border-zinc-800 bg-zinc-950 shadow-sm overflow-hidden">
        {(!strategy || Object.keys(strategy).length === 0 || (strategy.testing_strategy && strategy.testing_strategy.length === 0)) ? (
          <div className="p-12 text-center flex flex-col items-center justify-center">
            <div className="h-12 w-12 rounded-full bg-zinc-900 flex items-center justify-center mb-4">
              <Target className="h-6 w-6 text-zinc-500" />
            </div>
            <h3 className="text-lg font-medium text-zinc-200">No strategy generated</h3>
            <p className="text-sm text-zinc-500 mt-1 max-w-sm">Run the AI Planner to establish a comprehensive testing approach for this project.</p>
          </div>
        ) : (
          <div className="p-8 space-y-12">
            <div className="prose prose-invert max-w-none">
              <div className="flex items-center gap-2 mb-4 border-b border-zinc-800 pb-2">
                <Target className="h-5 w-5 text-blue-400" />
                <h3 className="text-xl font-semibold text-zinc-100 m-0">Core Objectives</h3>
              </div>
              <p className="text-zinc-300 leading-relaxed">
                {strategy.objectives || strategy.summary || "No specific objectives summarized. The strategy outlines the required test levels and types below."}
              </p>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
              <div className="bg-zinc-900/50 rounded-lg p-6 border border-zinc-800">
                <div className="flex items-center gap-2 mb-4">
                  <ShieldCheck className="h-5 w-5 text-emerald-400" />
                  <h3 className="text-lg font-semibold text-zinc-100">Test Types</h3>
                </div>
                <ul className="space-y-3">
                  {(strategy.test_types || strategy.recommended_types || []).map((type: string, i: number) => (
                    <li key={i} className="flex items-start">
                      <span className="h-1.5 w-1.5 rounded-full bg-emerald-500 mt-2 mr-3 shrink-0"></span>
                      <span className="text-sm text-zinc-300">{type}</span>
                    </li>
                  ))}
                  {(!strategy.test_types && !strategy.recommended_types) && (
                    <li className="text-sm text-zinc-500">Functional, Visual, E2E, API</li>
                  )}
                </ul>
              </div>

              <div className="bg-zinc-900/50 rounded-lg p-6 border border-zinc-800">
                <div className="flex items-center gap-2 mb-4">
                  <Zap className="h-5 w-5 text-amber-400" />
                  <h3 className="text-lg font-semibold text-zinc-100">Focus Areas</h3>
                </div>
                <ul className="space-y-3">
                  {(strategy.focus_areas || strategy.priorities || []).map((area: string, i: number) => (
                    <li key={i} className="flex items-start">
                      <span className="h-1.5 w-1.5 rounded-full bg-amber-500 mt-2 mr-3 shrink-0"></span>
                      <span className="text-sm text-zinc-300">{area}</span>
                    </li>
                  ))}
                  {(!strategy.focus_areas && !strategy.priorities) && (
                    <li className="text-sm text-zinc-500">Critical user journeys, authentication, checkout.</li>
                  )}
                </ul>
              </div>
            </div>
            
            {(strategy.environments || strategy.tools) && (
              <div className="pt-6 border-t border-zinc-800">
                <h3 className="text-lg font-semibold text-zinc-100 mb-4">Environment & Tooling</h3>
                <div className="flex flex-wrap gap-2">
                  {(strategy.environments || []).map((env: string, i: number) => (
                    <span key={i} className="inline-flex items-center rounded-md bg-zinc-800 px-2.5 py-1 text-sm font-medium text-zinc-300">
                      {env}
                    </span>
                  ))}
                  {(strategy.tools || []).map((tool: string, i: number) => (
                    <span key={`tool-${i}`} className="inline-flex items-center rounded-md bg-zinc-800 px-2.5 py-1 text-sm font-medium text-zinc-300 border border-zinc-700">
                      {tool}
                    </span>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
