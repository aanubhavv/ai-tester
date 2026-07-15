"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

export default function ProjectTabs({ projectId }: { projectId: string }) {
  const pathname = usePathname();

  const tabs = [
    { name: 'Overview', href: `/projects/${projectId}`, exact: true },
    { name: 'Knowledge', href: `/projects/${projectId}/knowledge` },
    { name: 'Test Cases', href: `/projects/${projectId}/test-cases` },
    { name: 'Scans', href: `/projects/${projectId}/scans` },
    { name: 'Comparisons', href: `/projects/${projectId}/comparisons` },
    { name: 'Executions', href: `/projects/${projectId}/executions` },
  ];

  return (
    <div className="flex overflow-x-auto mt-4 hide-scrollbar">
      <nav className="flex space-x-1" aria-label="Tabs">
        {tabs.map((tab) => {
          const isActive = tab.exact 
            ? pathname === tab.href 
            : pathname?.startsWith(tab.href);

          return (
            <Link
              key={tab.name}
              href={tab.href}
              className={`whitespace-nowrap py-3 px-4 text-sm font-medium border-b-2 transition-colors ${
                isActive
                  ? "border-blue-500 text-blue-400"
                  : "border-transparent text-zinc-400 hover:border-zinc-700 hover:text-zinc-200"
              }`}
            >
              {tab.name}
            </Link>
          );
        })}
      </nav>
    </div>
  );
}
