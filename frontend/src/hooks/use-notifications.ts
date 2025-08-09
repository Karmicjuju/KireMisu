'use client';

import { useCallback } from 'react';
import useSWR, { mutate } from 'swr';
import { notificationsApi, type NotificationResponse } from '@/lib/api';

export interface UseNotificationsReturn {
  data: NotificationResponse[] | undefined;
  error: any;
  isLoading: boolean;
  mutate: () => Promise<NotificationResponse[] | undefined>;
}

export function useNotifications(limit?: number): UseNotificationsReturn {
  const {
    data,
    error,
    isLoading,
    mutate: swrMutate,
  } = useSWR<NotificationResponse[]>(
    limit ? `/api/notifications?limit=${limit}` : '/api/notifications',
    () => notificationsApi.getNotifications({ limit }),
    {
      refreshInterval: 30000, // Refresh every 30 seconds
      errorRetryCount: 2,
      revalidateOnFocus: true,
      dedupingInterval: 10000, // Dedupe requests within 10 seconds
    }
  );

  return {
    data,
    error,
    isLoading,
    mutate: swrMutate,
  };
}