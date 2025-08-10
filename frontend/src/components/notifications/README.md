# Push Notifications Components

This directory contains React components for implementing web push notifications in KireMisu.

## Components

### `PushNotificationOptIn`

A comprehensive component for managing push notification permissions and subscriptions.

**Features:**
- Browser support detection
- Permission status display with visual indicators
- Subscribe/unsubscribe functionality  
- Test notification capability
- Technical details view (subscription endpoint, keys)
- Compact and full UI modes
- Error handling with user-friendly messages

**Props:**
- `className?: string` - Additional CSS classes
- `showTestButton?: boolean` - Show/hide test notification button (default: true)
- `compact?: boolean` - Use compact layout mode (default: false)

**Usage:**
```tsx
import { PushNotificationOptIn } from '@/components/notifications';

// Full UI mode
<PushNotificationOptIn />

// Compact mode for dropdowns/settings
<PushNotificationOptIn compact={true} showTestButton={false} />
```

### `usePushNotifications` Hook

A custom hook for managing push notification state and actions.

**Returns:**
- `isSupported: boolean` - Browser support for push notifications
- `permission: NotificationPermission` - Current permission status
- `subscription: PushSubscription | null` - Active subscription
- `subscriptionInfo: PushSubscriptionInfo | null` - Serializable subscription data
- `isLoading: boolean` - Loading state
- `error: string | null` - Error message
- `requestPermission(): Promise<NotificationPermission>` - Request permission
- `subscribe(): Promise<PushSubscription | null>` - Subscribe to push notifications
- `unsubscribe(): Promise<boolean>` - Unsubscribe from push notifications
- `sendTestNotification(title, body?): void` - Send test notification
- `refreshSubscription(): Promise<void>` - Refresh subscription status

**Usage:**
```tsx
import { usePushNotifications } from '@/hooks/use-push-notifications';

function MyComponent() {
  const { 
    isSupported, 
    permission, 
    subscribe, 
    sendTestNotification 
  } = usePushNotifications();

  if (!isSupported) return <div>Push notifications not supported</div>;

  return (
    <div>
      <p>Permission: {permission}</p>
      <button onClick={subscribe}>Subscribe</button>
      <button onClick={() => sendTestNotification('Test', 'Hello!')}>
        Test
      </button>
    </div>
  );
}
```

## Integration with Notification Dropdown

The push notification settings are automatically integrated into the main notification dropdown:

1. A "Push Settings" button appears at the bottom of the dropdown
2. Clicking it reveals the compact `PushNotificationOptIn` component
3. Users can toggle notifications on/off directly from the dropdown

## Service Worker

The system includes a service worker (`/public/sw.js`) that handles:

- Push event processing
- Notification display with custom options
- Click/close event handling
- Background sync for offline notifications
- Message passing with the main thread

The service worker is automatically registered via the `ServiceWorkerRegistration` component.

## PWA Support

Full Progressive Web App support with:

- Web App Manifest (`/public/manifest.json`)
- Service worker registration
- Push notification capabilities
- Offline functionality
- App shortcuts and icons

## Environment Variables

Configure VAPID keys in your environment:

```env
NEXT_PUBLIC_VAPID_PUBLIC_KEY=your_vapid_public_key_here
```

## Browser Support

Push notifications require:
- HTTPS (or localhost for development)
- Modern browser with service worker support
- User permission granted

Supported browsers:
- Chrome/Edge 42+
- Firefox 44+
- Safari 16+ (limited support)
- Opera 29+

## Error Handling

The components provide comprehensive error handling:
- Browser support detection
- Permission denied scenarios
- Network failures
- Subscription errors
- Service worker registration issues

All errors are displayed with user-friendly messages and suggested actions.