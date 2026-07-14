import { GitCompare, Plus } from "lucide-react";

export default async function ComparisonsTab(props: { params: Promise<{ project_id: string }> }) {
  const params = await props.params;
  // Mock data since we are focused on UI/Frontend layout
  const comparisons: any[] = [];

  return (
    <div className="flex flex-col max-w-6xl mx-auto space-y-8">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-zinc-100">Visual Comparisons</h2>
          <p className="text-zinc-400 mt-1">Review visual regression results between test runs.</p>
        </div>
        <button className="inline-flex items-center justify-center rounded-md text-sm font-medium transition-colors bg-blue-600 text-white hover:bg-blue-700 h-10 px-4 py-2">
          <Plus className="mr-2 h-4 w-4" />
          New Comparison
        </button>
      </div>

      <div className="rounded-xl border border-zinc-800 bg-zinc-950 shadow-sm overflow-hidden">
        {(!comparisons || comparisons.length === 0) ? (
          <div className="p-12 text-center flex flex-col items-center justify-center">
            <div className="h-12 w-12 rounded-full bg-zinc-900 flex items-center justify-center mb-4">
              <GitCompare className="h-6 w-6 text-zinc-500" />
            </div>
            <h3 className="text-lg font-medium text-zinc-200">No comparisons found</h3>
            <p className="text-sm text-zinc-500 mt-1 max-w-sm">Select a baseline execution and a current execution to detect visual regressions.</p>
            <div className="mt-8 flex gap-8 items-center opacity-40 select-none pointer-events-none">
              <div className="flex flex-col items-center">
                <div className="h-32 w-48 rounded bg-zinc-800 border border-zinc-700 flex items-center justify-center text-xs font-mono text-zinc-500">Baseline</div>
              </div>
              <GitCompare className="h-8 w-8 text-zinc-600" />
              <div className="flex flex-col items-center">
                <div className="h-32 w-48 rounded bg-zinc-800 border border-zinc-700 flex items-center justify-center text-xs font-mono text-zinc-500">Current</div>
              </div>
            </div>
          </div>
        ) : (
          <div className="p-6">
            {/* Real implementation would render comparison list */}
          </div>
        )}
      </div>
    </div>
  );
}
