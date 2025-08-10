'use client';

import React, { useEffect, useRef, useState } from 'react';
import { createPortal } from 'react-dom';
import { GlassCard } from '@/components/ui/glass-card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Separator } from '@/components/ui/separator';
import { ScrollArea } from '@/components/ui/scroll-area';
import { NotificationItem } from './notification-item';
import { PushNotificationOptIn } from './push-notification-opt-in';
import { useNotificationActions } from '@/hooks/use-notification-actions';
import { cn } from '@/lib/utils';
import { CheckCheck, X, Settings } from 'lucide-react';
import type { NotificationResponse } from '@/lib/api';

export interface NotificationDropdownProps {
  isOpen: boolean;
  onClose: () => void;
  notifications: NotificationResponse[];
  isLoading: boolean;
  className?: string;
  triggerRef?: React.RefObject<HTMLElement>;
  showPushSettings?: boolean;
}

export function NotificationDropdown({
  isOpen,
  onClose,
  notifications,
  isLoading,
  className,
  triggerRef,
  showPushSettings = true
}: NotificationDropdownProps) {
  const dropdownRef = useRef<HTMLDivElement>(null);
  const [mounted, setMounted] = useState(false);
  const [position, setPosition] = useState({ top: 0, right: 0 });
  const [showSettings, setShowSettings] = useState(false);
  const { markAsRead, markAllAsRead } = useNotificationActions();

  // Track mounting for portal
  useEffect(() => {
    setMounted(true);
  }, []);

  // Calculate position based on trigger element
  useEffect(() => {
    if (triggerRef?.current && isOpen) {
      const rect = triggerRef.current.getBoundingClientRect();
      setPosition({
        top: rect.bottom + 8, // 8px gap below the trigger
        right: window.innerWidth - rect.right, // Distance from right edge
      });
    }
  }, [triggerRef, isOpen]);

  // Close dropdown when clicking outside
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        // Also check if click is on the trigger
        if (triggerRef?.current && !triggerRef.current.contains(event.target as Node)) {
          onClose();
        }
      }
    }

    if (isOpen) {
      document.addEventListener('mousedown', handleClickOutside);
      return () => document.removeEventListener('mousedown', handleClickOutside);
    }
  }, [isOpen, onClose, triggerRef]);

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

  if (!isOpen || !mounted) return null;

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

  const dropdownContent = (
    <div
      ref={dropdownRef}
      className={cn(
        "fixed z-[99999] w-96 max-w-[90vw] animate-in slide-in-from-top-2",
        className
      )}
      style={{
        top: `${position.top}px`,
        right: `${position.right}px`,
      }}
    >
      <GlassCard variant="strong" className="overflow-hidden shadow-2xl border-border bg-card/95 backdrop-blur-xl relative z-10">
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-border">
          <div className="flex items-center gap-2">
            <h3 className="font-semibold text-sm text-foreground">Notifications</h3>
            {unreadNotifications.length > 0 && (
              <Badge variant="default" className="text-xs bg-primary text-primary-foreground">
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
                className="h-7 px-2 text-xs text-foreground/80 hover:text-foreground hover:bg-accent"
              >
                <CheckCheck className="h-3 w-3 mr-1" />
                Mark all read
              </Button>
            )}
            <Button
              variant="ghost"
              size="sm"
              onClick={onClose}
              className="h-7 w-7 p-0 text-foreground/80 hover:text-foreground hover:bg-accent"
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
              <p className="text-sm text-foreground/80">Loading notifications...</p>
            </div>
          ) : recentNotifications.length === 0 ? (
            <div className="p-6 text-center">
              <p className="text-sm text-foreground mb-2">No notifications yet</p>
              <p className="text-xs text-foreground/70">
                We&apos;ll notify you about new chapters, updates, and more!
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
                      "transition-colors hover:bg-accent/30"
                    )}
                  />
                ))}
              </div>
            </ScrollArea>
          )}
        </div>

        {/* Footer */}
        {(recentNotifications.length > 0 || showPushSettings) && (
          <>
            <Separator />
            <div className="p-3 space-y-3">
              {/* Settings Toggle */}
              {showPushSettings && (
                <div className="flex items-center justify-between">
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => setShowSettings(!showSettings)}
                    className="text-xs text-foreground/80 hover:text-foreground hover:bg-accent"
                  >
                    <Settings className="h-3 w-3 mr-1" />
                    Push Settings
                  </Button>
                  {recentNotifications.length > 0 && (
                    <Button
                      variant="ghost"
                      size="sm"
                      className="text-xs text-foreground/80 hover:text-foreground hover:bg-accent"
                      onClick={onClose}
                    >
                      View all notifications
                    </Button>
                  )}
                </div>
              )}
              
              {/* View all button if no push settings */}
              {!showPushSettings && recentNotifications.length > 0 && (
                <div className="text-center">
                  <Button
                    variant="ghost"
                    size="sm"
                    className="text-xs text-foreground/80 hover:text-foreground hover:bg-accent"
                    onClick={onClose}
                  >
                    View all notifications
                  </Button>
                </div>
              )}

              {/* Push Notification Settings */}
              {showPushSettings && showSettings && (
                <>
                  <Separator />
                  <PushNotificationOptIn
                    compact={true}
                    showTestButton={false}
                    className="px-0"
                  />
                </>
              )}
            </div>
          </>
        )}
      </GlassCard>
    </div>
  );

  // Render dropdown using portal to bypass z-index stacking issues
  return createPortal(dropdownContent, document.body);
}