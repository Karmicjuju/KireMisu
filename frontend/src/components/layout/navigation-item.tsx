'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { LucideIcon } from 'lucide-react';
import { cn } from '@/lib/utils';
import { useNavigationStore } from '@/lib/stores/navigation';

interface NavigationItemProps {
  href: string;
  icon: LucideIcon;
  label: string;
  collapsed?: boolean;
}

export function NavigationItem({
  href,
  icon: Icon,
  label,
  collapsed = false,
}: NavigationItemProps) {
  const pathname = usePathname();
  const isActive = pathname === href || pathname.startsWith(href + '/');
  const setCurrentPage = useNavigationStore((state) => state.setCurrentPage);

  return (
    <Link
      href={href}
      onClick={() => setCurrentPage(label.toLowerCase())}
      className={cn(
        'flex items-center rounded-xl px-3 py-2.5 text-sm font-medium transition-all duration-200',
        'hover:bg-accent/10 hover:backdrop-blur-sm',
        'focus:outline-none focus:ring-2 focus:ring-primary/50',
        isActive && 'bg-gradient-to-r from-primary/20 to-accent/20 text-primary shadow-lg',
        !isActive && 'text-muted-foreground hover:text-foreground',
        collapsed && 'justify-center px-2'
      )}
    >
      <Icon className={cn('h-5 w-5 flex-shrink-0', !collapsed && 'mr-3')} />
      {!collapsed && <span className="truncate">{label}</span>}
    </Link>
  );
}
