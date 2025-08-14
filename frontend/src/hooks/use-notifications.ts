'use client';

import { useCallback } from 'react';
import useSWR, { mutate } from 'swr';
import { notificationsApi, type NotificationResponse } from '@/lib/api';
import { useAuth } from '@/contexts/auth-context';

export interface UseNotificationsReturn {
  data: NotificationResponse[] | undefined;
  error: any;
  isLoading: boolean;
  mutate: () => Promise<NotificationResponse[] | undefined>;
}

export function useNotifications(limit?: number): UseNotificationsReturn {
  const { isAuthenticated } = useAuth();
  
  const {
    data,
    error,
    isLoading,
    mutate: swrMutate,
  } = useSWR<NotificationResponse[]>(
    // Only fetch notifications if user is authenticated
    isAuthenticated 
      ? (limit ? `/api/notifications?limit=${limit}` : '/api/notifications')
      : null,
    () => notificationsApi.getNotifications({ limit }),
    {
      refreshInterval: 60000, // Refresh every 60 seconds (reduced from 30)
      errorRetryCount: 1, // Reduced retry attempts
      revalidateOnFocus: false, // Don't revalidate on focus (was causing constant activity)
      dedupingInterval: 30000, // Increased deduping interval to 30 seconds
      revalidateOnReconnect: false, // Don't revalidate on network reconnect
    }
  );

  return {
    data,
    error,
    isLoading,
    mutate: swrMutate,
  };
}