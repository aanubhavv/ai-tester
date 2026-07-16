"use client";

import { useState, useEffect } from "react";
import { Download, Beaker, PlayCircle, Eye, Edit2, Check, X, CheckCircle2, AlertCircle, Circle, FileText, Save, Edit, Terminal, Copy, Undo2, ImageIcon, Minimize2, Maximize2, ZoomIn, ZoomOut, RotateCcw, Sparkles } from "lucide-react";
import { useToast } from "@/components/ui/ToastProvider";
import { useConfirm } from "@/components/ui/ConfirmProvider";
import { useRouter } from "next/navigation";
import dynamic from 'next/dynamic';

const CodeEditor = dynamic(
  () => import('@uiw/react-textarea-code-editor').then((mod) => mod.default),
  { ssr: false }
);

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
  const [isEditingScript, setIsEditingScript] = useState(false);
  const [editedScript, setEditedScript] = useState("");
  const [isImprovingScript, setIsImprovingScript] = useState(false);
  const [improveContext, setImproveContext] = useState("");
  const [showImproveInput, setShowImproveInput] = useState(false);
  const [isScreenshotExpanded, setIsScreenshotExpanded] = useState(false);
  const [zoom, setZoom] = useState(1);

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

  const handleCopyScript = () => {
    if (scriptViewerCase?.script) {
      navigator.clipboard.writeText(scriptViewerCase.script);
      success("Script copied to clipboard.");
    }
  };

  const handleSaveScript = async () => {
    if (!scriptViewerCase) return;
    try {
      const response = await fetch(`http://127.0.0.1:8000/api/v1/projects/${projectId}/test-cases/${scriptViewerCase.id}/script`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ script: editedScript }),
      });
      if (!response.ok) throw new Error("Failed to update script");
      
      setScriptViewerCase({ ...scriptViewerCase, script: editedScript });
      setIsEditingScript(false);
      success("Script updated successfully.");
      router.refresh();
    } catch (e) {
      error("Failed to update script.");
    }
  };

  const handleImproveScript = async () => {
    if (!scriptViewerCase || !improveContext.trim()) return;
    setIsImprovingScript(true);
    try {
      const response = await fetch(`http://127.0.0.1:8000/api/v1/projects/${projectId}/test-cases/${scriptViewerCase.id}/scripts/improve`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ 
          context: improveContext,
          old_script: scriptViewerCase.script || ""
        }),
      });
      if (!response.ok) throw new Error("Failed to improve script");
      
      const data = await response.json();
      setScriptViewerCase({ ...scriptViewerCase, script: data.script });
      setImproveContext("");
      setShowImproveInput(false);
      success("Script improved successfully.");
      router.refresh();
    } catch (e) {
      error("Failed to improve script.");
    } finally {
      setIsImprovingScript(false);
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
                        {tc.script_status === 'Generating' && (
                          <button 
                            onClick={async () => {
                              const confirmed = await confirm({
                                title: "Stop Generation?",
                                message: "Are you sure you want to stop generating this script?",
                                confirmText: "Yes, Stop"
                              });
                              if (confirmed) {
                                try {
                                  await fetch(`http://127.0.0.1:8000/api/v1/projects/${projectId}/test-cases/scripts/stop`, {
                                    method: "POST",
                                    headers: { "Content-Type": "application/json" },
                                    body: JSON.stringify({ test_case_ids: [tc.id] })
                                  });
                                  success("Stopped generation.");
                                  router.refresh();
                                } catch (e) { error("Failed to stop generation."); }
                              }
                            }}
                            className="p-1 rounded bg-red-500/10 text-red-400 hover:bg-red-500/20 transition-colors"
                            title="Stop Generation"
                          >
                            <X className="h-3 w-3" />
                          </button>
                        )}
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
                        {tc.execution_status === 'Running' && (
                          <button 
                            onClick={async () => {
                              const confirmed = await confirm({
                                title: "Stop Execution?",
                                message: "Are you sure you want to stop this execution?",
                                confirmText: "Yes, Stop"
                              });
                              if (confirmed) {
                                try {
                                  await fetch(`http://127.0.0.1:8000/api/v1/projects/${projectId}/test-cases/scripts/stop`, {
                                    method: "POST",
                                    headers: { "Content-Type": "application/json" },
                                    body: JSON.stringify({ test_case_ids: [tc.id] })
                                  });
                                  success("Stopped execution.");
                                  router.refresh();
                                } catch (e) { error("Failed to stop execution."); }
                              }
                            }}
                            className="p-1 rounded bg-red-500/10 text-red-400 hover:bg-red-500/20 transition-colors"
                            title="Stop Execution"
                          >
                            <X className="h-3 w-3" />
                          </button>
                        )}
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
                            {selectedCase.last_execution_error.includes('[Fixed via Self-Healing]') ? (
                              <>
                                <h4 className="text-sm font-semibold text-amber-400 mb-2 uppercase tracking-wider">Resolved Error (Self-Healed)</h4>
                                <div className="bg-amber-950/20 p-4 rounded-lg border border-amber-900/30 text-sm text-amber-200 font-mono whitespace-pre-wrap overflow-x-auto">
                                  {selectedCase.last_execution_error}
                                </div>
                              </>
                            ) : (
                              <>
                                <h4 className="text-sm font-semibold text-red-400 mb-2 uppercase tracking-wider">Error Message</h4>
                                <div className="bg-red-950/20 p-4 rounded-lg border border-red-900/30 text-sm text-red-200 font-mono whitespace-pre-wrap overflow-x-auto">
                                  {selectedCase.last_execution_error}
                                </div>
                              </>
                            )}
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

                  {/* Target Location Screenshot */}
                  {selectedCase.screenshot && selectedCase.screenshot.startsWith('/') && (
                    <div className="mt-8 border-t border-zinc-800/50 pt-6">
                      <div className="flex items-center justify-between mb-4">
                        <h3 className="text-base font-semibold text-zinc-100 flex items-center gap-2">
                          <ImageIcon className="h-4 w-4 text-emerald-400" />
                          Target Location Screenshot
                        </h3>
                        <button 
                          onClick={() => setIsScreenshotExpanded(!isScreenshotExpanded)}
                          className="p-1.5 rounded-md hover:bg-zinc-800 text-zinc-400 hover:text-zinc-200 transition-colors"
                        >
                          {isScreenshotExpanded ? <Minimize2 className="h-4 w-4" /> : <Maximize2 className="h-4 w-4" />}
                        </button>
                      </div>
                      
                      <div className={`bg-zinc-900 border border-zinc-800 rounded-lg overflow-hidden flex transition-all ${isScreenshotExpanded ? 'fixed inset-4 z-50 p-4 bg-zinc-950/95 backdrop-blur shadow-2xl flex-col' : 'relative h-[400px]'}`}>
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
                        <div className={`${isScreenshotExpanded ? 'w-full h-full overflow-auto pt-16' : 'absolute inset-0'}`}>
                          {/* eslint-disable-next-line @next/next/no-img-element */}
                          <img 
                            src={`http://127.0.0.1:8000${selectedCase.screenshot}`} 
                            alt="Target Location Screenshot" 
                            style={isScreenshotExpanded ? { width: `${zoom * 100}%`, transition: 'width 0.2s' } : {}}
                            className={`transition-all ${isScreenshotExpanded ? 'max-w-none mx-auto block' : 'w-full h-full object-cover object-top block'}`}
                          />
                        </div>
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
            <div className="flex items-center justify-between px-6 py-4 border-b border-zinc-800 bg-zinc-900/50 gap-4">
              <div className="flex items-center gap-3 min-w-0 flex-1">
                <div className="flex items-center justify-center h-8 w-8 rounded-lg bg-zinc-800 border border-zinc-700 flex-shrink-0">
                  <PlayCircle className="h-4 w-4 text-purple-400" />
                </div>
                <div className="min-w-0">
                  <h3 className="text-lg font-semibold text-zinc-100 truncate">Playwright Script</h3>
                  <p className="text-xs text-zinc-500 truncate" title={`${scriptViewerCase.tc_id} • ${scriptViewerCase.title}`}>
                    {scriptViewerCase.tc_id} • {scriptViewerCase.title}
                  </p>
                </div>
              </div>
              <div className="flex items-center gap-2 flex-shrink-0">
                <button 
                  onClick={() => setShowImproveInput(!showImproveInput)}
                  className="px-3 py-1.5 rounded-md bg-gradient-to-r from-indigo-500 via-purple-500 to-pink-500 hover:from-indigo-600 hover:via-purple-600 hover:to-pink-600 text-white text-sm font-medium transition-all shadow-md shadow-purple-500/20 flex items-center gap-1.5"
                  title="Improve with AI"
                >
                  <Sparkles className="h-4 w-4" />
                  <span>Improve with AI</span>
                </button>
                <button 
                  onClick={handleCopyScript}
                  className="p-2 text-zinc-400 hover:text-zinc-100 hover:bg-zinc-800 rounded-md transition-colors"
                  title="Copy Script"
                >
                  <Copy className="h-5 w-5" />
                </button>
                {isEditingScript ? (
                  <>
                    <button 
                      onClick={() => setIsEditingScript(false)}
                      className="p-2 text-red-400 hover:text-red-300 hover:bg-zinc-800 rounded-md transition-colors"
                      title="Cancel Edit"
                    >
                      <Undo2 className="h-5 w-5" />
                    </button>
                    <button 
                      onClick={handleSaveScript}
                      className="p-2 text-green-400 hover:text-green-300 hover:bg-zinc-800 rounded-md transition-colors"
                      title="Save Script"
                    >
                      <Save className="h-5 w-5" />
                    </button>
                  </>
                ) : (
                  <button 
                    onClick={() => { setIsEditingScript(true); setEditedScript(scriptViewerCase.script || ""); }}
                    className="p-2 text-zinc-400 hover:text-zinc-100 hover:bg-zinc-800 rounded-md transition-colors"
                    title="Edit Script"
                  >
                    <Edit2 className="h-5 w-5" />
                  </button>
                )}
                <button 
                  onClick={() => { setScriptViewerCase(null); setIsEditingScript(false); setShowImproveInput(false); }}
                  className="p-2 text-zinc-400 hover:text-zinc-100 hover:bg-zinc-800 rounded-md transition-colors"
                  title="Close"
                >
                  <X className="h-5 w-5" />
                </button>
              </div>
            </div>
            
            {showImproveInput && (
              <div className="px-6 py-3 bg-indigo-950/20 border-b border-indigo-900/30 flex gap-3 items-center">
                <Sparkles className="h-4 w-4 text-purple-400 flex-shrink-0" />
                <input 
                  type="text"
                  value={improveContext}
                  onChange={(e) => setImproveContext(e.target.value)}
                  placeholder="Tell AI how to improve this script (e.g. 'Use standard test data instead of generic strings')"
                  className="flex-1 bg-transparent border-none focus:outline-none text-sm text-zinc-200 placeholder:text-zinc-500"
                  disabled={isImprovingScript}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter') handleImproveScript();
                  }}
                />
                <button 
                  onClick={handleImproveScript}
                  disabled={isImprovingScript || !improveContext.trim()}
                  className="px-3 py-1.5 bg-purple-600 hover:bg-purple-700 text-white rounded-md text-xs font-medium transition-colors disabled:opacity-50 whitespace-nowrap"
                >
                  {isImprovingScript ? "Improving..." : "Apply"}
                </button>
              </div>
            )}
            
            <div className="p-6 bg-zinc-950 max-h-[70vh] overflow-y-auto w-full">
              <div className="rounded-lg overflow-hidden border border-zinc-700 relative">
                {isImprovingScript && (
                  <div className="absolute inset-0 z-10 flex flex-col items-center justify-center bg-black/60 backdrop-blur-sm">
                    <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500 mb-2"></div>
                    <span className="text-sm font-medium text-blue-400">Regenerating script...</span>
                  </div>
                )}
                {isEditingScript ? (
                  <CodeEditor
                    value={editedScript}
                    language="typescript"
                    placeholder="Please enter TS code."
                    onChange={(evn) => setEditedScript(evn.target.value)}
                    padding={20}
                    style={{
                      fontSize: '0.875rem',
                      backgroundColor: '#0d1117',
                      fontFamily: 'ui-monospace,SFMono-Regular,SF Mono,Consolas,Liberation Mono,Menlo,monospace',
                      minHeight: '500px'
                    }}
                  />
                ) : (
                  <CodeEditor
                    value={scriptViewerCase.script || '// No script generated yet.'}
                    language="typescript"
                    readOnly={true}
                    padding={20}
                    style={{
                      fontSize: '0.875rem',
                      backgroundColor: '#0d1117',
                      fontFamily: 'ui-monospace,SFMono-Regular,SF Mono,Consolas,Liberation Mono,Menlo,monospace',
                      minHeight: '500px'
                    }}
                  />
                )}
              </div>
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
