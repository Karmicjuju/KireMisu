'use client';

import React, { useState } from 'react';
import { Bell } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { cn } from '@/lib/utils';
import { NotificationDropdown } from './notification-dropdown';
import { useNotifications } from '@/hooks/use-notifications';

export interface NotificationBellProps {
  className?: string;
}

export function NotificationBell({ className }: NotificationBellProps) {
  const [isOpen, setIsOpen] = useState(false);
  const { data: notifications, isLoading } = useNotifications();
  
  const unreadCount = notifications?.filter(n => !n.is_read).length || 0;

  return (
    <div className="relative">
      <Button
        variant="ghost"
        size="sm"
        onClick={() => setIsOpen(!isOpen)}
        className={cn(
          "text-muted-foreground hover:bg-accent hover:text-accent-foreground relative",
          className
        )}
        aria-label={`Notifications ${unreadCount > 0 ? `(${unreadCount} unread)` : ''}`}
      >
        <Bell className="h-4 w-4" />
        {unreadCount > 0 && (
          <Badge 
            variant="destructive" 
            className="absolute -right-1 -top-1 h-5 w-5 p-0 flex items-center justify-center text-xs"
          >
            {unreadCount > 99 ? '99+' : unreadCount}
          </Badge>
        )}
      </Button>

      {isOpen && (
        <NotificationDropdown
          isOpen={isOpen}
          onClose={() => setIsOpen(false)}
          notifications={notifications || []}
          isLoading={isLoading}
        />
      )}
    </div>
  );
}