'use client';

import { useEffect, useState } from 'react';

interface ServiceWorkerState {
  isRegistered: boolean;
  isUpdateAvailable: boolean;
  isUpdating: boolean;
  error: string | null;
}

export function ServiceWorkerRegistration() {
  const [swState, setSwState] = useState<ServiceWorkerState>({
    isRegistered: false,
    isUpdateAvailable: false,
    isUpdating: false,
    error: null
  });

  const [registration, setRegistration] = useState<ServiceWorkerRegistration | null>(null);

  // Function to skip waiting and activate new service worker
  const activateNewServiceWorker = () => {
    if (registration?.waiting) {
      setSwState(prev => ({ ...prev, isUpdating: true }));
      registration.waiting.postMessage({ type: 'SKIP_WAITING' });
    }
  };

  // Function to dismiss update notification
  const dismissUpdate = () => {
    setSwState(prev => ({ ...prev, isUpdateAvailable: false }));
  };

  useEffect(() => {
    // DISABLE SERVICE WORKER - causing infinite reload loops
    console.log('Service Worker disabled to fix authentication flow');
    return;

    // Only register service worker in browser environment and if supported
    if (typeof window === 'undefined' || !('serviceWorker' in navigator)) {
      console.log('Service Worker not supported');
      setSwState(prev => ({ ...prev, error: 'Service Worker not supported' }));
      return;
    }

    const registerServiceWorker = async () => {
      try {
        console.log('Registering service worker...');
        
        const reg = await navigator.serviceWorker.register('/sw.js', {
          scope: '/',
          updateViaCache: 'imports'
        });

        setRegistration(reg);
        setSwState(prev => ({ ...prev, isRegistered: true, error: null }));
        console.log('Service Worker registered successfully:', reg);

        // Handle updates with controlled activation
        const handleUpdate = () => {
          const newWorker = reg.installing;
          if (newWorker) {
            console.log('New service worker available');
            
            const handleStateChange = () => {
              if (newWorker.state === 'installed') {
                if (navigator.serviceWorker.controller) {
                  // New service worker available, show update prompt
                  console.log('New service worker installed, update available');
                  setSwState(prev => ({ 
                    ...prev, 
                    isUpdateAvailable: true,
                    isUpdating: false 
                  }));
                } else {
                  // First time installation
                  console.log('Service worker installed for the first time');
                  setSwState(prev => ({ ...prev, isRegistered: true }));
                }
              }
            };

            newWorker.addEventListener('statechange', handleStateChange);
            
            // Clean up listener when component unmounts
            return () => {
              newWorker.removeEventListener('statechange', handleStateChange);
            };
          }
        };

        reg.addEventListener('updatefound', handleUpdate);

        // Listen for controlling service worker change (when new SW takes control)
        const handleControllerChange = () => {
          console.log('Service worker controller changed');
          setSwState(prev => ({ ...prev, isUpdating: false }));
          // Don't auto-reload to prevent infinite reload loop during first installation
          // window.location.reload();
        };

        navigator.serviceWorker.addEventListener('controllerchange', handleControllerChange);

        // Check for existing updates
        if (reg.waiting) {
          setSwState(prev => ({ ...prev, isUpdateAvailable: true }));
        }

        // Periodically check for updates (every 30 minutes)
        const updateInterval = setInterval(() => {
          if (reg) {
            reg.update().catch(console.error);
          }
        }, 30 * 60 * 1000);

        // Clean up function
        return () => {
          reg.removeEventListener('updatefound', handleUpdate);
          navigator.serviceWorker.removeEventListener('controllerchange', handleControllerChange);
          clearInterval(updateInterval);
        };

      } catch (error) {
        console.error('Service Worker registration failed:', error);
        setSwState(prev => ({ 
          ...prev, 
          error: error instanceof Error ? error.message : 'Registration failed' 
        }));
      }
    };

    // Register on page load
    const cleanup = registerServiceWorker();

    return () => {
      cleanup?.then(cleanupFn => cleanupFn?.());
    };
  }, []);

  // Show update notification when available
  if (swState.isUpdateAvailable && !swState.isUpdating) {
    return (
      <div style={{
        position: 'fixed',
        bottom: '20px',
        right: '20px',
        backgroundColor: '#4f46e5',
        color: 'white',
        padding: '16px',
        borderRadius: '8px',
        boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.1)',
        zIndex: 9999,
        maxWidth: '350px'
      }}>
        <div style={{ marginBottom: '12px' }}>
          <strong>App Update Available</strong>
        </div>
        <div style={{ marginBottom: '12px', fontSize: '14px' }}>
          A new version of KireMisu is available. Update now for the latest features and improvements.
        </div>
        <div style={{ display: 'flex', gap: '8px' }}>
          <button
            onClick={activateNewServiceWorker}
            style={{
              backgroundColor: 'white',
              color: '#4f46e5',
              border: 'none',
              padding: '8px 16px',
              borderRadius: '4px',
              cursor: 'pointer',
              fontSize: '14px',
              fontWeight: 'bold'
            }}
          >
            Update Now
          </button>
          <button
            onClick={dismissUpdate}
            style={{
              backgroundColor: 'transparent',
              color: 'white',
              border: '1px solid white',
              padding: '8px 16px',
              borderRadius: '4px',
              cursor: 'pointer',
              fontSize: '14px'
            }}
          >
            Later
          </button>
        </div>
      </div>
    );
  }

  // Show loading state during update
  if (swState.isUpdating) {
    return (
      <div style={{
        position: 'fixed',
        bottom: '20px',
        right: '20px',
        backgroundColor: '#059669',
        color: 'white',
        padding: '16px',
        borderRadius: '8px',
        boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.1)',
        zIndex: 9999
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <div style={{
            width: '20px',
            height: '20px',
            border: '2px solid transparent',
            borderTop: '2px solid white',
            borderRadius: '50%',
            animation: 'spin 1s linear infinite'
          }}></div>
          <span>Updating app...</span>
        </div>
        <style jsx>{`
          @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
          }
        `}</style>
      </div>
    );
  }

  // This component renders nothing when no update is available
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