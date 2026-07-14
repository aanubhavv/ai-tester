"use client";

import { useState } from "react";
import { FileText, FileImage, FileCode2, File } from "lucide-react";
import ViewDocumentModal from "@/components/modals/ViewDocumentModal";

interface ClientKnowledgeTableProps {
  files: any[];
  projectId: string;
}

export default function ClientKnowledgeTable({ files, projectId }: ClientKnowledgeTableProps) {
  const [selectedDocId, setSelectedDocId] = useState<string | null>(null);
  const [selectedDocTitle, setSelectedDocTitle] = useState<string | null>(null);
  const [selectedDocFilename, setSelectedDocFilename] = useState<string | null>(null);

  const getIcon = (type: string) => {
    if (type.includes('image')) return <FileImage className="h-5 w-5 text-blue-400" />;
    if (type.includes('markdown') || type.includes('text')) return <FileText className="h-5 w-5 text-emerald-400" />;
    if (type.includes('json')) return <FileCode2 className="h-5 w-5 text-amber-400" />;
    return <File className="h-5 w-5 text-zinc-400" />;
  };

  const handleRowClick = (docId: string, title: string, filename: string) => {
    setSelectedDocId(docId);
    setSelectedDocTitle(title);
    setSelectedDocFilename(filename);
  };

  const handleCloseModal = () => {
    setSelectedDocId(null);
    setSelectedDocTitle(null);
    setSelectedDocFilename(null);
  };

  if (!files || files.length === 0) {
    return (
      <div className="p-12 text-center flex flex-col items-center justify-center">
        <div className="h-12 w-12 rounded-full bg-zinc-900 flex items-center justify-center mb-4">
          <FileText className="h-6 w-6 text-zinc-500" />
        </div>
        <h3 className="text-lg font-medium text-zinc-200">No documents found</h3>
        <p className="text-sm text-zinc-500 mt-1 max-w-sm">Upload PRDs, requirement specifications, or business context to improve AI test generation.</p>
      </div>
    );
  }

  return (
    <>
      <table className="min-w-full divide-y divide-zinc-800 text-left text-sm whitespace-nowrap">
        <thead className="bg-zinc-900/50">
          <tr>
            <th scope="col" className="px-6 py-4 font-semibold text-zinc-300">File Name</th>
            <th scope="col" className="px-6 py-4 font-semibold text-zinc-300">Type</th>
            <th scope="col" className="px-6 py-4 font-semibold text-zinc-300">Size</th>
            <th scope="col" className="px-6 py-4 font-semibold text-zinc-300">Uploaded</th>
            <th scope="col" className="px-6 py-4 font-semibold text-zinc-300">Status</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-zinc-800">
          {files.map((file: any) => (
            <tr 
              key={file.document_id || file.id} 
              className="hover:bg-zinc-900/50 transition-colors cursor-pointer"
              onClick={() => handleRowClick(file.document_id || file.id, file.title || file.filename, file.filename)}
            >
              <td className="px-6 py-4">
                <div className="flex items-center gap-3">
                  {getIcon(file.document_type || file.file_type || '')}
                  <span className="font-medium text-zinc-200">{file.filename}</span>
                </div>
              </td>
              <td className="px-6 py-4 text-zinc-400 capitalize">{file.document_type || file.file_type || 'other'}</td>
              <td className="px-6 py-4 text-zinc-400">
                {file.size_bytes ? `${(file.size_bytes / 1024).toFixed(1)} KB` : 'Unknown'}
              </td>
              <td className="px-6 py-4 text-zinc-400">
                {file.created_at || file.uploaded_at ? new Date(file.created_at || file.uploaded_at).toLocaleDateString() : 'N/A'}
              </td>
              <td className="px-6 py-4">
                <span className="inline-flex items-center rounded-full bg-emerald-500/10 px-2 py-1 text-xs font-medium text-emerald-400 ring-1 ring-inset ring-emerald-500/20">
                  Processed
                </span>
              </td>
            </tr>
          ))}
        </tbody>
      </table>

      {selectedDocId && (
        <ViewDocumentModal 
          projectId={projectId} 
          documentId={selectedDocId} 
          documentTitle={selectedDocTitle} 
          documentFilename={selectedDocFilename}
          onClose={handleCloseModal} 
        />
      )}
    </>
  );
}
