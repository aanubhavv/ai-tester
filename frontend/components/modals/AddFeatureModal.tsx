"use client";

import { useState } from "react";
import { X, Layers, AlertCircle } from "lucide-react";
import { useRouter } from "next/navigation";

interface AddFeatureModalProps {
  projectId: string;
}

export default function AddFeatureModal({ projectId }: AddFeatureModalProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  
  const router = useRouter();

  const handleOpen = () => setIsOpen(true);
  const handleClose = () => {
    if (isSubmitting) return;
    setIsOpen(false);
    setName("");
    setDescription("");
    setError(null);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name) {
      setError("Feature name is required.");
      return;
    }

    setIsSubmitting(true);
    setError(null);

    try {
      const payload = {
        name,
        description,
      };

      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000'}/api/v1/projects/${projectId}/features`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(payload),
      });

      if (!res.ok) {
        throw new Error("Failed to add feature");
      }

      router.refresh();
      handleClose();
    } catch (err: any) {
      setError(err.message || "An error occurred.");
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <>
      <button 
        onClick={handleOpen}
        className="inline-flex items-center justify-center rounded-md text-sm font-medium transition-colors border border-zinc-700 bg-zinc-900 text-zinc-300 hover:bg-zinc-800 h-10 px-4 py-2"
      >
        <Layers className="mr-2 h-4 w-4" />
        Add Feature
      </button>

      {isOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm">
          <div className="bg-zinc-950 border border-zinc-800 rounded-xl shadow-xl w-full max-w-md overflow-hidden">
            <div className="flex items-center justify-between px-6 py-4 border-b border-zinc-800">
              <h3 className="text-lg font-medium text-zinc-100">Add Feature</h3>
              <button onClick={handleClose} disabled={isSubmitting} className="text-zinc-400 hover:text-zinc-200">
                <X className="h-5 w-5" />
              </button>
            </div>
            
            <form onSubmit={handleSubmit} className="p-6 space-y-4">
              {error && (
                <div className="bg-red-900/30 border border-red-900 text-red-400 px-4 py-3 rounded-md flex items-start text-sm">
                  <AlertCircle className="h-5 w-5 mr-2 shrink-0" />
                  {error}
                </div>
              )}

              <div>
                <label className="block text-sm font-medium text-zinc-300 mb-1">Name *</label>
                <input 
                  type="text" 
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  className="w-full bg-zinc-900 border border-zinc-800 rounded-md px-3 py-2 text-zinc-200 focus:outline-none focus:ring-1 focus:ring-blue-500" 
                  placeholder="e.g. User Authentication"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-zinc-300 mb-1">Description</label>
                <textarea 
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  className="w-full bg-zinc-900 border border-zinc-800 rounded-md px-3 py-2 text-zinc-200 focus:outline-none focus:ring-1 focus:ring-blue-500" 
                  rows={3}
                  placeholder="Describe what this feature entails"
                />
              </div>

              <div className="pt-4 flex justify-end gap-3">
                <button 
                  type="button" 
                  onClick={handleClose}
                  disabled={isSubmitting}
                  className="px-4 py-2 text-sm font-medium text-zinc-300 hover:text-white transition-colors"
                >
                  Cancel
                </button>
                <button 
                  type="submit"
                  disabled={isSubmitting}
                  className="px-4 py-2 text-sm font-medium bg-zinc-100 hover:bg-white text-zinc-900 rounded-md transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center"
                >
                  {isSubmitting ? (
                    <>
                      <div className="animate-spin mr-2 h-4 w-4 border-2 border-zinc-500 border-t-zinc-900 rounded-full" />
                      Saving...
                    </>
                  ) : "Add Feature"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </>
  );
}
