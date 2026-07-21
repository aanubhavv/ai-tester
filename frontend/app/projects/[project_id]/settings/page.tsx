import { Settings, Trash2, Save } from "lucide-react";
import ProjectSettingsForm from "./ProjectSettingsForm";
import DeleteProjectButton from "./DeleteProjectButton";

async function getProject(projectId: string) {
  try {
    const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000'}/api/v1/projects/${projectId}`, { cache: 'no-store' });
    if (!res.ok) return null;
    return res.json();
  } catch (error) {
    return null;
  }
}

export default async function SettingsPage(props: { params: Promise<{ project_id: string }> }) {
  const params = await props.params;
  const project = await getProject(params.project_id);

  if (!project) return null;

  return (
    <div className="flex flex-col max-w-4xl mx-auto space-y-8">
      <div>
        <h2 className="text-2xl font-bold text-zinc-100 flex items-center">
          <Settings className="mr-2 h-6 w-6 text-zinc-400" />
          Project Settings
        </h2>
        <p className="text-zinc-400 mt-1">Manage your project configuration and preferences.</p>
      </div>

      <div className="rounded-xl border border-zinc-800 bg-zinc-950 p-6 shadow-sm">
        <h3 className="text-lg font-medium text-zinc-200 mb-4">General Settings</h3>
        <ProjectSettingsForm project={project} />
      </div>

      <div className="rounded-xl border border-red-900/30 bg-red-950/10 p-6 shadow-sm">
        <h3 className="text-lg font-medium text-red-400 mb-2">Danger Zone</h3>
        <p className="text-sm text-zinc-400 mb-4">
          Once you delete a project, there is no going back. Please be certain.
        </p>
        
        <DeleteProjectButton projectId={project.project_id} />
      </div>
    </div>
  );
}
