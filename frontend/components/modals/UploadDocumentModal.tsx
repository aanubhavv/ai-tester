"use client";

import { useState } from "react";
import { X, UploadCloud, File, AlertCircle, Loader2 } from "lucide-react";
import { useRouter } from "next/navigation";

interface UploadDocumentModalProps {
  projectId: string;
}

export default function UploadDocumentModal({ projectId }: UploadDocumentModalProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [file, setFile] = useState<File | null>(null);
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [documentType, setDocumentType] = useState("other");
  const [isUploading, setIsUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  
  const router = useRouter();

  const handleOpen = () => setIsOpen(true);
  const handleClose = () => {
    if (isUploading) return;
    setIsOpen(false);
    setFile(null);
    setTitle("");
    setDescription("");
    setDocumentType("other");
    setError(null);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!file || !title) {
      setError("File and title are required.");
      return;
    }

    setIsUploading(true);
    setError(null);

    try {
      const formData = new FormData();
      formData.append("file", file);
      formData.append("title", title);
      formData.append("description", description);
      formData.append("document_type", documentType);

      const res = await fetch(`http://127.0.0.1:8000/api/v1/projects/${projectId}/documents`, {
        method: "POST",
        body: formData,
      });

      if (!res.ok) {
        throw new Error("Failed to upload document");
      }

      router.refresh();
      handleClose();
    } catch (err: any) {
      setError(err.message || "An error occurred during upload.");
    } finally {
      setIsUploading(false);
    }
  };

  return (
    <>
      <button 
        onClick={handleOpen}
        className="inline-flex items-center justify-center rounded-md text-sm font-medium transition-colors bg-blue-600 text-white hover:bg-blue-700 h-10 px-4 py-2"
      >
        <UploadCloud className="mr-2 h-4 w-4" />
        Upload Document
      </button>

      {isOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm">
          <div className="bg-zinc-950 border border-zinc-800 rounded-xl shadow-xl w-full max-w-md overflow-hidden">
            <div className="flex items-center justify-between px-6 py-4 border-b border-zinc-800">
              <h3 className="text-lg font-medium text-zinc-100">Upload Document</h3>
              <button onClick={handleClose} disabled={isUploading} className="text-zinc-400 hover:text-zinc-200">
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
                <label className="block text-sm font-medium text-zinc-300 mb-1">File *</label>
                <div className="flex items-center justify-center w-full">
                  <label className="flex flex-col items-center justify-center w-full h-32 border-2 border-zinc-700 border-dashed rounded-lg cursor-pointer bg-zinc-900/50 hover:bg-zinc-900 transition-colors">
                    <div className="flex flex-col items-center justify-center pt-5 pb-6">
                      <UploadCloud className="w-8 h-8 mb-2 text-zinc-400" />
                      <p className="mb-2 text-sm text-zinc-400">
                        <span className="font-semibold text-zinc-300">Click to upload</span> or drag and drop
                      </p>
                      {file && <p className="text-xs text-blue-400 mt-2 font-medium">{file.name}</p>}
                    </div>
                    <input 
                      type="file" 
                      className="hidden" 
                      onChange={(e) => setFile(e.target.files?.[0] || null)}
                    />
                  </label>
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-zinc-300 mb-1">Title *</label>
                <input 
                  type="text" 
                  value={title}
                  onChange={(e) => setTitle(e.target.value)}
                  className="w-full bg-zinc-900 border border-zinc-800 rounded-md px-3 py-2 text-zinc-200 focus:outline-none focus:ring-1 focus:ring-blue-500" 
                  placeholder="e.g. Authentication PRD"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-zinc-300 mb-1">Type</label>
                <select 
                  value={documentType}
                  onChange={(e) => setDocumentType(e.target.value)}
                  className="w-full bg-zinc-900 border border-zinc-800 rounded-md px-3 py-2 text-zinc-200 focus:outline-none focus:ring-1 focus:ring-blue-500"
                >
                  <option value="prd">PRD (Product Requirements)</option>
                  <option value="business_logic">Business Logic</option>
                  <option value="api_spec">API Specification</option>
                  <option value="architecture">Architecture</option>
                  <option value="other">Other</option>
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium text-zinc-300 mb-1">Description</label>
                <textarea 
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  className="w-full bg-zinc-900 border border-zinc-800 rounded-md px-3 py-2 text-zinc-200 focus:outline-none focus:ring-1 focus:ring-blue-500" 
                  rows={2}
                  placeholder="Optional description"
                />
              </div>

              <div className="pt-4 flex justify-end gap-3">
                <button 
                  type="button" 
                  onClick={handleClose}
                  disabled={isUploading}
                  className="px-4 py-2 text-sm font-medium text-zinc-300 hover:text-white transition-colors"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isUploading}
                  className="px-4 py-2 text-sm font-medium bg-blue-600 hover:bg-blue-700 text-white rounded-md transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
                >
                  {isUploading ? (
                    <>
                      <Loader2 className="animate-spin h-4 w-4" />
                      Extracting & Uploading...
                    </>
                  ) : "Upload"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </>
  );
}
