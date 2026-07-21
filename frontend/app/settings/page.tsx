import { BrainCircuit, CheckCircle2, AlertTriangle, KeySquare } from "lucide-react";

async function getAiConfig() {
  try {
    const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000'}/api/v1/ai/providers`, { cache: 'no-store' });
    if (!res.ok) return null;
    return res.json();
  } catch (error) {
    return null;
  }
}

async function getAiHealth() {
  try {
    const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000'}/api/v1/ai/health`, { cache: 'no-store' });
    if (!res.ok) return { status: 'unknown' };
    return res.json();
  } catch (error) {
    return { status: 'unknown' };
  }
}

export default async function SettingsPage() {
  const aiConfig = await getAiConfig();
  const health = await getAiHealth();

  return (
    <div className="max-w-4xl space-y-8">
      <div>
        <h2 className="text-xl font-semibold text-zinc-100">AI Provider Configuration</h2>
        <p className="text-sm text-zinc-400 mt-1">Configure which foundation models QAForge uses to generate tests and plans.</p>
      </div>

      <div className="rounded-xl border border-zinc-800 bg-zinc-950 shadow-sm overflow-hidden">
        <div className="p-6 border-b border-zinc-800">
          <div className="flex items-center justify-between mb-6">
            <div className="flex items-center gap-3">
              <div className="flex items-center justify-center h-10 w-10 rounded-lg bg-purple-500/10 border border-purple-500/20">
                <BrainCircuit className="h-5 w-5 text-purple-400" />
              </div>
              <div>
                <h3 className="text-base font-semibold text-zinc-100">Primary Provider</h3>
                <p className="text-xs text-zinc-400">Used for requirements parsing and test generation</p>
              </div>
            </div>
            <div>
              {health.status === 'healthy' ? (
                <span className="inline-flex items-center rounded-full bg-emerald-500/10 px-2.5 py-1 text-xs font-medium text-emerald-400 ring-1 ring-inset ring-emerald-500/20">
                  <CheckCircle2 className="mr-1 h-3.5 w-3.5" /> Connected
                </span>
              ) : (
                <span className="inline-flex items-center rounded-full bg-red-500/10 px-2.5 py-1 text-xs font-medium text-red-400 ring-1 ring-inset ring-red-500/20">
                  <AlertTriangle className="mr-1 h-3.5 w-3.5" /> Disconnected
                </span>
              )}
            </div>
          </div>

          <div className="space-y-4 max-w-xl">
            <div>
              <label className="block text-sm font-medium text-zinc-300 mb-1.5">Provider</label>
              <select className="w-full bg-zinc-900 border border-zinc-700 rounded-md py-2 px-3 text-sm text-zinc-200 focus:outline-none focus:ring-1 focus:ring-blue-500 focus:border-blue-500">
                {(aiConfig?.active_providers || ['openrouter']).map((p: string) => (
                  <option key={p} value={p} selected={p === aiConfig?.default}>
                    {p === 'openrouter' ? 'OpenRouter (Recommended)' : p}
                  </option>
                ))}
              </select>
            </div>
            
            <div>
              <label className="block text-sm font-medium text-zinc-300 mb-1.5">Model Override (Optional)</label>
              <input 
                type="text" 
                placeholder="e.g. nvidia/nemotron-3-ultra-550b-a55b:free" 
                className="w-full bg-zinc-900 border border-zinc-700 rounded-md py-2 px-3 text-sm text-zinc-200 placeholder-zinc-500 focus:outline-none focus:ring-1 focus:ring-blue-500 focus:border-blue-500"
                defaultValue=""
              />
              <p className="text-xs text-zinc-500 mt-1.5">Leave blank to use the backend default (Nemotron via OpenRouter).</p>
            </div>
          </div>
        </div>
        
        <div className="bg-zinc-900/30 p-6">
          <div className="flex items-center justify-between">
            <div>
              <h4 className="text-sm font-medium text-zinc-200">API Key Configuration</h4>
              <p className="text-xs text-zinc-500 mt-1">Manage authentication for your selected provider.</p>
            </div>
            <button className="inline-flex items-center justify-center rounded-md text-sm font-medium transition-colors border border-zinc-700 bg-zinc-900 text-zinc-300 hover:bg-zinc-800 h-9 px-4 py-2">
              <KeySquare className="mr-2 h-4 w-4" />
              Manage Keys
            </button>
          </div>
        </div>
      </div>
      
      <div className="flex justify-end pt-4">
        <button className="inline-flex items-center justify-center rounded-md text-sm font-medium transition-colors bg-blue-600 text-white hover:bg-blue-700 h-10 px-6 py-2">
          Save Configuration
        </button>
      </div>
    </div>
  );
}
