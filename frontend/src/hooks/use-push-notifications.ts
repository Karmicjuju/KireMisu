'use client';

import { useCallback, useEffect, useState } from 'react';
import { useNotifications } from './use-notifications';

export type NotificationPermission = 'default' | 'granted' | 'denied';

export interface PushSubscriptionInfo {
  endpoint: string;
  keys: {
    p256dh: string;
    auth: string;
  };
}

export interface UsePushNotificationsState {
  isSupported: boolean;
  permission: NotificationPermission;
  subscription: PushSubscription | null;
  subscriptionInfo: PushSubscriptionInfo | null;
  isLoading: boolean;
  error: string | null;
}

export interface UsePushNotificationsActions {
  requestPermission: () => Promise<NotificationPermission>;
  subscribe: () => Promise<PushSubscription | null>;
  unsubscribe: () => Promise<boolean>;
  sendTestNotification: (title: string, body?: string) => void;
  refreshSubscription: () => Promise<void>;
}

export interface UsePushNotificationsReturn extends UsePushNotificationsState, UsePushNotificationsActions {}

// Check if push notifications are supported in the current environment
const checkPushSupport = (): boolean => {
  if (typeof window === 'undefined') return false;
  
  return !!(
    'serviceWorker' in navigator &&
    'PushManager' in window &&
    'Notification' in window
  );
};

// Convert PushSubscription to serializable format
const getSubscriptionInfo = (subscription: PushSubscription | null): PushSubscriptionInfo | null => {
  if (!subscription) return null;
  
  try {
    const p256dhKey = subscription.getKey('p256dh');
    const authKey = subscription.getKey('auth');
    
    if (!p256dhKey || !authKey) return null;
    
    return {
      endpoint: subscription.endpoint,
      keys: {
        p256dh: arrayBufferToBase64(p256dhKey),
        auth: arrayBufferToBase64(authKey),
      },
    };
  } catch (error) {
    console.error('Failed to extract subscription info:', error);
    return null;
  }
};

// Helper function to convert ArrayBuffer to base64
const arrayBufferToBase64 = (buffer: ArrayBuffer): string => {
  const bytes = new Uint8Array(buffer);
  let binary = '';
  for (let i = 0; i < bytes.byteLength; i++) {
    binary += String.fromCharCode(bytes[i]);
  }
  return btoa(binary);
};

// VAPID public key - this should match your backend configuration
const VAPID_PUBLIC_KEY = process.env.NEXT_PUBLIC_VAPID_PUBLIC_KEY || 
  'BEl62iUYgUivxIkv69yViEuiBIa40HI80NM9lE3b6PJdlOOCFjLkjVmCAZ6F6DKUr2b0oLhQhR-ByP3F9PAa6BQ';

// Convert VAPID key from base64 to Uint8Array
const urlBase64ToUint8Array = (base64String: string): Uint8Array => {
  const padding = '='.repeat((4 - (base64String.length % 4)) % 4);
  const base64 = (base64String + padding)
    .replace(/-/g, '+')
    .replace(/_/g, '/');

  const rawData = atob(base64);
  const outputArray = new Uint8Array(rawData.length);

  for (let i = 0; i < rawData.length; ++i) {
    outputArray[i] = rawData.charCodeAt(i);
  }
  return outputArray;
};

