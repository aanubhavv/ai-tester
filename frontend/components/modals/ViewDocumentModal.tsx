"use client";

import { useState, useEffect } from "react";
import { X, FileText, AlertCircle } from "lucide-react";

interface ViewDocumentModalProps {
  projectId: string;
  documentId: string | null;
  documentTitle: string | null;
  documentFilename?: string | null;
  onClose: () => void;
}

export default function ViewDocumentModal({ projectId, documentId, documentTitle, documentFilename, onClose }: ViewDocumentModalProps) {
  const [content, setContent] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const isPdf = documentFilename?.toLowerCase().endsWith('.pdf');
  const isImage = documentFilename?.toLowerCase().match(/\.(jpg|jpeg|png|gif|webp)$/i);
  const fileUrl = `http://127.0.0.1:8000/api/v1/projects/${projectId}/documents/${documentId}/file`;

  useEffect(() => {
    if (!documentId) return;
    if (isPdf || isImage) return; // Don't fetch text content for binary files

    const fetchContent = async () => {
      setIsLoading(true);
      setError(null);
      try {
        const res = await fetch(`http://127.0.0.1:8000/api/v1/projects/${projectId}/documents/${documentId}/content`);
        if (!res.ok) {
          throw new Error("Failed to load document content");
        }
        const data = await res.json();
        setContent(data.content);
      } catch (err: any) {
        setError(err.message || "An error occurred while fetching content");
      } finally {
        setIsLoading(false);
      }
    };

    fetchContent();
  }, [projectId, documentId, isPdf, isImage]);

  if (!documentId) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm">
      <div className="bg-zinc-950 border border-zinc-800 rounded-xl shadow-xl w-full max-w-4xl max-h-[90vh] flex flex-col overflow-hidden">
        <div className="flex items-center justify-between px-6 py-4 border-b border-zinc-800 bg-zinc-900/50 shrink-0">
          <div className="flex items-center gap-3">
            <div className="flex items-center justify-center h-8 w-8 rounded-full bg-zinc-800 border border-zinc-700">
              <FileText className="h-4 w-4 text-zinc-400" />
            </div>
            <h3 className="text-lg font-medium text-zinc-100">{documentTitle || "Document Viewer"}</h3>
          </div>
          <button onClick={onClose} className="text-zinc-400 hover:text-zinc-200 transition-colors">
            <X className="h-5 w-5" />
          </button>
        </div>
        
        <div className="flex-1 overflow-auto p-6 bg-zinc-950 flex flex-col">
          {isPdf ? (
            <iframe src={fileUrl} className="w-full flex-1 min-h-[60vh] rounded-md bg-zinc-900" title={documentTitle || "PDF Document"} />
          ) : isImage ? (
            <div className="flex justify-center items-center h-full bg-zinc-900/50 rounded-lg border border-zinc-800 p-6">
              <img src={fileUrl} alt={documentTitle || "Image Document"} className="max-w-full max-h-[70vh] object-contain rounded-md" />
            </div>
          ) : isLoading ? (
            <div className="flex flex-col items-center justify-center h-full text-zinc-500 min-h-[40vh]">
              <div className="animate-spin mb-4 h-8 w-8 border-2 border-zinc-700 border-t-zinc-400 rounded-full" />
              <p>Loading document content...</p>
            </div>
          ) : error ? (
            <div className="flex flex-col items-center justify-center h-full text-red-400 space-y-3 min-h-[40vh]">
              <AlertCircle className="h-10 w-10 opacity-80" />
              <p>{error}</p>
            </div>
          ) : content ? (
            <div className="bg-zinc-900/50 rounded-lg border border-zinc-800 p-6 shadow-inner flex-1">
              <pre className="text-sm text-zinc-300 font-mono whitespace-pre-wrap leading-relaxed">
                {content}
              </pre>
            </div>
          ) : (
            <div className="flex flex-col items-center justify-center h-full text-zinc-500 min-h-[40vh]">
              <p>No content available.</p>
            </div>
          )}
        </div>

        <div className="px-6 py-4 border-t border-zinc-800 bg-zinc-900/30 flex justify-end shrink-0">
          <button 
            onClick={onClose}
            className="px-4 py-2 text-sm font-medium bg-zinc-800 hover:bg-zinc-700 text-zinc-200 rounded-md transition-colors"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
}
