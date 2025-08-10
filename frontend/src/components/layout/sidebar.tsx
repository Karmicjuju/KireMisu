'use client';

import { useState } from 'react';
import {
  LayoutDashboard,
  Library,
  Download,
  Settings,
  ChevronLeft,
  ChevronRight,
  BookOpen,
  Bell,
} from 'lucide-react';
import { GlassCard } from '@/components/ui/glass-card';
import { NavigationItem } from './navigation-item';
import { Button } from '@/components/ui/button';
import { useNavigationStore } from '@/lib/stores/navigation';
import { cn } from '@/lib/utils';

const navigationItems = [
  { href: '/', icon: LayoutDashboard, label: 'Dashboard' },
  { href: '/library', icon: Library, label: 'Library' },
  { href: '/library/watching', icon: Bell, label: 'Watching' },
  { href: '/downloads', icon: Download, label: 'Downloads' },
  { href: '/settings', icon: Settings, label: 'Settings' },
];

export function Sidebar() {
  const { sidebarCollapsed, setSidebarCollapsed } = useNavigationStore();

  return (
    <div
      className={cn(
        'relative flex h-full flex-col border-r border-border bg-gradient-to-b from-card to-background transition-all duration-300',
        sidebarCollapsed ? 'w-16' : 'w-64'
      )}
    >
      {/* Header */}
      <div className="flex h-16 items-center border-b border-border px-4">
        {!sidebarCollapsed && (
          <div className="flex items-center space-x-2">
            <BookOpen className="h-6 w-6 text-orange-500" />
            <span className="bg-gradient-to-r from-orange-500 to-red-500 bg-clip-text text-lg font-bold text-transparent">
              KireMisu
            </span>
          </div>
        )}
        {sidebarCollapsed && (
          <div className="flex w-full justify-center">
            <BookOpen className="h-6 w-6 text-orange-500" />
          </div>
        )}
      </div>

      {/* Navigation */}
      <nav className="flex-1 space-y-2 p-4">
        {navigationItems.map((item) => (
          <NavigationItem
            key={item.href}
            href={item.href}
            icon={item.icon}
            label={item.label}
            collapsed={sidebarCollapsed}
          />
        ))}
      </nav>

      {/* Collapse Toggle */}
      <div className="border-t border-border p-4">
        <Button
          variant="ghost"
          size="sm"
          onClick={() => setSidebarCollapsed(!sidebarCollapsed)}
          className={cn(
            'w-full text-muted-foreground hover:bg-accent hover:text-accent-foreground',
            sidebarCollapsed && 'px-2'
          )}
        >
          {sidebarCollapsed ? (
            <ChevronRight className="h-4 w-4" />
          ) : (
            <>
              <ChevronLeft className="mr-2 h-4 w-4" />
              Collapse
            </>
          )}
        </Button>
      </div>
    </div>
  );
}
