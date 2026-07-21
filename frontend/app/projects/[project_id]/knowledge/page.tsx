import { FileText, FileImage, FileCode2, UploadCloud, File } from "lucide-react";
import UploadDocumentModal from "@/components/modals/UploadDocumentModal";
import ProjectContextInput from "./ProjectContextInput";

import ClientKnowledgeTable from "./ClientKnowledgeTable";

async function getKnowledgeFiles(projectId: string) {
  try {
    const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000'}/api/v1/projects/${projectId}/documents`, { cache: 'no-store' });
    if (!res.ok) return { files: [] };
    const data = await res.json();
    return { files: data.documents || [] };
  } catch (error) {
    return { files: [] };
  }
}

async function getProjectDetails(projectId: string) {
  try {
    const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000'}/api/v1/projects/${projectId}`, { cache: 'no-store' });
    if (!res.ok) return null;
    return res.json();
  } catch (error) {
    return null;
  }
}

export default async function KnowledgeTab(props: { params: Promise<{ project_id: string }> }) {
  const params = await props.params;
  const [project, { files }] = await Promise.all([
    getProjectDetails(params.project_id),
    getKnowledgeFiles(params.project_id)
  ]);

  const getIcon = (type: string) => {
    if (type.includes('image')) return <FileImage className="h-5 w-5 text-blue-400" />;
    if (type.includes('markdown') || type.includes('text')) return <FileText className="h-5 w-5 text-emerald-400" />;
    if (type.includes('json')) return <FileCode2 className="h-5 w-5 text-amber-400" />;
    return <File className="h-5 w-5 text-zinc-400" />;
  };

  return (
    <div className="flex flex-col max-w-6xl mx-auto space-y-8">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-zinc-100">Knowledge Base</h2>
          <p className="text-zinc-400 mt-1">Manage project requirements, PRDs, context, and documentation.</p>
        </div>
        <UploadDocumentModal projectId={params.project_id} />
      </div>

      {project && (
        <ProjectContextInput projectId={params.project_id} initialContext={project.project_context || ""} />
      )}

      <div className="rounded-xl border border-zinc-800 bg-zinc-950 shadow-sm overflow-hidden">
        <div className="divide-y divide-zinc-800">
          <ClientKnowledgeTable files={files} projectId={params.project_id} />
        </div>
      </div>
    </div>
  );
}
