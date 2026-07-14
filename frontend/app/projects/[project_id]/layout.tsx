"use client";

import Link from "next/link";
import { ReactNode } from "react";
import { usePathname } from "next/navigation";

export default function ProjectLayout({
  children,
  params,
}: {
  children: ReactNode;
  params: { project_id: string };
}) {
  const projectId = params.project_id;
  const pathname = usePathname();

  const generalTabs = [
    { name: "Overview", href: `/projects/${projectId}` },
    { name: "Knowledge", href: `/projects/${projectId}/knowledge` },
    { name: "Executions", href: `/projects/${projectId}/executions` },
    { name: "Reports", href: `/projects/${projectId}/reports` },
  ];

  const qaBrainTabs = [
    { name: "Requirements", href: `/projects/${projectId}/planning/requirements` },
    { name: "Features", href: `/projects/${projectId}/planning/features` },
    { name: "User Flows", href: `/projects/${projectId}/planning/flows` },
    { name: "Risk Matrix", href: `/projects/${projectId}/planning/risks` },
    { name: "Testing Strategy", href: `/projects/${projectId}/planning/strategy` },
    { name: "Test Suites", href: `/projects/${projectId}/planning/suites` },
  ];

  const handleGenerate = async () => {
    try {
      await fetch(`http://localhost:8000/api/v1/projects/${projectId}/planning/generate`, {
        method: "POST"
      });
      alert("AI Planning Generation started! This may take a minute depending on context size.");
    } catch (e) {
      alert("Failed to start planning pipeline.");
    }
  };

  return (
    <div className="flex h-screen bg-gray-50 font-sans text-gray-900">
      {/* Sidebar */}
      <aside className="w-64 bg-white border-r border-gray-200 flex flex-col">
        <div className="p-4 border-b border-gray-200">
          <Link href="/projects" className="text-blue-600 font-medium hover:underline">
            &larr; All Projects
          </Link>
          <div className="mt-4 font-bold text-lg text-gray-800">Project Workspace</div>
          <div className="text-xs text-gray-500 font-mono mt-1 break-all">{projectId}</div>
        </div>
        
        <nav className="flex-1 overflow-y-auto p-4 space-y-6">
          <div>
            <div className="text-xs font-bold text-gray-400 uppercase tracking-wider mb-2">General</div>
            <div className="space-y-1">
              {generalTabs.map((tab) => (
                <Link
                  key={tab.name}
                  href={tab.href}
                  className={`block px-3 py-2 rounded-md transition ${
                    pathname === tab.href ? "bg-blue-50 text-blue-700 font-medium" : "text-gray-700 hover:bg-gray-100 hover:text-blue-600"
                  }`}
                >
                  {tab.name}
                </Link>
              ))}
            </div>
          </div>

          <div>
            <div className="flex items-center justify-between mb-2">
              <div className="text-xs font-bold text-purple-500 uppercase tracking-wider">QA Brain</div>
            </div>
            <div className="space-y-1">
              {qaBrainTabs.map((tab) => (
                <Link
                  key={tab.name}
                  href={tab.href}
                  className={`block px-3 py-2 rounded-md transition ${
                    pathname === tab.href ? "bg-purple-50 text-purple-700 font-medium" : "text-gray-700 hover:bg-gray-100 hover:text-purple-600"
                  }`}
                >
                  {tab.name}
                </Link>
              ))}
            </div>
            <button 
              onClick={handleGenerate}
              className="mt-4 w-full text-xs font-semibold bg-purple-100 text-purple-700 py-2 rounded hover:bg-purple-200 transition"
            >
              Generate AI Plan
            </button>
          </div>
        </nav>
      </aside>

      {/* Main Content Area */}
      <main className="flex-1 overflow-y-auto p-8">
        {children}
      </main>
    </div>
  );
}
