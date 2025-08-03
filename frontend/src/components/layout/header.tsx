'use client';

import { Search, Moon, Sun, Bell } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { useTheme } from 'next-themes';
import { GlassCard } from '@/components/ui/glass-card';

export function Header() {
  const { theme, setTheme } = useTheme();

  return (
    <header className="flex h-16 items-center justify-between border-b border-slate-800/50 bg-slate-950/50 px-6 backdrop-blur-sm">
      {/* Search */}
      <div className="flex flex-1 items-center space-x-4">
        <div className="relative max-w-md flex-1">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
          <Input
            placeholder="Search your library..."
            className="border-slate-700/50 bg-slate-900/50 pl-10 focus:border-orange-500/50 focus:ring-orange-500/20"
          />
        </div>
      </div>

      {/* Actions */}
      <div className="flex items-center space-x-2">
        {/* Notifications */}
        <Button
          variant="ghost"
          size="sm"
          className="text-slate-400 hover:bg-white/10 hover:text-white"
        >
          <Bell className="h-4 w-4" />
        </Button>

        {/* Theme Toggle */}
        <Button
          variant="ghost"
          size="sm"
          onClick={() => setTheme(theme === 'dark' ? 'light' : 'dark')}
          className="text-slate-400 hover:bg-white/10 hover:text-white"
        >
          <Sun className="h-4 w-4 rotate-0 scale-100 transition-all dark:-rotate-90 dark:scale-0" />
          <Moon className="absolute h-4 w-4 rotate-90 scale-0 transition-all dark:rotate-0 dark:scale-100" />
          <span className="sr-only">Toggle theme</span>
        </Button>
      </div>
    </header>
  );
}
