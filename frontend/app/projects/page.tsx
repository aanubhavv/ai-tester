"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Plus } from "lucide-react";

interface Project {
  project_id: string;
  name: string;
  description: string;
}

export default function ProjectsPage() {
  const router = useRouter();
  const [projects, setProjects] = useState<Project[]>([]);
  const [isCreating, setIsCreating] = useState(false);
  const [newProjectName, setNewProjectName] = useState("");
  const [newProjectDesc, setNewProjectDesc] = useState("");
  const [newPrimaryUrl, setNewPrimaryUrl] = useState("");

  useEffect(() => {
    fetch(`${process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000'}/api/v1/projects`)
      .then((res) => res.json())
      .then((data) => setProjects(data.projects || []))
      .catch((err) => console.error("Failed to load projects", err));
      
    if (typeof window !== "undefined") {
      const urlParams = new URLSearchParams(window.location.search);
      if (urlParams.get("create") === "true") {
        setIsCreating(true);
        window.history.replaceState({}, '', '/projects');
      }
    }
  }, []);

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000'}/api/v1/projects`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          name: newProjectName,
          description: newProjectDesc,
          primary_url: newPrimaryUrl,
        }),
      });
      const data = await res.json();
      router.push(`/projects/${data.project_id}`);
    } catch (err) {
      console.error("Failed to create project", err);
    }
  };

  return (
    <div className="p-8 max-w-6xl mx-auto font-sans text-zinc-100">
      <div className="flex justify-between items-center mb-8">
        <div>
          <h1 className="text-3xl font-bold text-zinc-100">Projects</h1>
          <p className="text-zinc-400 mt-1">Manage and access your testing projects.</p>
        </div>
        <button
          onClick={() => setIsCreating(true)}
          className="inline-flex items-center justify-center rounded-md text-sm font-medium transition-colors bg-blue-600 text-white hover:bg-blue-700 h-10 px-4 py-2"
        >
          <Plus className="mr-2 h-4 w-4" />
          Create Project
        </button>
      </div>

      {isCreating && (
        <div className="mb-8 p-6 bg-zinc-950 border border-zinc-800 rounded-xl shadow-sm">
          <h2 className="text-xl font-semibold mb-4 text-zinc-100">New Project</h2>
          <form onSubmit={handleCreate} className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-zinc-300">Name</label>
              <input
                type="text"
                required
                className="mt-1 block w-full bg-zinc-900 border border-zinc-800 text-zinc-200 rounded-lg p-2.5 outline-none focus:border-blue-500 transition-colors"
                value={newProjectName}
                onChange={(e) => setNewProjectName(e.target.value)}
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-zinc-300">Primary URL</label>
              <input
                type="url"
                placeholder="https://example.com"
                className="mt-1 block w-full bg-zinc-900 border border-zinc-800 text-zinc-200 rounded-lg p-2.5 outline-none focus:border-blue-500 transition-colors"
                value={newPrimaryUrl}
                onChange={(e) => setNewPrimaryUrl(e.target.value)}
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-zinc-300">Description</label>
              <textarea
                className="mt-1 block w-full bg-zinc-900 border border-zinc-800 text-zinc-200 rounded-lg p-2.5 outline-none focus:border-blue-500 transition-colors min-h-[100px]"
                value={newProjectDesc}
                onChange={(e) => setNewProjectDesc(e.target.value)}
              />
            </div>
            <div className="flex justify-end space-x-3 pt-2">
              <button
                type="button"
                onClick={() => setIsCreating(false)}
                className="px-4 py-2 text-sm font-medium text-zinc-400 hover:text-zinc-200 transition-colors"
              >
                Cancel
              </button>
              <button
                type="submit"
                className="inline-flex items-center justify-center rounded-md text-sm font-medium transition-colors bg-blue-600 text-white hover:bg-blue-700 h-10 px-6"
              >
                Save
              </button>
            </div>
          </form>
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {projects.map((proj) => (
          <Link
            key={proj.project_id}
            href={`/projects/${proj.project_id}`}
            className="block p-6 bg-zinc-950 border border-zinc-800 rounded-xl hover:bg-zinc-900/80 transition-colors group"
          >
            <h2 className="text-xl font-bold mb-2 text-zinc-100 group-hover:text-blue-400 transition-colors">{proj.name}</h2>
            <p className="text-zinc-400 mb-6 line-clamp-2 text-sm">{proj.description || "No description provided."}</p>
            <div className="text-xs text-zinc-500 font-mono flex items-center justify-between">
              <span>ID: {proj.project_id}</span>
            </div>
          </Link>
        ))}
        {projects.length === 0 && !isCreating && (
          <div className="col-span-full p-12 bg-zinc-950 border border-zinc-800 rounded-xl text-center flex flex-col items-center justify-center">
            <h3 className="text-lg font-medium text-zinc-200 mb-2">No projects found</h3>
            <p className="text-zinc-500 max-w-sm">Create your first testing project to get started with visual regression and AI-powered analysis.</p>
          </div>
        )}
      </div>
    </div>
  );
}
