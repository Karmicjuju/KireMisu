'use client';

import React from 'react';
import Link from 'next/link';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { cn } from '@/lib/utils';
import { formatDistanceToNow } from 'date-fns';
import { 
  BookOpen, 
  Download, 
  AlertCircle, 
  CheckCircle, 
  Bell, 
  Book,
  Clock,
  X
} from 'lucide-react';
import type { NotificationResponse } from '@/lib/api';

export interface NotificationItemProps {
  notification: NotificationResponse;
  onClick?: () => void;
  onMarkAsRead?: () => void;
  className?: string;
}

function getNotificationIcon(type: string) {
  switch (type) {
    case 'new_chapter':
      return BookOpen;
    case 'chapter_available':
      return Book;
    case 'download_complete':
      return Download;
    case 'download_failed':
      return AlertCircle;
    case 'series_complete':
      return CheckCircle;
    case 'library_update':
      return Bell;
    default:
      return Bell;
  }
}

function getNotificationVariant(type: string) {
  switch (type) {
    case 'new_chapter':
    case 'chapter_available':
      return 'default';
    case 'download_complete':
    case 'series_complete':
      return 'success';
    case 'download_failed':
      return 'destructive';
    case 'library_update':
      return 'secondary';
    default:
      return 'outline';
  }
}

export function NotificationItem({
  notification,
  onClick,
  onMarkAsRead,
  className
}: NotificationItemProps) {
  const IconComponent = getNotificationIcon(notification.type);
  const variant = getNotificationVariant(notification.type);
  
  const timeAgo = formatDistanceToNow(new Date(notification.created_at), {
    addSuffix: true
  });

  const handleClick = () => {
    if (onClick) {
      onClick();
    }
  };

  const handleMarkAsRead = (e: React.MouseEvent) => {
    e.stopPropagation();
    if (onMarkAsRead) {
      onMarkAsRead();
    }
  };

  const content = (
    <div
      className={cn(
        "flex items-start gap-3 p-3 cursor-pointer transition-colors hover:bg-accent/50",
        !notification.is_read && "bg-primary/10 border-l-2 border-l-primary",
        className
      )}
      onClick={handleClick}
    >
      {/* Icon */}
      <div className={cn(
        "flex-shrink-0 rounded-full p-1.5",
        variant === 'success' && "bg-green-100 text-green-600 dark:bg-green-900/20 dark:text-green-400",
        variant === 'destructive' && "bg-red-100 text-red-600 dark:bg-red-900/20 dark:text-red-400",
        variant === 'default' && "bg-primary/10 text-primary",
        variant === 'secondary' && "bg-secondary text-secondary-foreground",
        variant === 'outline' && "bg-muted text-muted-foreground"
      )}>
        <IconComponent className="h-3 w-3" />
      </div>

      {/* Content */}
      <div className="flex-1 min-w-0 space-y-1">
        <div className="flex items-start justify-between gap-2">
          <p className={cn(
            "text-sm line-clamp-2 text-foreground",
            !notification.is_read && "font-medium"
          )}>
            {notification.title}
          </p>
          {!notification.is_read && (
            <Button
              variant="ghost"
              size="sm"
              onClick={handleMarkAsRead}
              className="h-6 w-6 p-0 opacity-0 group-hover:opacity-100 transition-opacity"
              aria-label="Mark as read"
            >
              <X className="h-3 w-3" />
            </Button>
          )}
        </div>

        {notification.message && (
          <p className="text-xs text-foreground/80 line-clamp-2">
            {notification.message}
          </p>
        )}

        <div className="flex items-center justify-between gap-2 text-xs text-foreground/70">
          <div className="flex items-center gap-1">
            <Clock className="h-3 w-3" />
            <span>{timeAgo}</span>
          </div>
          
          {!notification.is_read && (
            <div className="w-2 h-2 bg-primary rounded-full flex-shrink-0" />
          )}
        </div>
      </div>
    </div>
  );

  // If notification has a link, wrap in Link component
  if (notification.link) {
    return (
      <Link href={notification.link} className="block group">
        {content}
      </Link>
    );
  }

  return <div className="group">{content}</div>;
}