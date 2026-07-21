"use client";

import { useState, useEffect, useRef } from "react";
import { Search, Loader2, Link as LinkIcon, Monitor, Image as ImageIcon, History, Maximize2, Minimize2, ChevronRight, ChevronDown, ZoomIn, ZoomOut, RotateCcw } from "lucide-react";
import { useRouter, useSearchParams } from "next/navigation";
import AnalysisViewer from "./AnalysisViewer";

export default function ClientScans({ projectId }: { projectId: string }) {
  const router = useRouter();
  const searchParams = useSearchParams();
  const autoScanUrl = searchParams.get("url");
  const autoScanTriggered = searchParams.get("autoScan");
  const hasAutoScanned = useRef(false);

  const [url, setUrl] = useState(autoScanUrl || "");
  const [headed, setHeaded] = useState(false);
  const [isScanning, setIsScanning] = useState(false);
  const [scanResult, setScanResult] = useState<any | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isScreenshotExpanded, setIsScreenshotExpanded] = useState(false);
  const [zoom, setZoom] = useState(1);
  
  const [history, setHistory] = useState<any[]>([]);
  const [isLoadingHistory, setIsLoadingHistory] = useState(true);
  const [showHistory, setShowHistory] = useState(true);

  const fetchHistory = async () => {
    setIsLoadingHistory(true);
    try {
      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000'}/api/v1/projects/${projectId}/executions`);
      if (res.ok) {
        const data = await res.json();
        setHistory(data.executions.filter((e: any) => e.type === "scan"));
      }
    } catch (e) {
      console.error("Failed to load history", e);
    } finally {
      setIsLoadingHistory(false);
    }
  };

  const performScan = async (targetUrl: string) => {
    if (!targetUrl) return;
    
    setIsScanning(true);
    setError(null);
    setScanResult(null);
    setIsScreenshotExpanded(false);
    setZoom(1);
    
    try {
      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000'}/api/v1/scan`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ url: targetUrl, headed, project_id: projectId }),
      });
      
      const data = await res.json();
      
      if (res.ok) {
        setScanResult(data);
        fetchHistory(); // Refresh history
      } else {
        setError(data.detail || "Scan failed.");
      }
    } catch (e: any) {
      setError(e.message || "An error occurred.");
    } finally {
      setIsScanning(false);
    }
  };

  useEffect(() => {
    fetchHistory();
    
    if (autoScanTriggered === "true" && autoScanUrl && !hasAutoScanned.current) {
      hasAutoScanned.current = true;
      performScan(autoScanUrl);
      
      // Clean up the URL to remove the autoScan parameter
      const newUrl = `/projects/${projectId}/scans`;
      window.history.replaceState({}, '', newUrl);
    }
  }, [projectId, autoScanTriggered, autoScanUrl]);

  const handleScan = async (e: React.FormEvent) => {
    e.preventDefault();
    performScan(url);
  };

  const loadPastScan = async (execution: any) => {
    try {
      const scanId = execution.execution_id;
      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000'}/api/v1/scans/${scanId}`);
      if (res.ok) {
        const data = await res.json();
        // Construct scanResult similar to POST response
        setScanResult({
          status: data.scan_info.status,
          load_time: data.scan_info.duration_seconds,
          final_url: data.scan_info.url,
          analysis: data.analysis,
          screenshot_url: `/api/v1/scans/${scanId}/screenshot`
        });
        setUrl(data.scan_info.url);
        setIsScreenshotExpanded(false);
        setZoom(1);
      }
    } catch (e) {
      console.error("Failed to load past scan", e);
    }
  };

  return (
    <div className="flex flex-col h-full gap-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-zinc-100">Website Scanner</h2>
          <p className="text-zinc-400 mt-1">Scan URLs to analyze structure, capture screenshots, and assess readiness.</p>
        </div>
      </div>

      <div className="flex gap-6 flex-1 overflow-hidden">
        {/* Main Content Area */}
        <div className="flex flex-col flex-1 gap-6 overflow-y-auto pr-2 hide-scrollbar">
          <div className="rounded-xl border border-zinc-800 bg-zinc-950 p-6 shrink-0">
            <form onSubmit={handleScan} className="flex gap-4 items-end">
              <div className="flex-1 space-y-2">
                <label className="text-sm font-medium text-zinc-300">Target URL</label>
                <div className="relative">
                  <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                    <LinkIcon className="h-4 w-4 text-zinc-500" />
                  </div>
                  <input
                    type="url"
                    value={url}
                    onChange={(e) => setUrl(e.target.value)}
                    placeholder="https://example.com"
                    required
                    className="block w-full pl-10 bg-zinc-900 border border-zinc-700 rounded-md py-2 text-zinc-300 focus:ring-blue-500 focus:border-blue-500 sm:text-sm"
                  />
                </div>
              </div>
              
              <div className="flex items-center h-10 px-4 bg-zinc-900 border border-zinc-700 rounded-md">
                <input
                  id="headed-mode"
                  type="checkbox"
                  checked={headed}
                  onChange={(e) => setHeaded(e.target.checked)}
                  className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-zinc-600 rounded bg-zinc-800"
                />
                <label htmlFor="headed-mode" className="ml-2 block text-sm text-zinc-300">
                  Headed Mode
                </label>
              </div>
              
              <button
                type="submit"
                disabled={isScanning || !url}
                className="inline-flex items-center justify-center rounded-md text-sm font-medium transition-colors bg-blue-600 text-white hover:bg-blue-700 h-10 px-6 disabled:opacity-50 disabled:cursor-not-allowed shrink-0"
              >
                {isScanning ? (
                  <><Loader2 className="mr-2 h-4 w-4 animate-spin" /> Scanning...</>
                ) : (
                  <><Search className="mr-2 h-4 w-4" /> Scan</>
                )}
              </button>
            </form>
            {error && (
              <div className="mt-4 p-3 bg-red-900/20 border border-red-900/50 rounded text-sm text-red-400">
                {error}
              </div>
            )}
          </div>

          {scanResult && (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6 pb-6 shrink-0">
              <div className="rounded-xl border border-zinc-800 bg-zinc-950 p-6 flex flex-col h-[450px]">
                <h3 className="text-lg font-medium text-zinc-200 flex items-center gap-2 mb-4 shrink-0">
                  <Monitor className="h-5 w-5 text-blue-400" /> Scan Results
                </h3>
                <div className="space-y-4 text-sm flex-1 flex flex-col min-h-0">
                  <div className="grid grid-cols-2 gap-4 shrink-0">
                    <div className="bg-zinc-900 p-3 rounded-lg border border-zinc-800">
                      <span className="block text-zinc-500 mb-1">Status</span>
                      <span className="text-zinc-200">{scanResult.status}</span>
                    </div>
                    <div className="bg-zinc-900 p-3 rounded-lg border border-zinc-800">
                      <span className="block text-zinc-500 mb-1">Load Time</span>
                      <span className="text-zinc-200">{scanResult.load_time}s</span>
                    </div>
                  </div>
                  <div className="bg-zinc-900 p-3 rounded-lg border border-zinc-800 shrink-0">
                    <span className="block text-zinc-500 mb-1">Final URL</span>
                    <span className="text-zinc-200 truncate block">{scanResult.final_url}</span>
                  </div>
                  {scanResult.analysis && (
                    <div className="flex-1 min-h-0">
                      <AnalysisViewer analysis={scanResult.analysis} />
                    </div>
                  )}
                </div>
              </div>
              
              <div className="rounded-xl border border-zinc-800 bg-zinc-950 p-6 flex flex-col relative h-[450px]">
                <div className="flex items-center justify-between mb-4 shrink-0">
                  <h3 className="text-lg font-medium text-zinc-200 flex items-center gap-2">
                    <ImageIcon className="h-5 w-5 text-emerald-400" /> Screenshot
                  </h3>
                  <button 
                    onClick={() => setIsScreenshotExpanded(!isScreenshotExpanded)}
                    className="p-1.5 rounded-md hover:bg-zinc-800 text-zinc-400 hover:text-zinc-200 transition-colors"
                  >
                    {isScreenshotExpanded ? <Minimize2 className="h-4 w-4" /> : <Maximize2 className="h-4 w-4" />}
                  </button>
                </div>
                
                <div className={`bg-zinc-900 border border-zinc-800 rounded-lg overflow-hidden flex transition-all ${isScreenshotExpanded ? 'fixed inset-4 z-50 p-4 bg-zinc-950/95 backdrop-blur shadow-2xl flex-col' : 'flex-1 relative'}`}>
                  {isScreenshotExpanded && (
                    <div className="absolute top-6 right-6 flex items-center gap-2 z-50">
                      <button 
                        onClick={() => setZoom(z => z + 0.25)}
                        className="p-2 rounded-md bg-zinc-800 hover:bg-zinc-700 text-zinc-200 transition-colors"
                      >
                        <ZoomIn className="h-5 w-5" />
                      </button>
                      <button 
                        onClick={() => setZoom(z => Math.max(0.1, z - 0.25))}
                        className="p-2 rounded-md bg-zinc-800 hover:bg-zinc-700 text-zinc-200 transition-colors"
                      >
                        <ZoomOut className="h-5 w-5" />
                      </button>
                      <button 
                        onClick={() => setZoom(1)}
                        className="p-2 rounded-md bg-zinc-800 hover:bg-zinc-700 text-zinc-200 transition-colors"
                      >
                        <RotateCcw className="h-5 w-5" />
                      </button>
                      <button 
                        onClick={() => { setIsScreenshotExpanded(false); setZoom(1); }}
                        className="p-2 rounded-md bg-zinc-800 hover:bg-zinc-700 text-zinc-200 transition-colors ml-4"
                      >
                        <Minimize2 className="h-5 w-5" />
                      </button>
                    </div>
                  )}
                  {scanResult.screenshot_url ? (
                    <div className={`${isScreenshotExpanded ? 'w-full h-full overflow-auto pt-16' : 'absolute inset-0'}`}>
                      {/* eslint-disable-next-line @next/next/no-img-element */}
                      <img 
                        src={scanResult.screenshot_url.startsWith('http') ? scanResult.screenshot_url : `${process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000'}${scanResult.screenshot_url}`} 
                        alt="Scan Screenshot" 
                        style={isScreenshotExpanded ? { width: `${zoom * 100}%`, transition: 'width 0.2s' } : {}}
                        className={`transition-all ${isScreenshotExpanded ? 'max-w-none mx-auto block' : 'w-full h-full object-cover object-top block'}`}
                      />
                    </div>
                  ) : (
                    <span className="text-zinc-500 m-auto">No screenshot available</span>
                  )}
                </div>
              </div>
            </div>
          )}
        </div>

        {/* History Sidebar */}
        <div className="w-80 flex flex-col border border-zinc-800 bg-zinc-950 rounded-xl overflow-hidden shrink-0">
          <div 
            className="p-4 border-b border-zinc-800 bg-zinc-900/50 flex items-center justify-between cursor-pointer hover:bg-zinc-900 transition-colors"
            onClick={() => setShowHistory(!showHistory)}
          >
            <h3 className="font-medium text-zinc-200 flex items-center gap-2">
              <History className="h-4 w-4 text-zinc-400" /> Scan History
            </h3>
            {showHistory ? <ChevronDown className="h-4 w-4 text-zinc-500" /> : <ChevronRight className="h-4 w-4 text-zinc-500" />}
          </div>
          
          {showHistory && (
            <div className="flex-1 overflow-y-auto p-4 space-y-3 hide-scrollbar">
              {isLoadingHistory ? (
                <div className="flex items-center justify-center py-8 text-zinc-500">
                  <Loader2 className="h-5 w-5 animate-spin mr-2" /> Loading...
                </div>
              ) : history.length === 0 ? (
                <div className="text-center py-8 text-sm text-zinc-500">
                  No scan history found.
                </div>
              ) : (
                history.map((exec) => (
                  <button
                    key={exec.execution_id}
                    onClick={() => loadPastScan(exec)}
                    className="w-full text-left p-3 rounded-lg border border-zinc-800 bg-zinc-900/30 hover:bg-zinc-900 transition-colors"
                  >
                    <div className="flex justify-between items-start mb-1">
                      <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${exec.status === 'COMPLETED' ? 'bg-emerald-500/10 text-emerald-400 ring-1 ring-inset ring-emerald-500/20' : 'bg-zinc-500/10 text-zinc-400 ring-1 ring-inset ring-zinc-500/20'}`}>
                        {exec.status}
                      </span>
                      <span className="text-xs text-zinc-500">
                        {new Date(exec.started_at).toLocaleDateString()}
                      </span>
                    </div>
                    <div className="text-sm font-medium text-zinc-300 truncate mt-2" title={exec.metadata?.url}>
                      {exec.metadata?.url || 'Unknown URL'}
                    </div>
                    <div className="text-xs text-zinc-500 mt-1 font-mono">
                      {exec.execution_id.split('_').pop()}
                    </div>
                  </button>
                ))
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
