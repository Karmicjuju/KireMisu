'use client';

import { useEffect } from 'react';

export function ServiceWorkerRegistration() {
  useEffect(() => {
    // Only register service worker in browser environment and if supported
    if (typeof window === 'undefined' || !('serviceWorker' in navigator)) {
      console.log('Service Worker not supported');
      return;
    }

    const registerServiceWorker = async () => {
      try {
        console.log('Registering service worker...');
        
        const registration = await navigator.serviceWorker.register('/sw.js', {
          scope: '/',
          updateViaCache: 'imports'
        });

        console.log('Service Worker registered successfully:', registration);

        // Handle updates
        registration.addEventListener('updatefound', () => {
          const newWorker = registration.installing;
          if (newWorker) {
            console.log('New service worker available');
            
            newWorker.addEventListener('statechange', () => {
              if (newWorker.state === 'installed') {
                if (navigator.serviceWorker.controller) {
                  // New service worker available, prompt user to refresh
                  console.log('New service worker installed, refresh available');
                  
                  // You could show a notification here asking user to refresh
                  // For now, we'll just log it
                } else {
                  // First time installation
                  console.log('Service worker installed for the first time');
                }
              }
            });
          }
        });

        // Listen for controlling service worker change
        navigator.serviceWorker.addEventListener('controllerchange', () => {
          console.log('Service worker controller changed, reloading page');
          window.location.reload();
        });

      } catch (error) {
        console.error('Service Worker registration failed:', error);
      }
    };

    // Register on page load
    registerServiceWorker();

    // Clean up function
    return () => {
      // No cleanup needed for service worker registration
    };
  }, []);

  // This component renders nothing
  return null;
}

// Utility function to check if service worker is registered and ready
export const isServiceWorkerReady = async (): Promise<boolean> => {
  if (typeof window === 'undefined' || !('serviceWorker' in navigator)) {
    return false;
  }

  try {
    const registration = await navigator.serviceWorker.getRegistration();
    return !!registration && !!registration.active;
  } catch (error) {
    console.error('Error checking service worker status:', error);
    return false;
  }
};

// Utility function to update service worker
export const updateServiceWorker = async (): Promise<void> => {
  if (typeof window === 'undefined' || !('serviceWorker' in navigator)) {
    return;
  }

  try {
    const registration = await navigator.serviceWorker.getRegistration();
    if (registration) {
      await registration.update();
      console.log('Service worker update triggered');
    }
  } catch (error) {
    console.error('Error updating service worker:', error);
  }
};

// Utility function to unregister service worker
export const unregisterServiceWorker = async (): Promise<boolean> => {
  if (typeof window === 'undefined' || !('serviceWorker' in navigator)) {
    return false;
  }

  try {
    const registration = await navigator.serviceWorker.getRegistration();
    if (registration) {
      const result = await registration.unregister();
      console.log('Service worker unregistered:', result);
      return result;
    }
    return false;
  } catch (error) {
    console.error('Error unregistering service worker:', error);
    return false;
  }
};