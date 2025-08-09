'use client';

import { useCallback } from 'react';
import { mutate } from 'swr';
import { notificationsApi } from '@/lib/api';
import { toast } from '@/hooks/use-toast';

export interface UseNotificationActionsReturn {
  markAsRead: (notificationId: string) => Promise<void>;
  markAllAsRead: () => Promise<void>;
  deleteNotification: (notificationId: string) => Promise<void>;
  deleteAllRead: () => Promise<void>;
}

export function useNotificationActions(): UseNotificationActionsReturn {
  // Mark a single notification as read
  const markAsRead = useCallback(async (notificationId: string) => {
    try {
      await notificationsApi.markAsRead(notificationId);
      
      // Revalidate all notification-related cache keys
      await Promise.all([
        mutate((key) => typeof key === 'string' && key.includes('/api/notifications')),
      ]);
    } catch (error) {
      console.error('Failed to mark notification as read:', error);
      toast({
        title: 'Error',
        description: 'Failed to mark notification as read',
        variant: 'destructive',
      });
      throw error;
    }
  }, []);

  // Mark all notifications as read
  const markAllAsRead = useCallback(async () => {
    try {
      await notificationsApi.markAllAsRead();
      
      // Revalidate all notification-related cache keys
      await Promise.all([
        mutate((key) => typeof key === 'string' && key.includes('/api/notifications')),
      ]);

      toast({
        title: 'Success',
        description: 'All notifications marked as read',
      });
    } catch (error) {
      console.error('Failed to mark all notifications as read:', error);
      toast({
        title: 'Error',
        description: 'Failed to mark all notifications as read',
        variant: 'destructive',
      });
      throw error;
    }
  }, []);

  // Delete a single notification
  const deleteNotification = useCallback(async (notificationId: string) => {
    try {
      await notificationsApi.deleteNotification(notificationId);
      
      // Revalidate all notification-related cache keys
      await Promise.all([
        mutate((key) => typeof key === 'string' && key.includes('/api/notifications')),
      ]);

      toast({
        title: 'Success',
        description: 'Notification deleted',
      });
    } catch (error) {
      console.error('Failed to delete notification:', error);
      toast({
        title: 'Error',
        description: 'Failed to delete notification',
        variant: 'destructive',
      });
      throw error;
    }
  }, []);

  // Delete all read notifications
  const deleteAllRead = useCallback(async () => {
    try {
      await notificationsApi.deleteAllRead();
      
      // Revalidate all notification-related cache keys
      await Promise.all([
        mutate((key) => typeof key === 'string' && key.includes('/api/notifications')),
      ]);

      toast({
        title: 'Success',
        description: 'All read notifications deleted',
      });
    } catch (error) {
      console.error('Failed to delete read notifications:', error);
      toast({
        title: 'Error',
        description: 'Failed to delete read notifications',
        variant: 'destructive',
      });
      throw error;
    }
  }, []);

  return {
    markAsRead,
    markAllAsRead,
    deleteNotification,
    deleteAllRead,
  };
}