import { Layers, Play, Settings } from "lucide-react";

async function getSuites(projectId: string) {
  try {
    const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000'}/api/v1/projects/${projectId}/planning/suites`, { cache: 'no-store' });
    if (!res.ok) return null;
    return res.json();
  } catch (error) {
    return null;
  }
}

export default async function TestSuitesTab(props: { params: Promise<{ project_id: string }> }) {
  const params = await props.params;
  const data = await getSuites(params.project_id);
  const suites = data?.suites || [];

  return (
    <div className="flex flex-col max-w-6xl mx-auto space-y-8">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-zinc-100">Test Suites</h2>
          <p className="text-zinc-400 mt-1">AI-generated groups of test cases mapped to features.</p>
        </div>
      </div>

      <div className="space-y-6">
        {(!suites || suites.length === 0) ? (
          <div className="rounded-xl border border-zinc-800 bg-zinc-950 p-12 text-center flex flex-col items-center justify-center">
            <div className="h-12 w-12 rounded-full bg-zinc-900 flex items-center justify-center mb-4">
              <Layers className="h-6 w-6 text-zinc-500" />
            </div>
            <h3 className="text-lg font-medium text-zinc-200">No test suites generated</h3>
            <p className="text-sm text-zinc-500 mt-1 max-w-sm">Run the AI Planner to automatically generate comprehensive test suites.</p>
          </div>
        ) : (
          suites.map((suite: any, index: number) => (
            <div key={index} className="rounded-xl border border-zinc-800 bg-zinc-950 shadow-sm overflow-hidden">
              <div className="px-6 py-5 border-b border-zinc-800 flex items-start justify-between bg-zinc-900/30">
                <div>
                  <div className="flex items-center gap-3 mb-1">
                    <h3 className="text-lg font-semibold text-zinc-100">{suite.suite_name}</h3>
                    <span className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium 
                        ${suite.priority?.toLowerCase() === 'high' ? 'bg-red-500/10 text-red-400 ring-1 ring-inset ring-red-500/20' : 
                          suite.priority?.toLowerCase() === 'medium' ? 'bg-amber-500/10 text-amber-400 ring-1 ring-inset ring-amber-500/20' : 
                          'bg-blue-500/10 text-blue-400 ring-1 ring-inset ring-blue-500/20'}`}>
                        {suite.priority || "Medium"} Priority
                    </span>
                  </div>
                  <p className="text-sm text-zinc-400">{suite.description}</p>
                </div>
                <div className="flex items-center gap-2">
                  <button className="inline-flex items-center justify-center rounded-md text-sm font-medium transition-colors border border-zinc-700 bg-zinc-900 text-zinc-300 hover:bg-zinc-800 h-9 px-3 py-1.5">
                    <Settings className="mr-2 h-3 w-3" />
                    Edit
                  </button>
                  <button className="inline-flex items-center justify-center rounded-md text-sm font-medium transition-colors bg-blue-600 text-white hover:bg-blue-700 h-9 px-3 py-1.5">
                    <Play className="mr-2 h-3 w-3" />
                    Generate Test Cases
                  </button>
                </div>
              </div>
              
              <div className="p-6">
                <div className="flex items-center justify-between mb-4">
                  <h4 className="text-sm font-medium text-zinc-300">High-Level Scenarios ({suite.high_level_test_cases?.length || 0})</h4>
                  <div className="text-xs text-zinc-500">Feature: <span className="font-medium text-zinc-300">{suite.feature_name}</span></div>
                </div>
                <ul className="space-y-3">
                  {(suite.high_level_test_cases || []).map((tc: any, i: number) => (
                    <li key={i} className="flex items-start text-sm text-zinc-400 bg-zinc-900/50 p-3 rounded-md border border-zinc-800/50">
                      <span className="text-zinc-500 w-6 shrink-0 mt-0.5">{i + 1}.</span>
                      <div>
                        <span className="font-medium text-zinc-200 block mb-1">{tc.title || tc.name || tc}</span>
                        {tc.description && <span className="text-zinc-500">{tc.description}</span>}
                      </div>
                    </li>
                  ))}
                </ul>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
