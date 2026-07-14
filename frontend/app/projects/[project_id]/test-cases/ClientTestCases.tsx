"use client";

import { useState } from "react";
import { CheckCircle2, Circle, AlertCircle, PlayCircle, Eye, Tag, Beaker, FileText, X } from "lucide-react";
import { useRouter } from "next/navigation";

export default function ClientTestCases({ initialTestCases, projectId }: { initialTestCases: any[], projectId: string }) {
  const router = useRouter();
  const [selectedCase, setSelectedCase] = useState<any | null>(null);

  const getPriorityColor = (priority: string) => {
    switch(priority?.toLowerCase()) {
      case 'critical': return 'bg-red-500/10 text-red-400 ring-red-500/20';
      case 'high': return 'bg-orange-500/10 text-orange-400 ring-orange-500/20';
      case 'medium': return 'bg-blue-500/10 text-blue-400 ring-blue-500/20';
      case 'low': return 'bg-zinc-500/10 text-zinc-400 ring-zinc-500/20';
      default: return 'bg-zinc-500/10 text-zinc-400 ring-zinc-500/20';
    }
  };

  const getStatusIcon = (status: string) => {
    switch(status?.toLowerCase()) {
      case 'approved': return <CheckCircle2 className="h-4 w-4 text-emerald-500" />;
      case 'reviewed': return <Eye className="h-4 w-4 text-blue-500" />;
      case 'draft': return <Circle className="h-4 w-4 text-zinc-500" />;
      case 'deprecated': return <AlertCircle className="h-4 w-4 text-red-500" />;
      default: return <Circle className="h-4 w-4 text-zinc-500" />;
    }
  };

  const handleApprove = async () => {
    if (!selectedCase) return;
    try {
      const res = await fetch(`http://127.0.0.1:8000/api/v1/projects/${projectId}/test-cases/${selectedCase.id}/approve`, {
        method: "POST"
      });
      if (res.ok) {
        router.refresh();
        const updated = await res.json();
        setSelectedCase(updated);
      }
    } catch (e) {
      console.error(e);
    }
  };

  return (
    <div className="flex flex-col h-[calc(100vh-140px)]">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h2 className="text-2xl font-bold text-zinc-100">Test Cases</h2>
          <p className="text-zinc-400 mt-1">Review, edit, and approve AI-generated test scenarios.</p>
        </div>
        <div className="flex items-center gap-3">
          <button className="inline-flex items-center justify-center rounded-md text-sm font-medium transition-colors border border-zinc-700 bg-zinc-900 text-zinc-300 hover:bg-zinc-800 h-10 px-4 py-2">
            Export CSV
          </button>
          <button className="inline-flex items-center justify-center rounded-md text-sm font-medium transition-colors bg-blue-600 text-white hover:bg-blue-700 h-10 px-4 py-2">
            <PlayCircle className="mr-2 h-4 w-4" />
            Run Selected
          </button>
        </div>
      </div>

      <div className="flex flex-1 gap-6 overflow-hidden">
        {/* Table View */}
        <div className={`flex flex-col bg-zinc-950 rounded-xl border border-zinc-800 overflow-hidden transition-all duration-300 ${selectedCase ? 'w-2/3' : 'w-full'}`}>
          <div className="flex-1 overflow-auto hide-scrollbar">
            {(!initialTestCases || initialTestCases.length === 0) ? (
              <div className="flex flex-col items-center justify-center h-full p-12 text-center">
                <div className="h-12 w-12 rounded-full bg-zinc-900 flex items-center justify-center mb-4">
                  <FileText className="h-6 w-6 text-zinc-500" />
                </div>
                <h3 className="text-lg font-medium text-zinc-200">No test cases found</h3>
                <p className="text-sm text-zinc-500 mt-1 max-w-sm">Generate test cases from your test suites to populate this table.</p>
              </div>
            ) : (
              <table className="min-w-full divide-y divide-zinc-800 text-left text-sm">
                <thead className="bg-zinc-900/50 sticky top-0 z-10">
                  <tr>
                    <th scope="col" className="px-6 py-4 font-semibold text-zinc-300 w-10"></th>
                    <th scope="col" className="px-6 py-4 font-semibold text-zinc-300">Title</th>
                    <th scope="col" className="px-6 py-4 font-semibold text-zinc-300">Feature</th>
                    <th scope="col" className="px-6 py-4 font-semibold text-zinc-300">Type</th>
                    <th scope="col" className="px-6 py-4 font-semibold text-zinc-300">Priority</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-zinc-800">
                  {initialTestCases.map((tc) => (
                    <tr 
                      key={tc.id} 
                      onClick={() => setSelectedCase(tc)}
                      className={`cursor-pointer transition-colors ${selectedCase?.id === tc.id ? 'bg-zinc-900 border-l-2 border-l-blue-500' : 'hover:bg-zinc-900/50 border-l-2 border-l-transparent'}`}
                    >
                      <td className="px-6 py-4">
                        <div title={tc.status}>{getStatusIcon(tc.status)}</div>
                      </td>
                      <td className="px-6 py-4">
                        <span className="font-medium text-zinc-200 block truncate max-w-xs">{tc.title}</span>
                      </td>
                      <td className="px-6 py-4">
                        <span className="text-zinc-400 truncate max-w-[150px] block">{tc.traceability?.feature_name || "Unknown"}</span>
                      </td>
                      <td className="px-6 py-4">
                        <span className="text-zinc-400">{tc.type}</span>
                      </td>
                      <td className="px-6 py-4">
                        <span className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ring-1 ring-inset ${getPriorityColor(tc.priority)}`}>
                          {tc.priority}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </div>

        {/* Details Panel */}
        {selectedCase && (
          <div className="w-1/3 flex flex-col bg-zinc-950 rounded-xl border border-zinc-800 overflow-hidden animate-in slide-in-from-right-8 duration-300">
            <div className="flex items-start justify-between px-6 py-4 border-b border-zinc-800 bg-zinc-900/30">
              <div className="flex items-center gap-2">
                <span className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ring-1 ring-inset ${getPriorityColor(selectedCase.priority)}`}>
                  {selectedCase.priority}
                </span>
                <span className="text-xs font-medium text-zinc-500 uppercase tracking-wider">{selectedCase.type}</span>
              </div>
              <button 
                onClick={() => setSelectedCase(null)}
                className="text-zinc-500 hover:text-zinc-300 transition-colors"
              >
                <X className="h-5 w-5" />
              </button>
            </div>
            
            <div className="flex-1 overflow-y-auto p-6 space-y-8 hide-scrollbar">
              <div>
                <h3 className="text-lg font-bold text-zinc-100 mb-2">{selectedCase.title}</h3>
                <p className="text-sm text-zinc-400 leading-relaxed">{selectedCase.description}</p>
                <div className="mt-3 flex items-center gap-4 text-xs text-zinc-500">
                  <span className="flex items-center gap-1"><Tag className="h-3 w-3" /> v{selectedCase.version}</span>
                  <span className="flex items-center gap-1"><Beaker className="h-3 w-3" /> {selectedCase.status}</span>
                </div>
              </div>

              {selectedCase.preconditions && (
                <div>
                  <h4 className="text-sm font-semibold text-zinc-300 mb-2 border-b border-zinc-800 pb-2">Preconditions</h4>
                  <p className="text-sm text-zinc-400">{selectedCase.preconditions}</p>
                </div>
              )}

              <div>
                <h4 className="text-sm font-semibold text-zinc-300 mb-3 border-b border-zinc-800 pb-2">Test Steps</h4>
                <div className="space-y-4">
                  {(selectedCase.steps || []).map((step: any, idx: number) => (
                    <div key={idx} className="bg-zinc-900/50 p-3 rounded-lg border border-zinc-800/50">
                      <div className="flex items-start gap-3">
                        <span className="flex items-center justify-center h-5 w-5 rounded-full bg-zinc-800 text-xs font-medium text-zinc-400 shrink-0">
                          {step.step_number || idx + 1}
                        </span>
                        <div className="space-y-2 text-sm w-full">
                          <div>
                            <span className="text-zinc-500 text-xs block mb-0.5">Action</span>
                            <span className="text-zinc-200">{step.action}</span>
                          </div>
                          {step.test_data && (
                            <div className="bg-zinc-950 p-2 rounded border border-zinc-800 font-mono text-xs text-amber-400/90 overflow-x-auto">
                              {step.test_data}
                            </div>
                          )}
                          <div className="bg-emerald-500/5 p-2 rounded border border-emerald-500/10">
                            <span className="text-emerald-500/70 text-xs block mb-0.5">Expected Result</span>
                            <span className="text-zinc-300">{step.expected_result}</span>
                          </div>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              {selectedCase.postconditions && (
                <div>
                  <h4 className="text-sm font-semibold text-zinc-300 mb-2 border-b border-zinc-800 pb-2">Postconditions</h4>
                  <p className="text-sm text-zinc-400">{selectedCase.postconditions}</p>
                </div>
              )}
            </div>

            <div className="p-4 border-t border-zinc-800 bg-zinc-900/30 flex items-center justify-end gap-2">
              <button className="px-3 py-1.5 text-sm font-medium text-zinc-300 hover:text-white transition-colors">
                Edit
              </button>
              {selectedCase.status !== 'Approved' && (
                <button 
                  onClick={handleApprove}
                  className="px-3 py-1.5 text-sm font-medium bg-emerald-600 hover:bg-emerald-700 text-white rounded-md transition-colors"
                >
                  Approve
                </button>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
