"use client";

import { useState, useEffect } from "react";
import { Calendar, PlaySquare, AlertTriangle, CheckCircle2, ZoomIn, ZoomOut, RotateCcw, X, GitCompare } from "lucide-react";
import Link from "next/link";
import AnalysisViewer from "../scans/AnalysisViewer";

interface ClientExecutionsTableProps {
  projectId: string;
  initialExecutions: any[];
}

export default function ClientExecutionsTable({ projectId, initialExecutions }: ClientExecutionsTableProps) {
  const [executions] = useState<any[]>(initialExecutions);
  const [selectedExecution, setSelectedExecution] = useState<any | null>(null);
  const [zoom, setZoom] = useState(1);
  const [scanReport, setScanReport] = useState<any | null>(null);
  const [isLoadingScan, setIsLoadingScan] = useState(false);

  useEffect(() => {
    if (selectedExecution?.type === "scan") {
      setIsLoadingScan(true);
      fetch(`http://127.0.0.1:8000/api/v1/scans/${selectedExecution.id || selectedExecution.execution_id}`)
        .then(res => res.json())
        .then(data => {
          setScanReport(data);
        })
        .catch(err => console.error("Failed to load scan details", err))
        .finally(() => setIsLoadingScan(false));
    } else {
      setScanReport(null);
    }
  }, [selectedExecution]);

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

  const getImageUrl = (exec: any) => {
    if (exec.type === "visual_comparison") {
      return `http://127.0.0.1:8000/api/v1/projects/${projectId}/executions/${exec.execution_id || exec.id}/diff`;
    }
    return `http://127.0.0.1:8000/api/v1/scans/${exec.execution_id || exec.id}/screenshot`;
  };

  const closeModal = () => {
    setSelectedExecution(null);
    setZoom(1);
  };

  return (
    <>
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
                  <th scope="col" className="px-6 py-4 font-semibold text-zinc-300">Started</th>
                  <th scope="col" className="px-6 py-4 font-semibold text-zinc-300 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-zinc-800">
                {executions.map((exec: any) => (
                  <tr key={exec.id || exec.execution_id} className="hover:bg-zinc-900/50 transition-colors">
                    <td className="px-6 py-4">
                      <div className="flex items-center gap-3">
                        <span className="font-mono text-zinc-300">{(exec.id || exec.execution_id).split('-')[0]}</span>
                      </div>
                    </td>
                    <td className="px-6 py-4">
                      <span className="capitalize text-zinc-400 flex items-center gap-2">
                        {exec.type === 'visual_comparison' ? <GitCompare className="w-4 h-4" /> : null}
                        {exec.type === 'visual_comparison' ? 'Visual Comparison' : (exec.type || "Scan")}
                      </span>
                    </td>
                    <td className="px-6 py-4">
                      {getStatusDisplay(exec.status)}
                    </td>
                    <td className="px-6 py-4 text-zinc-400">
                      <div className="flex items-center">
                        <Calendar className="mr-1.5 h-3 w-3" />
                        {new Date(exec.started_at || exec.created_at).toLocaleString()}
                      </div>
                    </td>
                    <td className="px-6 py-4 text-right space-x-4">
                      <Link 
                        href={`/projects/${projectId}/${exec.type === 'visual_comparison' ? 'comparisons' : 'scans'}?execution_id=${exec.id || exec.execution_id}`}
                        className="text-blue-400 hover:text-blue-300 font-medium"
                      >
                        Open Tool
                      </Link>
                      <button 
                        onClick={() => setSelectedExecution(exec)}
                        className="text-emerald-400 hover:text-emerald-300 font-medium"
                      >
                        View Result
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>

      {selectedExecution && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm">
          <div className="bg-zinc-950 border border-zinc-800 rounded-xl w-full max-w-6xl h-[90vh] flex flex-col shadow-2xl overflow-hidden relative">
            
            {/* Header */}
            <div className="flex items-center justify-between p-4 border-b border-zinc-800 bg-zinc-900/50">
              <div className="flex items-center gap-4">
                <h3 className="text-lg font-medium text-zinc-100">
                  {selectedExecution.type === 'visual_comparison' ? 'Comparison Result' : 'Scan Result'}
                  <span className="ml-3 text-sm font-mono text-zinc-500">{(selectedExecution.execution_id || selectedExecution.id)}</span>
                </h3>
                {getStatusDisplay(selectedExecution.status)}
              </div>
              
              <div className="flex items-center gap-2">
                <div className="flex bg-zinc-900 rounded-md border border-zinc-800 mr-4">
                  <button onClick={() => setZoom(z => z + 0.25)} className="p-2 hover:bg-zinc-800 text-zinc-400 hover:text-zinc-200 transition-colors border-r border-zinc-800" title="Zoom In">
                    <ZoomIn className="w-4 h-4" />
                  </button>
                  <button onClick={() => setZoom(z => Math.max(0.1, z - 0.25))} className="p-2 hover:bg-zinc-800 text-zinc-400 hover:text-zinc-200 transition-colors border-r border-zinc-800" title="Zoom Out">
                    <ZoomOut className="w-4 h-4" />
                  </button>
                  <button onClick={() => setZoom(1)} className="p-2 hover:bg-zinc-800 text-zinc-400 hover:text-zinc-200 transition-colors" title="Reset Zoom">
                    <RotateCcw className="w-4 h-4" />
                  </button>
                </div>
                <button onClick={closeModal} className="p-2 rounded-md hover:bg-zinc-800 text-zinc-400 hover:text-zinc-200 transition-colors">
                  <X className="w-5 h-5" />
                </button>
              </div>
            </div>
            
            {/* Details Panel (if available) */}
            {selectedExecution.metadata?.passed !== undefined && (
              <div className="p-4 border-b border-zinc-800 bg-zinc-900/30 flex gap-6">
                <div>
                  <span className="text-xs text-zinc-500 block mb-1">Result</span>
                  {selectedExecution.metadata.passed ? (
                    <span className="text-emerald-400 font-medium">Passed</span>
                  ) : (
                    <span className="text-amber-400 font-medium">Regressions Detected</span>
                  )}
                </div>
                {selectedExecution.metadata.statistics && (
                  <>
                    <div>
                      <span className="text-xs text-zinc-500 block mb-1">Difference</span>
                      <span className="text-zinc-300">{(selectedExecution.metadata.statistics.difference_percentage * 100).toFixed(2)}%</span>
                    </div>
                    <div>
                      <span className="text-xs text-zinc-500 block mb-1">Changed Pixels</span>
                      <span className="text-zinc-300">{selectedExecution.metadata.statistics.changed_pixels}</span>
                    </div>
                  </>
                )}
              </div>
            )}

            {/* Modal Body */}
            <div className="flex-1 overflow-hidden flex flex-col lg:flex-row bg-zinc-950">
              {/* Image Viewer */}
              <div className={`flex-1 overflow-auto p-8 relative flex items-start justify-center ${scanReport?.analysis ? 'border-r border-zinc-800' : ''}`}>
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img 
                  src={getImageUrl(selectedExecution)} 
                  alt="Result" 
                  style={{ width: `${zoom * 100}%`, transition: 'width 0.2s' }}
                  className="max-w-none shadow-2xl ring-1 ring-zinc-800"
                  onError={(e) => {
                    e.currentTarget.style.display = 'none';
                    e.currentTarget.parentElement!.innerHTML = '<div class="text-zinc-500 flex flex-col items-center gap-2"><svg class="w-8 h-8 opacity-50" xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg><span>Image not available</span></div>';
                  }}
                />
              </div>

              {/* Analysis Panel */}
              {isLoadingScan && (
                <div className="w-full lg:w-[450px] flex items-center justify-center border-l border-zinc-800 bg-zinc-900/20">
                  <span className="text-zinc-500">Loading analysis...</span>
                </div>
              )}
              {!isLoadingScan && scanReport && (
                <div className="w-full lg:w-[450px] overflow-auto bg-zinc-950 p-6 flex flex-col border-l border-zinc-800">
                  <h3 className="text-lg font-medium text-zinc-200 flex items-center gap-2 mb-4 shrink-0">
                    <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="text-blue-400"><rect width="20" height="14" x="2" y="3" rx="2"/><line x1="8" x2="16" y1="21" y2="21"/><line x1="12" x2="12" y1="17" y2="21"/></svg>
                    Scan Results
                  </h3>
                  
                  <div className="space-y-4 text-sm flex-1 flex flex-col min-h-0">
                    <div className="grid grid-cols-2 gap-4 shrink-0">
                      <div className="bg-zinc-900 p-3 rounded-lg border border-zinc-800">
                        <span className="block text-zinc-500 mb-1">Status</span>
                        <span className="text-zinc-200">{scanReport.scan_info?.status || scanReport.status || "completed"}</span>
                      </div>
                      <div className="bg-zinc-900 p-3 rounded-lg border border-zinc-800">
                        <span className="block text-zinc-500 mb-1">Load Time</span>
                        <span className="text-zinc-200">
                          {(scanReport.scan_info?.duration_seconds || scanReport.timing?.duration_seconds) !== undefined 
                            ? `${(scanReport.scan_info?.duration_seconds || scanReport.timing?.duration_seconds).toFixed(2)}s` 
                            : "N/A"}
                        </span>
                      </div>
                    </div>
                    
                    <div className="bg-zinc-900 p-3 rounded-lg border border-zinc-800 shrink-0">
                      <span className="block text-zinc-500 mb-1">Final URL</span>
                      <span className="text-zinc-200 truncate block">{scanReport.scan_info?.url || scanReport.info?.url || selectedExecution.metadata?.url || "N/A"}</span>
                    </div>
                    
                    {scanReport.analysis && (
                      <div className="flex-1 min-h-0 mt-4">
                        <AnalysisViewer analysis={scanReport.analysis} />
                      </div>
                    )}
                  </div>
                </div>
              )}
            </div>

          </div>
        </div>
      )}
    </>
  );
}
