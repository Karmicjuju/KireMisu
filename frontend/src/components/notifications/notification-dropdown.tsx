'use client';

import React, { useEffect, useRef } from 'react';
import { GlassCard } from '@/components/ui/glass-card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Separator } from '@/components/ui/separator';
import { ScrollArea } from '@/components/ui/scroll-area';
import { NotificationItem } from './notification-item';
import { useNotificationActions } from '@/hooks/use-notification-actions';
import { cn } from '@/lib/utils';
import { CheckCheck, X } from 'lucide-react';
import type { NotificationResponse } from '@/lib/api';

export interface NotificationDropdownProps {
  isOpen: boolean;
  onClose: () => void;
  notifications: NotificationResponse[];
  isLoading: boolean;
  className?: string;
}

export function NotificationDropdown({
  isOpen,
  onClose,
  notifications,
  isLoading,
  className
}: NotificationDropdownProps) {
  const dropdownRef = useRef<HTMLDivElement>(null);
  const { markAsRead, markAllAsRead } = useNotificationActions();

  // Close dropdown when clicking outside
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        onClose();
      }
    }

    if (isOpen) {
      document.addEventListener('mousedown', handleClickOutside);
      return () => document.removeEventListener('mousedown', handleClickOutside);
    }
  }, [isOpen, onClose]);

  // Handle escape key
  useEffect(() => {
    function handleEscapeKey(event: KeyboardEvent) {
      if (event.key === 'Escape') {
        onClose();
      }
    }

    if (isOpen) {
      document.addEventListener('keydown', handleEscapeKey);
      return () => document.removeEventListener('keydown', handleEscapeKey);
    }
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  const unreadNotifications = notifications.filter(n => !n.is_read);
  const recentNotifications = notifications.slice(0, 10); // Show most recent 10

  const handleMarkAllAsRead = async () => {
    try {
      await markAllAsRead();
    } catch (error) {
      console.error('Failed to mark all notifications as read:', error);
    }
  };

  const handleNotificationClick = async (notification: NotificationResponse) => {
    if (!notification.is_read) {
      try {
        await markAsRead(notification.id);
      } catch (error) {
        console.error('Failed to mark notification as read:', error);
      }
    }
  };

  return (
    <div
      ref={dropdownRef}
      className={cn(
        "absolute right-0 top-12 z-50 w-96 max-w-[90vw] animate-in slide-in-from-top-2",
        className
      )}
    >
      <GlassCard className="overflow-hidden shadow-xl border-border">
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-border">
          <div className="flex items-center gap-2">
            <h3 className="font-semibold text-sm">Notifications</h3>
            {unreadNotifications.length > 0 && (
              <Badge variant="outline" className="text-xs">
                {unreadNotifications.length} new
              </Badge>
            )}
          </div>
          <div className="flex items-center gap-1">
            {unreadNotifications.length > 0 && (
              <Button
                variant="ghost"
                size="sm"
                onClick={handleMarkAllAsRead}
                className="h-7 px-2 text-xs text-muted-foreground hover:text-foreground"
              >
                <CheckCheck className="h-3 w-3 mr-1" />
                Mark all read
              </Button>
            )}
            <Button
              variant="ghost"
              size="sm"
              onClick={onClose}
              className="h-7 w-7 p-0 text-muted-foreground hover:text-foreground"
            >
              <X className="h-3 w-3" />
            </Button>
          </div>
        </div>

        {/* Content */}
        <div className="max-h-96">
          {isLoading ? (
            <div className="p-6 text-center">
              <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-primary mx-auto mb-2" />
              <p className="text-sm text-muted-foreground">Loading notifications...</p>
            </div>
          ) : recentNotifications.length === 0 ? (
            <div className="p-6 text-center">
              <p className="text-sm text-muted-foreground mb-2">No notifications yet</p>
              <p className="text-xs text-muted-foreground">
                We'll notify you about new chapters, updates, and more!
              </p>
            </div>
          ) : (
            <ScrollArea className="max-h-80">
              <div className="divide-y divide-border">
                {recentNotifications.map((notification, index) => (
                  <NotificationItem
                    key={notification.id}
                    notification={notification}
                    onClick={() => handleNotificationClick(notification)}
                    onMarkAsRead={() => markAsRead(notification.id)}
                    className={cn(
                      "transition-colors hover:bg-accent/50",
                      !notification.is_read && "bg-primary/5"
                    )}
                  />
                ))}
              </div>
            </ScrollArea>
          )}
        </div>

        {/* Footer */}
        {recentNotifications.length > 0 && (
          <>
            <Separator />
            <div className="p-3 text-center">
              <Button
                variant="ghost"
                size="sm"
                className="text-xs text-muted-foreground hover:text-foreground"
                onClick={onClose}
              >
                View all notifications
              </Button>
            </div>
          </>
        )}
      </GlassCard>
    </div>
  );
}