export function usePushNotifications(): UsePushNotificationsReturn {
  const [state, setState] = useState<UsePushNotificationsState>({
    isSupported: false,
    permission: 'default',
    subscription: null,
    subscriptionInfo: null,
    isLoading: true,
    error: null,
  });

  // Refresh notifications when subscription changes
  const { mutate: refreshNotifications } = useNotifications();

  // Initialize the hook
  useEffect(() => {
    const initialize = async () => {
      const supported = checkPushSupport();
      
      if (!supported) {
        setState(prev => ({
          ...prev,
          isSupported: false,
          isLoading: false,
          error: 'Push notifications are not supported in this browser',
        }));
        return;
      }

      try {
        // Get current permission status
        const permission = Notification.permission as NotificationPermission;
        
        // Get existing subscription if any
        const registration = await navigator.serviceWorker.ready;
        const subscription = await registration.pushManager.getSubscription();
        
        setState(prev => ({
          ...prev,
          isSupported: true,
          permission,
          subscription,
          subscriptionInfo: getSubscriptionInfo(subscription),
          isLoading: false,
          error: null,
        }));
      } catch (error) {
        console.error('Failed to initialize push notifications:', error);
        setState(prev => ({
          ...prev,
          isSupported: supported,
          isLoading: false,
          error: error instanceof Error ? error.message : 'Failed to initialize push notifications',
        }));
      }
    };

    initialize();
  }, []);

  // Request notification permission
  const requestPermission = useCallback(async (): Promise<NotificationPermission> => {
    if (!state.isSupported) {
      throw new Error('Push notifications are not supported');
    }

    setState(prev => ({ ...prev, isLoading: true, error: null }));

    try {
      const permission = await Notification.requestPermission() as NotificationPermission;
      
      setState(prev => ({
        ...prev,
        permission,
        isLoading: false,
      }));

      return permission;
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Failed to request permission';
      setState(prev => ({
        ...prev,
        isLoading: false,
        error: errorMessage,
      }));
      throw new Error(errorMessage);
    }
  }, [state.isSupported]);

  // Subscribe to push notifications
  const subscribe = useCallback(async (): Promise<PushSubscription | null> => {
    if (!state.isSupported) {
      throw new Error('Push notifications are not supported');
    }

    if (state.permission !== 'granted') {
      const permission = await requestPermission();
      if (permission !== 'granted') {
        throw new Error('Notification permission denied');
      }
    }

    setState(prev => ({ ...prev, isLoading: true, error: null }));

    try {
      const registration = await navigator.serviceWorker.ready;
      
      // Check if already subscribed
      const existingSubscription = await registration.pushManager.getSubscription();
      if (existingSubscription) {
        setState(prev => ({
          ...prev,
          subscription: existingSubscription,
          subscriptionInfo: getSubscriptionInfo(existingSubscription),
          isLoading: false,
        }));
        return existingSubscription;
      }

      // Create new subscription
      const subscription = await registration.pushManager.subscribe({
        userVisibleOnly: true,
        applicationServerKey: urlBase64ToUint8Array(VAPID_PUBLIC_KEY),
      });

      const subscriptionInfo = getSubscriptionInfo(subscription);

      setState(prev => ({
        ...prev,
        subscription,
        subscriptionInfo,
        isLoading: false,
      }));

      // TODO: Send subscription to backend for storage
      // This would typically involve calling an API endpoint to store the subscription
      console.log('Push subscription created:', subscriptionInfo);

      // Refresh notifications to update any subscription-related state
      refreshNotifications();

      return subscription;
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Failed to subscribe to push notifications';
      setState(prev => ({
        ...prev,
        isLoading: false,
        error: errorMessage,
      }));
      throw new Error(errorMessage);
    }
  }, [state.isSupported, state.permission, requestPermission, refreshNotifications]);

  // Unsubscribe from push notifications
  const unsubscribe = useCallback(async (): Promise<boolean> => {
    if (!state.subscription) {
      return true; // Already unsubscribed
    }

    setState(prev => ({ ...prev, isLoading: true, error: null }));

    try {
      const result = await state.subscription.unsubscribe();
      
      if (result) {
        setState(prev => ({
          ...prev,
          subscription: null,
          subscriptionInfo: null,
          isLoading: false,
        }));

        // TODO: Remove subscription from backend
        console.log('Push subscription removed');
        
        // Refresh notifications to update any subscription-related state
        refreshNotifications();
      } else {
        setState(prev => ({
          ...prev,
          isLoading: false,
          error: 'Failed to unsubscribe from push notifications',
        }));
      }

      return result;
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Failed to unsubscribe';
      setState(prev => ({
        ...prev,
        isLoading: false,
        error: errorMessage,
      }));
      throw new Error(errorMessage);
    }
  }, [state.subscription, refreshNotifications]);

  // Send a test notification (local notification, not push)
  const sendTestNotification = useCallback((title: string, body?: string): void => {
    if (!state.isSupported || state.permission !== 'granted') {
      console.warn('Cannot send test notification: permission not granted');
      return;
    }

    try {
      new Notification(title, {
        body: body || 'This is a test notification from KireMisu',
        icon: '/favicon.ico',
        badge: '/badge-72x72.png',
        tag: 'test-notification',
        requireInteraction: false,
        silent: false,
      });
    } catch (error) {
      console.error('Failed to send test notification:', error);
    }
  }, [state.isSupported, state.permission]);

  // Refresh subscription status
  const refreshSubscription = useCallback(async (): Promise<void> => {
    if (!state.isSupported) return;

    setState(prev => ({ ...prev, isLoading: true, error: null }));

    try {
      const registration = await navigator.serviceWorker.ready;
      const subscription = await registration.pushManager.getSubscription();
      const permission = Notification.permission as NotificationPermission;
      
      setState(prev => ({
        ...prev,
        permission,
        subscription,
        subscriptionInfo: getSubscriptionInfo(subscription),
        isLoading: false,
      }));
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Failed to refresh subscription';
      setState(prev => ({
        ...prev,
        isLoading: false,
        error: errorMessage,
      }));
    }
  }, [state.isSupported]);

  return {
    ...state,
    requestPermission,
    subscribe,
    unsubscribe,
    sendTestNotification,
    refreshSubscription,
  };
}

export default usePushNotifications;