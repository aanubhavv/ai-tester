import Link from 'next/link';
import { 
  LayoutDashboard, 
  FolderGit2, 
  PlaySquare, 
  GitCompare, 
  FileText, 
  BrainCircuit, 
  Layers, 
  CheckSquare, 
  BookOpen, 
  Settings 
} from 'lucide-react';

const navigation = [
  { name: 'Dashboard', href: '/', icon: LayoutDashboard },
  { name: 'Projects', href: '/projects', icon: FolderGit2 },
  { name: 'Settings', href: '/settings', icon: Settings },
];

export default function Sidebar() {
  return (
    <div className="flex w-64 flex-col bg-zinc-950 border-r border-zinc-800 text-zinc-300 h-full">
      <div className="flex h-16 shrink-0 items-center px-6 border-b border-zinc-800">
        <div className="flex items-center gap-2">
          <div className="h-6 w-6 rounded bg-blue-500 flex items-center justify-center">
            <span className="text-xs font-bold text-white">QA</span>
          </div>
          <span className="text-xl font-semibold text-white tracking-tight">Forge</span>
        </div>
      </div>
      <div className="flex flex-1 flex-col overflow-y-auto">
        <nav className="flex-1 space-y-1 px-3 py-4">
          {navigation.map((item) => {
            const Icon = item.icon;
            return (
              <Link
                key={item.name}
                href={item.href}
                className="group flex items-center px-3 py-2 text-sm font-medium rounded-md hover:bg-zinc-800 hover:text-white transition-colors"
              >
                <Icon className="mr-3 h-5 w-5 flex-shrink-0 text-zinc-400 group-hover:text-zinc-200" aria-hidden="true" />
                {item.name}
              </Link>
            );
          })}
        </nav>
      </div>
    </div>
  );
}
