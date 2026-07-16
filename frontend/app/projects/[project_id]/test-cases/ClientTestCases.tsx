"use client";

import { useState, useEffect } from "react";
import { Download, Beaker, PlayCircle, Eye, Edit2, Check, X, CheckCircle2, AlertCircle, Circle, FileText, Save, Edit, Terminal } from "lucide-react";
import { useToast } from "@/components/ui/ToastProvider";
import { useConfirm } from "@/components/ui/ConfirmProvider";
import { useRouter } from "next/navigation";

export default function ClientTestCases({ initialTestCases, projectId }: { initialTestCases: any[], projectId: string }) {
  const router = useRouter();
  const { success, error } = useToast();
  const { confirm } = useConfirm();
  const [selectedCase, setSelectedCase] = useState<any | null>(null);
  const [isEditing, setIsEditing] = useState(false);
  const [editedCase, setEditedCase] = useState<any | null>(null);
  const [isSaving, setIsSaving] = useState(false);
  const [selectedTestIds, setSelectedTestIds] = useState<string[]>([]);
  const [scriptViewerCase, setScriptViewerCase] = useState<any | null>(null);

  useEffect(() => {
    // Poll for updates if any scripts are generating or queued
    const hasActiveJobs = initialTestCases.some(tc => 
      ['Queued', 'Generating'].includes(tc.script_status) || 
      ['Queued', 'Preparing', 'Running'].includes(tc.execution_status)
    );

    if (hasActiveJobs) {
      const interval = setInterval(() => {
        router.refresh();
      }, 3000);
      return () => clearInterval(interval);
    }
  }, [initialTestCases, router]);

  const toggleSelectAll = () => {
    if (selectedTestIds.length === initialTestCases.length) {
      setSelectedTestIds([]);
    } else {
      setSelectedTestIds(initialTestCases.map(tc => tc.id));
    }
  };

  const toggleSelect = (id: string) => {
    setSelectedTestIds(prev => 
      prev.includes(id) ? prev.filter(t => t !== id) : [...prev, id]
    );
  };

  const getStatusIcon = (status: string) => {
    if (!status) return <Circle className="h-4 w-4 text-zinc-500" />;
    const s = status.toLowerCase();
    if (s.includes('pass') || s.includes('approved')) return <CheckCircle2 className="h-4 w-4 text-emerald-500" />;
    if (s.includes('fail')) return <AlertCircle className="h-4 w-4 text-red-500" />;
    if (s.includes('blocked')) return <AlertCircle className="h-4 w-4 text-orange-500" />;
    return <Circle className="h-4 w-4 text-zinc-500" />;
  };

  const handleGenerate = async () => {
    if (initialTestCases.length > 0) {
      const confirmed = await confirm({
        title: "Regenerate Test Cases",
        message: "This action will delete your previously generated test cases. Do you want to still continue?",
        confirmText: "Yes, Regenerate",
        cancelText: "Cancel"
      });
      if (!confirmed) return;
    }

    try {
      const res = await fetch(`http://127.0.0.1:8000/api/v1/projects/${projectId}/test-cases/generate`, {
        method: "POST"
      });
      if (res.ok) {
        success("Test generation started in the background. Check back in a few minutes.");
      } else {
        const errorData = await res.json().catch(() => ({}));
        error(`Failed to start generation: ${errorData.detail || 'Unknown error'}`);
      }
    } catch (e) {
      console.error(e);
      error("Failed to start generation.");
    }
  };

  const handleExport = () => {
    window.open(`http://127.0.0.1:8000/api/v1/projects/${projectId}/test-cases/export/xlsx`, '_blank');
  };

  const startEditing = () => {
    setEditedCase({ ...selectedCase });
    setIsEditing(true);
  };

  const cancelEditing = () => {
    setIsEditing(false);
    setEditedCase(null);
  };

  const handleSave = async () => {
    if (!editedCase) return;
    setIsSaving(true);
    try {
      const res = await fetch(`http://127.0.0.1:8000/api/v1/projects/${projectId}/test-cases/${editedCase.id}`, {
        method: "PATCH",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify(editedCase)
      });
      
      if (res.ok) {
        const updated = await res.json();
        setSelectedCase(updated);
        setIsEditing(false);
        router.refresh();
        success("Changes saved successfully.");
      } else {
        error("Failed to save changes.");
      }
    } catch (e) {
      console.error(e);
      error("An error occurred while saving.");
    } finally {
      setIsSaving(false);
    }
  };

  const handleChange = (field: string, value: string) => {
    setEditedCase((prev: any) => ({ ...prev, [field]: value }));
  };

  const handleQuickStatusChange = async (tcId: string, newStatus: string) => {
    const tcToUpdate = initialTestCases.find(tc => tc.id === tcId);
    if (!tcToUpdate) return;
    
    // Optimistic UI update could go here, but for simplicity we rely on router.refresh()
    try {
      const updatedData = { ...tcToUpdate, status: newStatus };
      const res = await fetch(`http://127.0.0.1:8000/api/v1/projects/${projectId}/test-cases/${tcId}`, {
        method: "PATCH",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify(updatedData)
      });
      
      if (res.ok) {
        router.refresh();
        success("Status updated successfully.");
      } else {
        error("Failed to update status.");
      }
    } catch (e) {
      console.error(e);
      error("An error occurred while saving status.");
    }
  };

  const renderFormattedText = (text: string | undefined | null) => {
    if (!text) return null;
    const withNewlines = text.replace(/<br\s*\/?>/gi, '\n');
    const parts = withNewlines.split(/(\*\*.*?\*\*)/g);
    return parts.map((part, i) => {
      if (part.startsWith('**') && part.endsWith('**')) {
        return <strong key={i} className="font-semibold text-zinc-100">{part.slice(2, -2)}</strong>;
      }
      return <span key={i}>{part}</span>;
    });
  };

  return (
    <div className="flex flex-col h-full bg-black text-zinc-300">
      <div className="flex-none p-6 border-b border-zinc-800 flex items-center justify-between bg-zinc-950/50 backdrop-blur-sm z-10 sticky top-0">
        <div>
          <h2 className="text-xl font-semibold text-zinc-100 flex items-center gap-2">
            <Beaker className="h-5 w-5 text-blue-400" />
            Test Cases
          </h2>
          <p className="text-sm text-zinc-500 mt-1">Generated test cases in tabular format.</p>
        </div>
        <div className="flex items-center gap-3">
          <button 
            onClick={handleExport}
            className="px-4 py-2 bg-zinc-800 hover:bg-zinc-700 text-zinc-200 rounded-md text-sm font-medium transition-colors border border-zinc-700 flex items-center gap-2"
          >
            <Download className="h-4 w-4" />
            Export to Excel
          </button>
          {selectedTestIds.length > 0 && (
            <>
              <button 
                onClick={async () => {
                  try {
                    await fetch(`http://127.0.0.1:8000/api/v1/projects/${projectId}/test-cases/scripts/generate`, {
                      method: "POST",
                      headers: { "Content-Type": "application/json" },
                      body: JSON.stringify({ test_case_ids: selectedTestIds })
                    });
                    success("Script generation queued!");
                    setSelectedTestIds([]);
                    router.refresh();
                  } catch(e) { error("Failed to queue generation."); }
                }}
                className="px-4 py-2 bg-purple-600 hover:bg-purple-700 text-white rounded-md text-sm font-medium transition-colors shadow-sm shadow-purple-900/20 flex items-center gap-2"
              >
                Generate Scripts
              </button>
              <button 
                onClick={async () => {
                  try {
                    await fetch(`http://127.0.0.1:8000/api/v1/projects/${projectId}/test-cases/scripts/execute`, {
                      method: "POST",
                      headers: { "Content-Type": "application/json" },
                      body: JSON.stringify({ test_case_ids: selectedTestIds })
                    });
                    success("Script execution queued!");
                    setSelectedTestIds([]);
                    router.refresh();
                  } catch(e) { error("Failed to queue execution."); }
                }}
                className="px-4 py-2 bg-emerald-600 hover:bg-emerald-700 text-white rounded-md text-sm font-medium transition-colors shadow-sm shadow-emerald-900/20 flex items-center gap-2"
              >
                <PlayCircle className="h-4 w-4" />
                Execute Selected
              </button>
              <button 
                onClick={async () => {
                  try {
                    await fetch(`http://127.0.0.1:8000/api/v1/projects/${projectId}/test-cases/scripts/stop`, {
                      method: "POST",
                      headers: { "Content-Type": "application/json" },
                      body: JSON.stringify({ test_case_ids: selectedTestIds })
                    });
                    success("Sent stop signal!");
                    setSelectedTestIds([]);
                    router.refresh();
                  } catch(e) { error("Failed to send stop signal."); }
                }}
                className="px-4 py-2 bg-red-600 hover:bg-red-700 text-white rounded-md text-sm font-medium transition-colors shadow-sm shadow-red-900/20 flex items-center gap-2"
              >
                <X className="h-4 w-4" />
                Stop Execution
              </button>
            </>
          )}
          <button 
            onClick={handleGenerate}
            className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-md text-sm font-medium transition-colors shadow-sm shadow-blue-900/20 flex items-center gap-2"
          >
            <Beaker className="h-4 w-4" />
            {initialTestCases.length > 0 ? "Regenerate Base Tests" : "Generate Test Cases"}
          </button>
        </div>
      </div>

      <div className="flex-1 overflow-auto">
        {initialTestCases.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full p-12 text-center">
            <div className="h-12 w-12 rounded-full bg-zinc-900 flex items-center justify-center mb-4">
              <Beaker className="h-6 w-6 text-zinc-500" />
            </div>
            <h3 className="text-lg font-medium text-zinc-200">No test cases yet</h3>
            <p className="text-sm text-zinc-500 mt-1 max-w-md">
              Generate test cases from your requirements and knowledge base context.
            </p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-zinc-800 text-left text-sm whitespace-nowrap">
              <thead className="bg-zinc-900/80 sticky top-0 z-10">
                <tr>
                  <th className="px-4 py-3 text-center">
                    <input 
                      type="checkbox" 
                      checked={initialTestCases.length > 0 && selectedTestIds.length === initialTestCases.length}
                      onChange={toggleSelectAll}
                      className="rounded border-zinc-700 bg-zinc-800 text-blue-600 focus:ring-blue-500/20"
                    />
                  </th>
                  <th className="px-4 py-3 font-semibold text-zinc-300">TC ID</th>
                  <th className="px-4 py-3 font-semibold text-zinc-300">Type</th>
                  <th className="px-4 py-3 font-semibold text-zinc-300">Title</th>
                  <th className="px-4 py-3 font-semibold text-zinc-300">Severity</th>
                  <th className="px-4 py-3 font-semibold text-zinc-300">Test Status</th>
                  <th className="px-4 py-3 font-semibold text-zinc-300">Script Status</th>
                  <th className="px-4 py-3 font-semibold text-zinc-300">Execution</th>
                  <th className="px-4 py-3 font-semibold text-zinc-300">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-zinc-800/50">
                {initialTestCases.map((tc) => (
                  <tr key={tc.id} className={`hover:bg-zinc-900/30 transition-colors ${selectedTestIds.includes(tc.id) ? 'bg-zinc-900/50' : ''}`}>
                    <td className="px-4 py-3 text-center">
                      <input 
                        type="checkbox" 
                        checked={selectedTestIds.includes(tc.id)}
                        onChange={() => toggleSelect(tc.id)}
                        className="rounded border-zinc-700 bg-zinc-800 text-blue-600 focus:ring-blue-500/20"
                      />
                    </td>
                    <td className="px-4 py-3 font-medium text-zinc-300">{tc.tc_id}</td>
                    <td className="px-4 py-3 text-zinc-400">
                      <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-zinc-800 text-zinc-300 border border-zinc-700">
                        {tc.test_type}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-zinc-200 font-medium truncate max-w-[200px]" title={tc.title}>
                      {tc.title}
                    </td>
                    <td className="px-4 py-3 text-zinc-400">{tc.severity}</td>
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-2">
                        {getStatusIcon(tc.status)}
                        <select 
                          value={tc.status}
                          onChange={(e) => handleQuickStatusChange(tc.id, e.target.value)}
                          className="bg-transparent text-zinc-300 font-medium cursor-pointer hover:text-zinc-100 focus:outline-none focus:ring-1 focus:ring-zinc-700 rounded px-1 -ml-1"
                        >
                          <option value="Pass" className="bg-zinc-900">Pass</option>
                          <option value="Fail" className="bg-zinc-900">Fail</option>
                          <option value="Blocked" className="bg-zinc-900">Blocked</option>
                          <option value="Not Executed" className="bg-zinc-900">Not Executed</option>
                        </select>
                      </div>
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-2">
                        <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium border
                          ${tc.script_status === 'Generated' ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20' :
                            tc.script_status === 'Generating' ? 'bg-blue-500/10 text-blue-400 border-blue-500/20 animate-pulse' :
                            tc.script_status === 'Failed' ? 'bg-red-500/10 text-red-400 border-red-500/20' :
                            'bg-zinc-800 text-zinc-400 border-zinc-700'
                          }
                        `}>
                          {tc.script_status || 'Not Generated'}
                        </span>
                      </div>
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-2">
                        <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium border
                          ${tc.execution_status === 'Passed' ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20' :
                            tc.execution_status === 'Failed' ? 'bg-red-500/10 text-red-400 border-red-500/20' :
                            tc.execution_status === 'Running' ? 'bg-purple-500/10 text-purple-400 border-purple-500/20 animate-pulse' :
                            'bg-zinc-800 text-zinc-400 border-zinc-700'
                          }
                        `}>
                          {tc.execution_status || 'Not Executed'}
                        </span>
                      </div>
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-3">
                        <button 
                          onClick={() => setSelectedCase(tc)}
                          className="text-blue-400 hover:text-blue-300 font-medium text-sm transition-colors"
                        >
                          Details
                        </button>
                        {tc.script_status === 'Generated' && (
                          <button 
                            onClick={() => setScriptViewerCase(tc)}
                            className="text-purple-400 hover:text-purple-300 font-medium text-sm transition-colors"
                          >
                            Script
                          </button>
                        )}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Details Modal */}
      {selectedCase && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4 sm:p-6">
          <div className="bg-zinc-950 border border-zinc-800 rounded-xl shadow-2xl w-full max-w-5xl max-h-[90vh] flex flex-col overflow-hidden animate-in fade-in zoom-in-95 duration-200">
            <div className="flex items-center justify-between px-6 py-4 border-b border-zinc-800 bg-zinc-900/50">
              <div className="flex items-center gap-3">
                <div className="flex items-center justify-center h-8 w-8 rounded-lg bg-zinc-800 border border-zinc-700">
                  <FileText className="h-4 w-4 text-zinc-400" />
                </div>
                <div>
                  <h3 className="text-lg font-medium text-zinc-100 flex items-center gap-2">
                    {isEditing ? (
                      <input 
                        type="text" 
                        value={editedCase?.title} 
                        onChange={(e) => handleChange('title', e.target.value)}
                        className="bg-zinc-900 border border-zinc-700 rounded px-2 py-1 text-sm w-96 text-zinc-100"
                      />
                    ) : (
                      <>{selectedCase.tc_id}: {selectedCase.title}</>
                    )}
                  </h3>
                  {!isEditing && (
                    <div className="flex items-center gap-2 text-xs text-zinc-500 mt-0.5">
                      <span>{selectedCase.module_area}</span>
                      <span>•</span>
                      <span className="uppercase">{selectedCase.test_type}</span>
                    </div>
                  )}
                </div>
              </div>
              <div className="flex items-center gap-3">
                {isEditing ? (
                  <>
                    <button 
                      onClick={cancelEditing}
                      className="px-3 py-1.5 text-sm font-medium bg-zinc-800 hover:bg-zinc-700 text-zinc-300 rounded-md transition-colors"
                    >
                      Cancel
                    </button>
                    <button 
                      onClick={handleSave}
                      disabled={isSaving}
                      className="px-3 py-1.5 text-sm font-medium bg-emerald-600 hover:bg-emerald-700 text-white rounded-md transition-colors flex items-center gap-2 disabled:opacity-50"
                    >
                      <Save className="h-4 w-4" />
                      {isSaving ? "Saving..." : "Save Changes"}
                    </button>
                  </>
                ) : (
                  <button 
                    onClick={startEditing}
                    className="px-3 py-1.5 text-sm font-medium bg-zinc-800 hover:bg-zinc-700 text-zinc-200 rounded-md transition-colors flex items-center gap-2 border border-zinc-700"
                  >
                    <Edit className="h-4 w-4" />
                    Edit
                  </button>
                )}
                <div className="w-px h-6 bg-zinc-800 mx-1"></div>
                <button 
                  onClick={() => { setSelectedCase(null); setIsEditing(false); }} 
                  className="text-zinc-400 hover:text-zinc-200 transition-colors p-1 hover:bg-zinc-800 rounded-md"
                >
                  <X className="h-5 w-5" />
                </button>
              </div>
            </div>
            
            <div className="flex-1 overflow-y-auto p-6">
              <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                
                {/* Main Content */}
                <div className="md:col-span-2 space-y-6">
                  <div>
                    <h4 className="text-sm font-semibold text-zinc-100 mb-2 uppercase tracking-wider">Preconditions</h4>
                    {isEditing ? (
                      <textarea 
                        value={editedCase?.preconditions}
                        onChange={(e) => handleChange('preconditions', e.target.value)}
                        className="w-full bg-zinc-900 border border-zinc-700 rounded-lg p-3 text-sm text-zinc-300 min-h-[80px]"
                      />
                    ) : (
                      <div className="bg-zinc-900/50 p-4 rounded-lg border border-zinc-800/50 text-sm text-zinc-300 leading-relaxed whitespace-pre-wrap">
                        {renderFormattedText(selectedCase.preconditions) || "None"}
                      </div>
                    )}
                  </div>
                  
                  <div>
                    <h4 className="text-sm font-semibold text-zinc-100 mb-2 uppercase tracking-wider">Test Steps</h4>
                    {isEditing ? (
                      <textarea 
                        value={editedCase?.test_steps}
                        onChange={(e) => handleChange('test_steps', e.target.value)}
                        className="w-full bg-zinc-900 border border-zinc-700 rounded-lg p-3 text-sm text-zinc-300 min-h-[120px]"
                      />
                    ) : (
                      <div className="bg-zinc-900/50 p-4 rounded-lg border border-zinc-800/50 text-sm text-zinc-300 leading-relaxed whitespace-pre-wrap">
                        {renderFormattedText(selectedCase.test_steps)}
                      </div>
                    )}
                  </div>
                  
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                    <div>
                      <h4 className="text-sm font-semibold text-zinc-100 mb-2 uppercase tracking-wider">Expected Result</h4>
                      {isEditing ? (
                        <textarea 
                          value={editedCase?.expected_result}
                          onChange={(e) => handleChange('expected_result', e.target.value)}
                          className="w-full bg-zinc-900 border border-zinc-700 rounded-lg p-3 text-sm text-zinc-300 min-h-[100px]"
                        />
                      ) : (
                        <div className="bg-zinc-900/50 p-4 rounded-lg border border-zinc-800/50 text-sm text-zinc-300 leading-relaxed whitespace-pre-wrap h-full">
                          {renderFormattedText(selectedCase.expected_result)}
                        </div>
                      )}
                    </div>
                    <div>
                      <h4 className="text-sm font-semibold text-zinc-100 mb-2 uppercase tracking-wider">Actual Result</h4>
                      {isEditing ? (
                        <textarea 
                          value={editedCase?.actual_result}
                          onChange={(e) => handleChange('actual_result', e.target.value)}
                          className="w-full bg-zinc-900 border border-zinc-700 rounded-lg p-3 text-sm text-zinc-300 min-h-[100px]"
                        />
                      ) : (
                        <div className="bg-zinc-900/50 p-4 rounded-lg border border-zinc-800/50 text-sm text-zinc-300 leading-relaxed whitespace-pre-wrap h-full">
                          {renderFormattedText(selectedCase.actual_result) || "N/A"}
                        </div>
                      )}
                    </div>
                  </div>
                  
                  {/* Execution Results Section */}
                  {(selectedCase.last_execution_error || selectedCase.execution_logs) && (
                    <div className="mt-8 border-t border-zinc-800/50 pt-6">
                      <h3 className="text-base font-semibold text-zinc-100 flex items-center gap-2 mb-4">
                        <Terminal className="h-4 w-4 text-zinc-400" />
                        Execution Output
                      </h3>
                      <div className="space-y-4">
                        {selectedCase.last_execution_error && (
                          <div>
                            <h4 className="text-sm font-semibold text-red-400 mb-2 uppercase tracking-wider">Error Message</h4>
                            <div className="bg-red-950/20 p-4 rounded-lg border border-red-900/30 text-sm text-red-200 font-mono whitespace-pre-wrap overflow-x-auto">
                              {selectedCase.last_execution_error}
                            </div>
                          </div>
                        )}
                        {selectedCase.execution_logs && (
                          <div>
                            <h4 className="text-sm font-semibold text-zinc-400 mb-2 uppercase tracking-wider">Console Logs</h4>
                            <div className="bg-[#0d1117] p-4 rounded-lg border border-zinc-800 text-xs text-zinc-300 font-mono whitespace-pre-wrap overflow-x-auto max-h-[300px] overflow-y-auto">
                              {selectedCase.execution_logs}
                            </div>
                          </div>
                        )}
                      </div>
                    </div>
                  )}
                </div>
                
                {/* Sidebar */}
                <div className="space-y-6">
                  {isEditing && (
                    <div className="bg-zinc-900/30 p-5 rounded-lg border border-zinc-800/50">
                      <h4 className="text-xs font-semibold text-zinc-500 uppercase tracking-wider mb-4">Edit Identifiers</h4>
                      <div className="space-y-4">
                        <div>
                          <label className="block text-xs text-zinc-500 mb-1">TC ID</label>
                          <input type="text" value={editedCase?.tc_id} onChange={(e) => handleChange('tc_id', e.target.value)} className="w-full bg-zinc-900 border border-zinc-700 rounded px-2 py-1.5 text-sm text-zinc-300" />
                        </div>
                        <div>
                          <label className="block text-xs text-zinc-500 mb-1">Module / Area</label>
                          <input type="text" value={editedCase?.module_area} onChange={(e) => handleChange('module_area', e.target.value)} className="w-full bg-zinc-900 border border-zinc-700 rounded px-2 py-1.5 text-sm text-zinc-300" />
                        </div>
                        <div>
                          <label className="block text-xs text-zinc-500 mb-1">Test Type</label>
                          <input type="text" value={editedCase?.test_type} onChange={(e) => handleChange('test_type', e.target.value)} className="w-full bg-zinc-900 border border-zinc-700 rounded px-2 py-1.5 text-sm text-zinc-300" />
                        </div>
                      </div>
                    </div>
                  )}

                  <div className="bg-zinc-900/30 p-5 rounded-lg border border-zinc-800/50">
                    <h4 className="text-xs font-semibold text-zinc-500 uppercase tracking-wider mb-4">Metadata</h4>
                    <div className="space-y-4">
                      <div>
                        <label className="block text-xs text-zinc-500 mb-1">Status</label>
                        {isEditing ? (
                          <select 
                            value={editedCase?.status || "Not Executed"} 
                            onChange={(e) => handleChange('status', e.target.value)} 
                            className="w-full bg-zinc-900 border border-zinc-700 rounded px-2 py-1 text-sm text-zinc-300 outline-none focus:border-zinc-500"
                          >
                            <option value="Not Executed">Not Executed</option>
                            <option value="Pass">Pass</option>
                            <option value="Fail">Fail</option>
                            <option value="Blocked">Blocked</option>
                          </select>
                        ) : (
                          <div className="flex items-center gap-2">
                            {getStatusIcon(selectedCase.status)}
                            <span className="text-sm font-medium text-zinc-300">{selectedCase.status}</span>
                          </div>
                        )}
                      </div>
                      <div>
                        <label className="block text-xs text-zinc-500 mb-1">Severity</label>
                        {isEditing ? (
                          <input type="text" value={editedCase?.severity} onChange={(e) => handleChange('severity', e.target.value)} className="w-full bg-zinc-900 border border-zinc-700 rounded px-2 py-1 text-sm text-zinc-300" />
                        ) : (
                          <span className="text-sm font-medium text-zinc-300">{selectedCase.severity}</span>
                        )}
                      </div>
                      <div>
                        <label className="block text-xs text-zinc-500 mb-1">Priority</label>
                        {isEditing ? (
                          <input type="text" value={editedCase?.priority} onChange={(e) => handleChange('priority', e.target.value)} className="w-full bg-zinc-900 border border-zinc-700 rounded px-2 py-1 text-sm text-zinc-300" />
                        ) : (
                          <span className="text-sm font-medium text-zinc-300">{selectedCase.priority}</span>
                        )}
                      </div>
                    </div>
                  </div>

                  <div>
                    <h4 className="text-sm font-semibold text-zinc-100 mb-2 uppercase tracking-wider">Remarks</h4>
                    {isEditing ? (
                      <textarea 
                        value={editedCase?.remarks}
                        onChange={(e) => handleChange('remarks', e.target.value)}
                        className="w-full bg-zinc-900 border border-zinc-700 rounded-lg p-3 text-sm text-zinc-300 min-h-[80px]"
                      />
                    ) : (
                      <div className="bg-zinc-900/50 p-4 rounded-lg border border-zinc-800/50 text-sm text-zinc-300 leading-relaxed whitespace-pre-wrap">
                        {renderFormattedText(selectedCase.remarks) || "No remarks."}
                      </div>
                    )}
                  </div>
                </div>

              </div>
            </div>
          </div>
        </div>
      )}

      {/* Script Viewer Modal */}
      {scriptViewerCase && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4 sm:p-6">
          <div className="bg-zinc-950 border border-zinc-800 rounded-xl shadow-2xl w-full max-w-4xl flex flex-col overflow-hidden animate-in fade-in zoom-in-95 duration-200">
            <div className="flex items-center justify-between px-6 py-4 border-b border-zinc-800 bg-zinc-900/50">
              <div className="flex items-center gap-3">
                <div className="flex items-center justify-center h-8 w-8 rounded-lg bg-zinc-800 border border-zinc-700">
                  <PlayCircle className="h-4 w-4 text-purple-400" />
                </div>
                <div>
                  <h3 className="text-lg font-semibold text-zinc-100">Playwright Script</h3>
                  <p className="text-xs text-zinc-500">{scriptViewerCase.tc_id} • {scriptViewerCase.title}</p>
                </div>
              </div>
              <button 
                onClick={() => setScriptViewerCase(null)}
                className="p-2 text-zinc-400 hover:text-zinc-100 hover:bg-zinc-800 rounded-md transition-colors"
              >
                <X className="h-5 w-5" />
              </button>
            </div>
            
            <div className="p-6 bg-zinc-950 max-h-[70vh] overflow-y-auto">
              <pre className="bg-[#0d1117] text-zinc-300 p-4 rounded-lg text-sm font-mono overflow-x-auto whitespace-pre-wrap border border-zinc-800">
                <code>{scriptViewerCase.script || '// No script generated yet.'}</code>
              </pre>
            </div>
            
            <div className="flex justify-between items-center px-6 py-4 border-t border-zinc-800 bg-zinc-900/30">
              <div className="text-xs text-zinc-500">
                {scriptViewerCase.script_metadata?.generated_at ? `Generated at: ${new Date(scriptViewerCase.script_metadata.generated_at).toLocaleString()}` : ''}
              </div>
              <button 
                onClick={() => setScriptViewerCase(null)}
                className="px-5 py-2 bg-zinc-800 hover:bg-zinc-700 text-zinc-100 rounded-md text-sm font-medium transition-colors"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
