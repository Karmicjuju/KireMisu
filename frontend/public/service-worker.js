// Service Worker for KireMisu Push Notifications
// Handles background push notifications for new manga chapters

const SW_VERSION = '1.0.0';
const CACHE_NAME = `kiremisu-cache-v${SW_VERSION}`;

self.addEventListener('install', (event) => {
  console.log(`[Service Worker v${SW_VERSION}] Installing...`);
  
  // Precache essential assets
  event.waitUntil(
    caches.open(CACHE_NAME).then(cache => {
      return cache.addAll([
        '/icon-192x192.png',
        '/badge-72x72.png',
        // Add other essential assets here
      ]).catch(err => {
        console.warn('[Service Worker] Failed to precache some assets:', err);
      });
    })
  );
  
  // Don't skip waiting automatically - let the app control when to update
  // This prevents race conditions with active notifications
});

self.addEventListener('activate', (event) => {
  console.log(`[Service Worker v${SW_VERSION}] Activating...`);
  
  // Clean up old caches
  event.waitUntil(
    caches.keys().then(cacheNames => {
      return Promise.all(
        cacheNames
          .filter(name => name.startsWith('kiremisu-cache-') && name !== CACHE_NAME)
          .map(name => {
            console.log(`[Service Worker] Deleting old cache: ${name}`);
            return caches.delete(name);
          })
      );
    }).then(() => {
      // Take control of all clients after cleanup
      return clients.claim();
    })
  );
});

// Message handler for controlled updates
self.addEventListener('message', (event) => {
  if (event.data && event.data.type === 'SKIP_WAITING') {
    console.log('[Service Worker] Received skip waiting message');
    self.skipWaiting();
  }
});

// Handle push notifications
self.addEventListener('push', (event) => {
  console.log('[Service Worker] Push received:', event);

  let notificationData = {
    title: 'KireMisu',
    body: 'You have a new notification',
    icon: '/icon-192x192.png',
    badge: '/badge-72x72.png',
    tag: 'kiremisu-notification',
    data: {}
  };

  // Parse push data if available
  if (event.data) {
    try {
      const data = event.data.json();
      notificationData = {
        title: data.title || 'KireMisu',
        body: data.body || 'New notification',
        icon: data.icon || '/icon-192x192.png',
        badge: data.badge || '/badge-72x72.png',
        tag: data.tag || `kiremisu-${Date.now()}`,
        data: data.data || {},
        // Additional notification options
        requireInteraction: data.requireInteraction || false,
        renotify: data.renotify || false,
        silent: data.silent || false,
        vibrate: data.vibrate || [200, 100, 200],
        actions: data.actions || []
      };

      // Add actions for new chapter notifications
      if (data.type === 'new_chapter') {
        notificationData.actions = [
          {
            action: 'read',
            title: 'Read Now',
            icon: '/icons/read.png'
          },
          {
            action: 'later',
            title: 'Read Later',
            icon: '/icons/later.png'
          }
        ];
      }
    } catch (error) {
      console.error('[Service Worker] Error parsing push data:', error);
    }
  }

  // Show the notification
  event.waitUntil(
    self.registration.showNotification(notificationData.title, notificationData)
  );
});

// Handle notification clicks
self.addEventListener('notificationclick', (event) => {
  console.log('[Service Worker] Notification clicked:', event);
  
  const notification = event.notification;
  const action = event.action;
  const data = notification.data;

  // Close the notification
  notification.close();

  // Handle different actions
  event.waitUntil(
    clients.matchAll({ type: 'window', includeUncontrolled: true }).then((clientList) => {
      // Handle action buttons
      if (action === 'read' && data.chapterId) {
        // Open reader for the specific chapter
        const url = `/reader/${data.seriesId}/${data.chapterId}`;
        return openOrFocusWindow(clientList, url);
      } else if (action === 'later') {
        // Just close the notification, maybe add to read later list
        return Promise.resolve();
      }

      // Default action - open the appropriate page
      let targetUrl = '/';
      if (data.type === 'new_chapter' && data.seriesId) {
        targetUrl = `/series/${data.seriesId}`;
      } else if (data.type === 'library_update') {
        targetUrl = '/library';
      } else if (data.notificationId) {
        targetUrl = `/notifications?id=${data.notificationId}`;
      }

      return openOrFocusWindow(clientList, targetUrl);
    })
  );
});

// Helper function to open or focus a window
function openOrFocusWindow(clientList, url) {
  // Check if we have a window open
  for (const client of clientList) {
    const clientUrl = new URL(client.url);
    const targetUrl = new URL(url, clientUrl.origin);
    
    // If we have a window on the same origin, focus it and navigate
    if (clientUrl.origin === targetUrl.origin) {
      return client.focus().then((focusedClient) => {
        if (focusedClient && 'navigate' in focusedClient) {
          return focusedClient.navigate(targetUrl.href);
        }
        // Fallback: post message to client
        focusedClient.postMessage({
          type: 'navigate',
          url: targetUrl.href
        });
        return focusedClient;
      });
    }
  }

  // No existing window, open a new one
  if (clients.openWindow) {
    return clients.openWindow(url);
  }

  return Promise.resolve();
}

// Handle background sync for offline notifications
self.addEventListener('sync', (event) => {
  console.log('[Service Worker] Background sync:', event.tag);
  
  if (event.tag === 'sync-notifications') {
    event.waitUntil(syncNotifications());
  }
});

// Sync notifications when back online
async function syncNotifications() {
  try {
    // Fetch any pending notifications from the server
    const response = await fetch('/api/notifications/pending', {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json'
      }
    });

    if (response.ok) {
      const notifications = await response.json();
      // Process and show any pending notifications
      for (const notification of notifications) {
        await self.registration.showNotification(notification.title, {
          body: notification.body,
          icon: notification.icon || '/icon-192x192.png',
          badge: notification.badge || '/badge-72x72.png',
          tag: `sync-${notification.id}`,
          data: notification.data
        });
      }
    }
  } catch (error) {
    console.error('[Service Worker] Sync failed:', error);
  }
}

// Listen for messages from the client
self.addEventListener('message', (event) => {
  console.log('[Service Worker] Message received:', event.data);
  
  if (event.data.type === 'SKIP_WAITING') {
    self.skipWaiting();
  } else if (event.data.type === 'TEST_NOTIFICATION') {
    // Show a test notification
    self.registration.showNotification('Test Notification', {
      body: 'This is a test notification from KireMisu',
      icon: '/icon-192x192.png',
      badge: '/badge-72x72.png',
      tag: 'test-notification',
      vibrate: [200, 100, 200]
    });
  }
});

// Periodic background sync for checking new chapters
self.addEventListener('periodicsync', (event) => {
  if (event.tag === 'check-new-chapters') {
    event.waitUntil(checkForNewChapters());
  }
});

async function checkForNewChapters() {
  try {
    const response = await fetch('/api/watching/check-updates', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      }
    });

    if (response.ok) {
      const result = await response.json();
      console.log('[Service Worker] Chapter check complete:', result);
    }
  } catch (error) {
    console.error('[Service Worker] Chapter check failed:', error);
  }
}