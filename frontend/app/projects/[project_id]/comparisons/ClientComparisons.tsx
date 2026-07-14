"use client";

import { useState, useEffect } from "react";
import { GitCompare, Loader2, AlertTriangle, CheckCircle2, XCircle } from "lucide-react";
import { useRouter } from "next/navigation";

export default function ClientComparisons({ projectId }: { projectId: string }) {
  const [scans, setScans] = useState<any[]>([]);
  const [baselineId, setBaselineId] = useState<string>("");
  const [currentId, setCurrentId] = useState<string>("");
  const [isLoading, setIsLoading] = useState(true);
  const [isComparing, setIsComparing] = useState(false);
  const [result, setResult] = useState<any | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchScans();
  }, [projectId]);

  const fetchScans = async () => {
    try {
      const res = await fetch(`http://127.0.0.1:8000/api/v1/projects/${projectId}/executions`);
      if (res.ok) {
        const data = await res.json();
        // filter for completed scans
        const completedScans = (data.executions || []).filter((e: any) => e.type === "scan" && e.status === "completed");
        setScans(completedScans);
        if (completedScans.length >= 2) {
          setBaselineId(completedScans[1].execution_id);
          setCurrentId(completedScans[0].execution_id);
        } else if (completedScans.length === 1) {
          setBaselineId(completedScans[0].execution_id);
        }
      }
    } catch (err) {
      console.error("Failed to fetch scans", err);
    } finally {
      setIsLoading(false);
    }
  };

  const handleCompare = async () => {
    if (!baselineId || !currentId) {
      setError("Please select both a baseline and current scan");
      return;
    }
    setIsComparing(true);
    setError(null);
    setResult(null);

    try {
      const res = await fetch(`http://127.0.0.1:8000/api/v1/compare`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify({
          project_id: projectId,
          baseline_scan_id: baselineId,
          current_scan_id: currentId,
          threshold: 0.05,
          ignored_selectors: []
        })
      });
      
      const data = await res.json();
      if (!res.ok) {
        throw new Error(data.detail || "Failed to compare scans");
      }
      setResult(data);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setIsComparing(false);
    }
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-[400px]">
        <Loader2 className="h-8 w-8 animate-spin text-zinc-500" />
      </div>
    );
  }

  return (
    <div className="flex flex-col max-w-6xl mx-auto space-y-8">
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h2 className="text-2xl font-bold text-zinc-100">Visual Comparisons</h2>
          <p className="text-zinc-400 mt-1">Review visual regression results between test runs.</p>
        </div>
      </div>

      <div className="rounded-xl border border-zinc-800 bg-zinc-950 p-6 shadow-sm">
        <div className="grid grid-cols-1 md:grid-cols-[1fr_auto_1fr] items-end gap-6 mb-8">
          <div className="space-y-2">
            <label className="text-sm font-medium text-zinc-300">Baseline Scan</label>
            <select 
              value={baselineId}
              onChange={(e) => setBaselineId(e.target.value)}
              className="w-full bg-zinc-900 border border-zinc-800 rounded-lg px-4 py-2.5 text-zinc-200 outline-none focus:border-blue-500"
            >
              <option value="">Select scan...</option>
              {scans.map(s => (
                <option key={s.execution_id} value={s.execution_id}>
                  {new Date(s.started_at).toLocaleString()} - {s.execution_id.split('_').pop()}
                </option>
              ))}
            </select>
          </div>
          
          <div className="flex justify-center pb-2 hidden md:block">
            <GitCompare className="w-6 h-6 text-zinc-500" />
          </div>

          <div className="space-y-2">
            <label className="text-sm font-medium text-zinc-300">Current Scan</label>
            <select 
              value={currentId}
              onChange={(e) => setCurrentId(e.target.value)}
              className="w-full bg-zinc-900 border border-zinc-800 rounded-lg px-4 py-2.5 text-zinc-200 outline-none focus:border-blue-500"
            >
              <option value="">Select scan...</option>
              {scans.map(s => (
                <option key={s.execution_id} value={s.execution_id}>
                  {new Date(s.started_at).toLocaleString()} - {s.execution_id.split('_').pop()}
                </option>
              ))}
            </select>
          </div>
        </div>
        
        <div className="flex justify-center border-b border-zinc-800 pb-6 mb-6">
          <button 
            onClick={handleCompare}
            disabled={isComparing || !baselineId || !currentId}
            className="inline-flex items-center justify-center rounded-md text-sm font-medium transition-colors bg-blue-600 text-white hover:bg-blue-700 h-10 px-8 py-2 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {isComparing ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : <GitCompare className="w-4 h-4 mr-2" />}
            Run Comparison
          </button>
        </div>

        {error && (
          <div className="bg-red-950/30 border border-red-900/50 p-4 rounded-lg flex gap-3 text-red-200 text-sm mb-6">
            <AlertTriangle className="w-5 h-5 shrink-0 text-red-400" />
            <p>{error}</p>
          </div>
        )}

        {result && (
          <div className="space-y-6">
            <div className="flex flex-wrap items-center gap-4">
              <h3 className="text-lg font-medium text-zinc-200">Result:</h3>
              {result.passed ? (
                <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-emerald-950/30 border border-emerald-900/50 text-emerald-400 text-sm font-medium">
                  <CheckCircle2 className="w-4 h-4" /> Passed (No significant changes)
                </span>
              ) : (
                <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-amber-950/30 border border-amber-900/50 text-amber-400 text-sm font-medium">
                  <AlertTriangle className="w-4 h-4" /> Visual Regressions Detected
                </span>
              )}
            </div>

            <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
              <div className="bg-zinc-900/50 p-4 rounded-lg border border-zinc-800/60">
                <span className="block text-[10px] font-medium text-zinc-500 uppercase tracking-wider mb-1">Difference %</span>
                <span className="text-xl font-semibold text-zinc-200">{(result.statistics.difference_percentage * 100).toFixed(2)}%</span>
              </div>
              <div className="bg-zinc-900/50 p-4 rounded-lg border border-zinc-800/60">
                <span className="block text-[10px] font-medium text-zinc-500 uppercase tracking-wider mb-1">Changed Pixels</span>
                <span className="text-xl font-semibold text-zinc-200">{result.statistics.changed_pixels}</span>
              </div>
              <div className="bg-zinc-900/50 p-4 rounded-lg border border-zinc-800/60">
                <span className="block text-[10px] font-medium text-zinc-500 uppercase tracking-wider mb-1">Changed Regions</span>
                <span className="text-xl font-semibold text-zinc-200">{result.changed_regions?.length || 0}</span>
              </div>
              <div className="bg-zinc-900/50 p-4 rounded-lg border border-zinc-800/60">
                <span className="block text-[10px] font-medium text-zinc-500 uppercase tracking-wider mb-1">Image Size</span>
                <span className="text-xl font-semibold text-zinc-200">{result.statistics.image_width}x{result.statistics.image_height}</span>
              </div>
            </div>

            {result.warnings && result.warnings.length > 0 && (
              <div className="bg-amber-950/20 border border-amber-900/30 p-3 rounded text-amber-400 text-sm space-y-1">
                {result.warnings.map((w: string, i: number) => <p key={i} className="flex gap-2"><AlertTriangle className="w-4 h-4 shrink-0" /> {w}</p>)}
              </div>
            )}

            <div className="bg-zinc-900 rounded-lg overflow-hidden border border-zinc-800">
              <div className="p-3 bg-zinc-950/50 border-b border-zinc-800 flex justify-between items-center">
                <span className="text-sm font-medium text-zinc-300">Visual Diff Overlay</span>
              </div>
              <div className="relative w-full flex justify-center bg-zinc-950 p-4">
                <img 
                  src={`http://127.0.0.1:8000${result.diff_image_url}`} 
                  alt="Diff" 
                  className="max-w-full rounded shadow-md border border-zinc-800"
                />
              </div>
            </div>
          </div>
        )}
        
        {!result && !error && !isComparing && (
          <div className="p-12 text-center flex flex-col items-center justify-center opacity-50">
            <GitCompare className="h-10 w-10 text-zinc-500 mb-4" />
            <h3 className="text-lg font-medium text-zinc-400">Select scans and run comparison</h3>
            <p className="text-sm text-zinc-500 mt-1 max-w-sm">Differences will be highlighted in magenta. Red lines highlight areas with changes.</p>
          </div>
        )}
      </div>
    </div>
  );
}
