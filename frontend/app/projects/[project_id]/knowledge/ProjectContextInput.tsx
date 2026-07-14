"use client";

import { useState, useEffect } from "react";
import { Save, AlertCircle, Check } from "lucide-react";
import { useRouter } from "next/navigation";

interface ProjectContextInputProps {
  projectId: string;
  initialContext: string;
}

export default function ProjectContextInput({ projectId, initialContext }: ProjectContextInputProps) {
  const [context, setContext] = useState(initialContext || "");
  const [isSaving, setIsSaving] = useState(false);
  const [saveStatus, setSaveStatus] = useState<"idle" | "saving" | "success" | "error">("idle");
  const router = useRouter();

  useEffect(() => {
    setContext(initialContext || "");
  }, [initialContext]);

  const handleSave = async () => {
    if (context === initialContext) return;
    
    setIsSaving(true);
    setSaveStatus("saving");
    try {
      const res = await fetch(`http://127.0.0.1:8000/api/v1/projects/${projectId}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ project_context: context }),
      });

      if (!res.ok) throw new Error("Failed to save context");
      
      setSaveStatus("success");
      router.refresh();
      
      setTimeout(() => setSaveStatus("idle"), 2000);
    } catch (error) {
      setSaveStatus("error");
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <div className="rounded-xl border border-zinc-800 bg-zinc-950 shadow-sm overflow-hidden flex flex-col">
      <div className="px-6 py-4 border-b border-zinc-800 bg-zinc-900/50 flex items-center justify-between">
        <h3 className="text-lg font-medium text-zinc-100">Project Context</h3>
        <div className="flex items-center gap-2">
          {saveStatus === "success" && (
            <span className="text-xs text-emerald-400 flex items-center">
              <Check className="w-3 h-3 mr-1" /> Saved
            </span>
          )}
          {saveStatus === "error" && (
            <span className="text-xs text-red-400 flex items-center">
              <AlertCircle className="w-3 h-3 mr-1" /> Error saving
            </span>
          )}
          <button
            onClick={handleSave}
            disabled={isSaving || context === initialContext}
            className="inline-flex items-center justify-center rounded-md text-xs font-medium transition-colors bg-blue-600 text-white hover:bg-blue-700 h-8 px-3 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {isSaving ? "Saving..." : "Save Context"}
          </button>
        </div>
      </div>
      <div className="p-0">
        <textarea
          value={context}
          onChange={(e) => {
            setContext(e.target.value);
            if (saveStatus !== "idle") setSaveStatus("idle");
          }}
          placeholder="Enter any additional context, business rules, or test generation instructions here..."
          className="w-full min-h-[150px] bg-transparent border-0 text-zinc-300 p-6 focus:ring-0 focus:outline-none resize-y"
        />
      </div>
    </div>
  );
}
