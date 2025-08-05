'use client';

import { Sidebar } from '@/components/layout/sidebar';
import { Header } from '@/components/layout/header';
import { useNavigationStore } from '@/lib/stores/navigation';
import { cn } from '@/lib/utils';

export default function AppLayout({ children }: { children: React.ReactNode }) {
  const sidebarCollapsed = useNavigationStore((state) => state.sidebarCollapsed);

  return (
    <div className="flex h-screen overflow-hidden bg-background text-foreground">
      <Sidebar />
      <div className="flex flex-1 flex-col overflow-hidden">
        <Header />
        <main
          className={cn(
            'flex-1 overflow-auto bg-gradient-to-br from-background via-muted/30 to-background p-6',
            'transition-all duration-300'
          )}
        >
          <div className="mx-auto max-w-7xl">{children}</div>
        </main>
      </div>
    </div>
  );
}
