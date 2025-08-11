// Service Worker for KireMisu Push Notifications
// This service worker handles push notification events

const CACHE_NAME = 'kiremisu-notifications-v1';

// Install event
self.addEventListener('install', (event) => {
  console.log('[SW] Installing service worker for push notifications');
  self.skipWaiting(); // Activate immediately
});

// Activate event
self.addEventListener('activate', (event) => {
  console.log('[SW] Activating service worker for push notifications');
  event.waitUntil(self.clients.claim()); // Take control immediately
});

// Push event handler
self.addEventListener('push', (event) => {
  console.log('[SW] Push event received:', event);

  if (!event.data) {
    console.log('[SW] Push event has no data');
    return;
  }

  try {
    const data = event.data.json();
    console.log('[SW] Push data:', data);

    const options = {
      body: data.body || 'You have a new notification from KireMisu',
      icon: data.icon || '/icon-192x192.png',
      badge: data.badge || '/badge-72x72.png',
      image: data.image,
      data: data.data || {},
      tag: data.tag || 'kiremisu-notification',
      requireInteraction: data.requireInteraction || false,
      silent: data.silent || false,
      timestamp: Date.now(),
      actions: data.actions || [],
      dir: data.dir || 'auto',
      lang: data.lang || 'en',
      renotify: data.renotify || false,
      vibrate: data.vibrate || [200, 100, 200]
    };

    const title = data.title || 'KireMisu';

    event.waitUntil(
      self.registration.showNotification(title, options)
        .then(() => {
          console.log('[SW] Notification shown successfully');
        })
        .catch((error) => {
          console.error('[SW] Failed to show notification:', error);
        })
    );
  } catch (error) {
    console.error('[SW] Error processing push event:', error);
    
    // Fallback notification
    event.waitUntil(
      self.registration.showNotification('KireMisu', {
        body: 'You have a new notification',
        icon: '/icon-192x192.png',
        badge: '/badge-72x72.png',
        tag: 'kiremisu-fallback'
      })
    );
  }
});

// Notification click handler
self.addEventListener('notificationclick', (event) => {
  console.log('[SW] Notification clicked:', event);

  event.notification.close();

  const data = event.notification.data || {};
  const url = data.url || '/';

  event.waitUntil(
    clients.matchAll({ type: 'window', includeUncontrolled: true })
      .then((clientList) => {
        console.log('[SW] Found clients:', clientList.length);

        // Check if there's already a window/tab open with the app
        for (let i = 0; i < clientList.length; i++) {
          const client = clientList[i];
          if (client.url.includes(self.location.origin)) {
            console.log('[SW] Focusing existing client:', client.url);
            
            // Navigate to the notification URL if specified
            if (url !== '/' && client.navigate) {
              client.navigate(url);
            }
            
            return client.focus();
          }
        }

        // If no existing client, open a new window
        console.log('[SW] Opening new client window:', url);
        return clients.openWindow(url);
      })
      .catch((error) => {
        console.error('[SW] Error handling notification click:', error);
      })
  );
});

// Notification close handler
self.addEventListener('notificationclose', (event) => {
  console.log('[SW] Notification closed:', event.notification.tag);

  const data = event.notification.data || {};
  
  // Optional: Send analytics or tracking data
  if (data.trackClose) {
    console.log('[SW] Tracking notification close');
    // Could send to analytics endpoint here
  }
});

// Background sync for offline notifications
self.addEventListener('sync', (event) => {
  console.log('[SW] Background sync event:', event.tag);

  if (event.tag === 'notification-sync') {
    event.waitUntil(
      // Handle background sync for notifications
      syncNotifications()
    );
  }
});

// Handle background sync
async function syncNotifications() {
  try {
    console.log('[SW] Syncing notifications in background');
    
    // This could fetch unread notifications from the server
    // and show them to the user when they come back online
    
    const response = await fetch('/api/notifications?unread_only=true&limit=5');
    
    if (response.ok) {
      const notifications = await response.json();
      
      // Show notifications that were missed while offline
      for (const notification of notifications.slice(0, 3)) { // Limit to 3 to avoid spam
        await self.registration.showNotification(notification.title, {
          body: notification.message,
          tag: `sync-${notification.id}`,
          data: { url: notification.link }
        });
      }
    }
  } catch (error) {
    console.error('[SW] Error syncing notifications:', error);
  }
}

// Message handler for communication with the main thread
self.addEventListener('message', (event) => {
  console.log('[SW] Message received:', event.data);

  const { type, payload } = event.data;

  switch (type) {
    case 'SKIP_WAITING':
      self.skipWaiting();
      break;
      
    case 'GET_VERSION':
      event.ports[0].postMessage({ version: CACHE_NAME });
      break;
      
    case 'CLEAR_NOTIFICATIONS':
      // Clear all notifications with a specific tag
      self.registration.getNotifications({ tag: payload.tag })
        .then(notifications => {
          notifications.forEach(notification => notification.close());
        });
      break;
      
    default:
      console.log('[SW] Unknown message type:', type);
  }
});