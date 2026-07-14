import Link from "next/link";
import { User, Settings, Shield, Bell, Database, BrainCircuit, Key } from "lucide-react";

export default function SettingsLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const navItems = [
    { name: "General", href: "/settings/general", icon: Settings },
    { name: "AI Provider & Models", href: "/settings", icon: BrainCircuit, active: true },
    { name: "API Keys", href: "/settings/api-keys", icon: Key },
    { name: "Team Members", href: "/settings/team", icon: User },
    { name: "Integrations", href: "/settings/integrations", icon: Database },
    { name: "Notifications", href: "/settings/notifications", icon: Bell },
    { name: "Security", href: "/settings/security", icon: Shield },
  ];

  return (
    <div className="flex flex-col min-h-full">
      <div className="bg-zinc-950 border-b border-zinc-800 pt-8 px-8 pb-8">
        <h1 className="text-2xl font-bold text-zinc-100">Workspace Settings</h1>
        <p className="text-sm text-zinc-400 mt-1">Manage your team, billing, and global configuration.</p>
      </div>

      <div className="flex flex-1 overflow-hidden">
        {/* Settings Sidebar */}
        <div className="w-64 border-r border-zinc-800 bg-zinc-950/50 p-4 overflow-y-auto">
          <nav className="space-y-1">
            {navItems.map((item) => {
              const Icon = item.icon;
              return (
                <Link
                  key={item.name}
                  href={item.href}
                  className={`flex items-center px-3 py-2 text-sm font-medium rounded-md transition-colors ${
                    item.active 
                      ? "bg-zinc-900 text-zinc-100" 
                      : "text-zinc-400 hover:bg-zinc-900/50 hover:text-zinc-200"
                  }`}
                >
                  <Icon className={`mr-3 h-4 w-4 shrink-0 ${item.active ? 'text-blue-400' : 'text-zinc-500'}`} />
                  {item.name}
                </Link>
              );
            })}
          </nav>
        </div>

        {/* Settings Content */}
        <div className="flex-1 p-8 overflow-y-auto">
          {children}
        </div>
      </div>
    </div>
  );
}
