import { Activity, Plus, BrainCircuit } from "lucide-react";
import AddFeatureModal from "@/components/modals/AddFeatureModal";

async function getFeatures(projectId: string) {
  try {
    const res = await fetch(`http://127.0.0.1:8000/api/v1/projects/${projectId}/features`, { cache: 'no-store' });
    if (!res.ok) return { features: [] };
    return res.json();
  } catch (error) {
    return { features: [] };
  }
}

export default async function FeaturesTab(props: { params: Promise<{ project_id: string }> }) {
  const params = await props.params;
  const { features } = await getFeatures(params.project_id);

  return (
    <div className="flex flex-col max-w-6xl mx-auto space-y-8">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-zinc-100">Features</h2>
          <p className="text-zinc-400 mt-1">Manage product features extracted from requirements or added manually.</p>
        </div>
        <div className="flex items-center gap-3">
          <button className="inline-flex items-center justify-center rounded-md text-sm font-medium transition-colors border border-zinc-700 bg-zinc-900 text-zinc-300 hover:bg-zinc-800 h-10 px-4 py-2">
            <BrainCircuit className="mr-2 h-4 w-4 text-purple-400" />
            Extract with AI
          </button>
          <AddFeatureModal projectId={params.project_id} />
        </div>
      </div>

      <div className="rounded-xl border border-zinc-800 bg-zinc-950 shadow-sm overflow-hidden">
        <div className="divide-y divide-zinc-800">
          {(!features || features.length === 0) ? (
            <div className="p-12 text-center flex flex-col items-center justify-center">
              <div className="h-12 w-12 rounded-full bg-zinc-900 flex items-center justify-center mb-4">
                <Activity className="h-6 w-6 text-zinc-500" />
              </div>
              <h3 className="text-lg font-medium text-zinc-200">No features defined</h3>
              <p className="text-sm text-zinc-500 mt-1 max-w-sm">Use the AI Planner to extract features from your Knowledge Base, or add one manually.</p>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 p-6">
              {features.map((feature: any) => (
                <div key={feature.feature_id} className="rounded-lg border border-zinc-800 bg-zinc-900/50 p-5 hover:border-zinc-600 transition-colors cursor-pointer group">
                  <div className="flex items-start justify-between">
                    <h3 className="text-base font-semibold text-zinc-200 group-hover:text-blue-400 transition-colors">{feature.name}</h3>
                  </div>
                  <p className="text-sm text-zinc-400 mt-2 line-clamp-3">{feature.description}</p>
                  <div className="mt-4 flex items-center gap-2">
                    <span className="inline-flex items-center rounded-full bg-zinc-800 px-2 py-1 text-xs font-medium text-zinc-300">
                      ID: {feature.feature_id.substring(0, 8)}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
