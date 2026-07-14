"use client";

import { useEffect, useState } from "react";

export default function ProjectOverview({ params }: { params: { project_id: string } }) {
  const [project, setProject] = useState<any>(null);

  useEffect(() => {
    fetch(`http://localhost:8000/api/v1/projects/${params.project_id}`)
      .then((res) => res.json())
      .then((data) => setProject(data))
      .catch((err) => console.error("Failed to load project", err));
  }, [params.project_id]);

  if (!project) return <div>Loading project details...</div>;

  return (
    <div className="bg-white p-8 rounded-lg shadow-sm border border-gray-200">
      <h1 className="text-3xl font-bold mb-4">{project.name}</h1>
      <p className="text-gray-700 text-lg mb-6">{project.description || "No description provided."}</p>
      
      <div className="grid grid-cols-2 gap-4 text-sm text-gray-600">
        <div>
          <strong className="block text-gray-900 mb-1">Project ID</strong>
          <span className="font-mono bg-gray-100 px-2 py-1 rounded">{project.project_id}</span>
        </div>
        <div>
          <strong className="block text-gray-900 mb-1">Primary URL</strong>
          <span>{project.primary_url || "Not set"}</span>
        </div>
        <div>
          <strong className="block text-gray-900 mb-1">Created At</strong>
          <span>{new Date(project.created_at).toLocaleString()}</span>
        </div>
        <div>
          <strong className="block text-gray-900 mb-1">Last Updated</strong>
          <span>{new Date(project.updated_at).toLocaleString()}</span>
        </div>
      </div>
    </div>
  );
}
