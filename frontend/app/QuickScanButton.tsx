"use client";

import { useState } from "react";
import { Play, Loader2 } from "lucide-react";
import { useRouter } from "next/navigation";

export default function QuickScanButton() {
  const router = useRouter();
  const [isOpen, setIsOpen] = useState(false);
  const [url, setUrl] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!url) return;

    setIsSubmitting(true);
    try {
      // 1. Create a new Quick Scan project
      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000'}/api/v1/projects`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          name: "Quick Scan",
          description: "Automated project created for quick scan.",
          primary_url: url
        }),
      });
      
      const data = await res.json();
      
      // 2. Redirect to the scans tab with autoScan query param
      if (data && data.project_id) {
        router.push(`/projects/${data.project_id}/scans?url=${encodeURIComponent(url)}&autoScan=true`);
      }
    } catch (error) {
      console.error("Quick scan failed:", error);
      setIsSubmitting(false);
    }
  };

  if (!isOpen) {
    return (
      <button 
        onClick={() => setIsOpen(true)} 
        className="flex items-center w-full p-3 text-sm font-medium text-zinc-300 rounded-lg hover:bg-zinc-900 transition-colors"
      >
        <Play className="mr-3 h-4 w-4 text-emerald-400" />
        Run Website Scan
      </button>
    );
  }

  return (
    <form onSubmit={handleSubmit} className="p-3 bg-zinc-900/50 rounded-lg border border-zinc-800 flex flex-col gap-2">
      <div className="flex items-center text-sm font-medium text-zinc-300">
        <Play className="mr-3 h-4 w-4 text-emerald-400" />
        Run Website Scan
      </div>
      <input
        type="url"
        required
        placeholder="https://example.com"
        className="w-full bg-zinc-950 border border-zinc-800 rounded-md px-3 py-2 text-sm text-zinc-200 focus:outline-none focus:border-blue-500 transition-colors"
        value={url}
        onChange={(e) => setUrl(e.target.value)}
        autoFocus
        disabled={isSubmitting}
      />
      <div className="flex justify-end gap-2 mt-1">
        <button
          type="button"
          onClick={() => setIsOpen(false)}
          disabled={isSubmitting}
          className="px-3 py-1.5 text-xs font-medium text-zinc-400 hover:text-zinc-200 transition-colors"
        >
          Cancel
        </button>
        <button
          type="submit"
          disabled={isSubmitting}
          className="inline-flex items-center justify-center rounded-md text-xs font-medium bg-blue-600 text-white hover:bg-blue-700 px-3 py-1.5 transition-colors disabled:opacity-50"
        >
          {isSubmitting ? (
            <Loader2 className="h-3.5 w-3.5 animate-spin" />
          ) : (
            "Start Scan"
          )}
        </button>
      </div>
    </form>
  );
}
