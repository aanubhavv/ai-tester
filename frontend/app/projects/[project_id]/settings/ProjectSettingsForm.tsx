"use client";

import { useState } from "react";
import { Save, Check } from "lucide-react";
import { useRouter } from "next/navigation";

interface ProjectSettingsFormProps {
  project: {
    project_id: string;
    name: string;
    primary_url: string;
    description: string;
  };
}

export default function ProjectSettingsForm({ project }: ProjectSettingsFormProps) {
  const router = useRouter();
  const [name, setName] = useState(project.name || "");
  const [primaryUrl, setPrimaryUrl] = useState(project.primary_url || "");
  const [description, setDescription] = useState(project.description || "");
  
  const [isSaving, setIsSaving] = useState(false);
  const [saveStatus, setSaveStatus] = useState<"idle" | "saving" | "success" | "error">("idle");

  const handleSave = async () => {
    setIsSaving(true);
    setSaveStatus("saving");
    
    try {
      const res = await fetch(`http://127.0.0.1:8000/api/v1/projects/${project.project_id}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ 
          name,
          primary_url: primaryUrl,
          description
        }),
      });

      if (!res.ok) throw new Error("Failed to save settings");
      
      setSaveStatus("success");
      router.refresh();
      
      setTimeout(() => setSaveStatus("idle"), 2000);
    } catch (error) {
      console.error(error);
      setSaveStatus("error");
      setTimeout(() => setSaveStatus("idle"), 3000);
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <div className="space-y-4">
      <div>
        <label className="block text-sm font-medium text-zinc-400 mb-1">Project Name</label>
        <input 
          type="text" 
          value={name}
          onChange={(e) => setName(e.target.value)}
          className="w-full bg-zinc-900 border border-zinc-800 rounded-md px-3 py-2 text-zinc-200 focus:outline-none focus:border-blue-500 transition-colors" 
        />
      </div>
      
      <div>
        <label className="block text-sm font-medium text-zinc-400 mb-1">Primary URL</label>
        <input 
          type="text" 
          placeholder="https://example.com"
          value={primaryUrl}
          onChange={(e) => setPrimaryUrl(e.target.value)}
          className="w-full bg-zinc-900 border border-zinc-800 rounded-md px-3 py-2 text-zinc-200 focus:outline-none focus:border-blue-500 transition-colors" 
        />
      </div>
      
      <div>
        <label className="block text-sm font-medium text-zinc-400 mb-1">Description</label>
        <textarea 
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          rows={3}
          className="w-full bg-zinc-900 border border-zinc-800 rounded-md px-3 py-2 text-zinc-200 focus:outline-none focus:border-blue-500 transition-colors resize-y" 
        />
      </div>

      <div className="flex justify-end pt-2">
        <button
          onClick={handleSave}
          disabled={isSaving}
          className={`inline-flex items-center justify-center rounded-md text-sm font-medium transition-colors h-10 px-4 py-2 ${
            saveStatus === "success" 
              ? "bg-emerald-600 hover:bg-emerald-700 text-white" 
              : "bg-blue-600 hover:bg-blue-700 text-white disabled:opacity-50"
          }`}
        >
          {saveStatus === "success" ? (
            <>
              <Check className="mr-2 h-4 w-4" />
              Saved
            </>
          ) : (
            <>
              <Save className="mr-2 h-4 w-4" />
              {isSaving ? "Saving..." : "Save Settings"}
            </>
          )}
        </button>
      </div>
    </div>
  );
}
