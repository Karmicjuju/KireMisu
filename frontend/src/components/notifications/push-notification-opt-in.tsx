'use client';

import React, { useEffect, useState } from 'react';
import { Button } from '@/components/ui/button';
import { GlassCard } from '@/components/ui/glass-card';
import { Switch } from '@/components/ui/switch';
import { Badge } from '@/components/ui/badge';
import { Separator } from '@/components/ui/separator';
import { usePushNotifications } from '@/hooks/use-push-notifications';
import { cn } from '@/lib/utils';
import { 
  Bell, 
  BellOff, 
  BellRing, 
  CheckCircle, 
  XCircle, 
  AlertCircle,
  Smartphone,
  Shield,
  RefreshCw
} from 'lucide-react';

export interface PushNotificationOptInProps {
  className?: string;
  showTestButton?: boolean;
  compact?: boolean;
}

const PERMISSION_STATUS_CONFIG = {
  default: {
    icon: AlertCircle,
    color: 'text-amber-500',
    bgColor: 'bg-amber-50 dark:bg-amber-900/20',
    borderColor: 'border-amber-200 dark:border-amber-800',
    label: 'Not Asked',
    description: 'Permission has not been requested yet',
  },
  granted: {
    icon: CheckCircle,
    color: 'text-green-500',
    bgColor: 'bg-green-50 dark:bg-green-900/20',
    borderColor: 'border-green-200 dark:border-green-800',
    label: 'Allowed',
    description: 'Push notifications are enabled',
  },
  denied: {
    icon: XCircle,
    color: 'text-red-500',
    bgColor: 'bg-red-50 dark:bg-red-900/20',
    borderColor: 'border-red-200 dark:border-red-800',
    label: 'Blocked',
    description: 'Push notifications are blocked in browser settings',
  },
};

export function PushNotificationOptIn({ 
  className, 
  showTestButton = true, 
  compact = false 
}: PushNotificationOptInProps) {
  const {
    isSupported,
    permission,
    subscription,
    subscriptionInfo,
    isLoading,
    error,
    requestPermission,
    subscribe,
    unsubscribe,
    sendTestNotification,
    refreshSubscription,
  } = usePushNotifications();

  const [isToggling, setIsToggling] = useState(false);
  const [showDetails, setShowDetails] = useState(false);

  // Refresh subscription on component mount
  useEffect(() => {
    if (isSupported) {
      refreshSubscription();
    }
  }, [isSupported, refreshSubscription]);

  const isSubscribed = !!subscription;
  const statusConfig = PERMISSION_STATUS_CONFIG[permission];
  const StatusIcon = statusConfig.icon;

  const handleToggleNotifications = async () => {
    if (isLoading || isToggling) return;

    setIsToggling(true);
    try {
      if (isSubscribed) {
        await unsubscribe();
      } else {
        if (permission === 'default') {
          await requestPermission();
        }
        await subscribe();
      }
    } catch (error) {
      console.error('Failed to toggle notifications:', error);
    } finally {
      setIsToggling(false);
    }
  };

  const handleTestNotification = () => {
    sendTestNotification(
      'KireMisu Test Notification',
      'This is a test notification to verify your settings are working correctly.'
    );
  };

  const handleRefresh = async () => {
    await refreshSubscription();
  };

  if (!isSupported) {
    return (
      <GlassCard variant="subtle" className={cn('p-4', className)}>
        <div className="flex items-center gap-3">
          <div className="flex-shrink-0 p-2 rounded-full bg-red-50 dark:bg-red-900/20">
            <Smartphone className="h-4 w-4 text-red-500" />
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-sm font-medium text-foreground">
              Push Notifications Unavailable
            </p>
            <p className="text-xs text-muted-foreground">
              Your browser doesn&apos;t support push notifications
            </p>
          </div>
        </div>
      </GlassCard>
    );
  }

  if (compact) {
    return (
      <div className={cn('flex items-center justify-between gap-3', className)}>
        <div className="flex items-center gap-2">
          <StatusIcon className={cn('h-4 w-4', statusConfig.color)} />
          <span className="text-sm font-medium">Push Notifications</span>
          {isSubscribed && (
            <Badge variant="secondary" className="text-xs">
              Active
            </Badge>
          )}
        </div>
        <Switch
          checked={isSubscribed && permission === 'granted'}
          onCheckedChange={handleToggleNotifications}
          disabled={isLoading || isToggling || permission === 'denied'}
        />
      </div>
    );
  }

  return (
    <GlassCard variant="subtle" className={cn('p-6', className)}>
      {/* Header */}
      <div className="flex items-start justify-between mb-4">
        <div className="flex items-center gap-3">
          <div className={cn(
            'flex-shrink-0 p-2 rounded-full border',
            statusConfig.bgColor,
            statusConfig.borderColor
          )}>
            {isSubscribed ? (
              <BellRing className="h-5 w-5 text-primary" />
            ) : permission === 'denied' ? (
              <BellOff className="h-5 w-5 text-red-500" />
            ) : (
              <Bell className="h-5 w-5 text-muted-foreground" />
            )}
          </div>
          <div>
            <h3 className="text-sm font-semibold text-foreground">
              Push Notifications
            </h3>
            <p className="text-xs text-muted-foreground">
              Get notified about new chapters and updates
            </p>
          </div>
        </div>
        
        <div className="flex items-center gap-2">
          <Button
            variant="ghost"
            size="sm"
            onClick={handleRefresh}
            disabled={isLoading}
            className="h-7 w-7 p-0"
          >
            <RefreshCw className={cn(
              'h-3 w-3',
              isLoading && 'animate-spin'
            )} />
          </Button>
          <Switch
            checked={isSubscribed && permission === 'granted'}
            onCheckedChange={handleToggleNotifications}
            disabled={isLoading || isToggling || permission === 'denied'}
          />
        </div>
      </div>

      {/* Status */}
      <div className={cn(
        'flex items-center gap-2 p-3 rounded-lg border mb-4',
        statusConfig.bgColor,
        statusConfig.borderColor
      )}>
        <StatusIcon className={cn('h-4 w-4', statusConfig.color)} />
        <div className="flex-1 min-w-0">
          <p className="text-sm font-medium text-foreground">
            Status: {statusConfig.label}
          </p>
          <p className="text-xs text-muted-foreground">
            {statusConfig.description}
          </p>
        </div>
        {isSubscribed && (
          <Badge variant="secondary" className="text-xs">
            Subscribed
          </Badge>
        )}
      </div>

      {/* Error Display */}
      {error && (
        <div className="flex items-start gap-2 p-3 rounded-lg bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 mb-4">
          <XCircle className="h-4 w-4 text-red-500 flex-shrink-0 mt-0.5" />
          <div className="flex-1 min-w-0">
            <p className="text-sm font-medium text-red-800 dark:text-red-200">
              Error
            </p>
            <p className="text-xs text-red-600 dark:text-red-300 break-words">
              {error}
            </p>
          </div>
        </div>
      )}

      {/* Permission-specific help text */}
      {permission === 'denied' && (
        <div className="p-3 rounded-lg bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800 mb-4">
          <div className="flex items-start gap-2">
            <Shield className="h-4 w-4 text-amber-500 flex-shrink-0 mt-0.5" />
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium text-amber-800 dark:text-amber-200">
                Notifications Blocked
              </p>
              <p className="text-xs text-amber-600 dark:text-amber-300">
                To enable notifications, click the notification icon in your browser&apos;s address bar or check your browser settings.
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Actions */}
      <div className="flex flex-col gap-3">
        {/* Main action button */}
        <div className="flex items-center gap-2">
          {permission === 'default' && (
            <Button
              onClick={handleToggleNotifications}
              disabled={isLoading || isToggling}
              className="flex-1"
            >
              {isToggling ? (
                <RefreshCw className="h-4 w-4 mr-2 animate-spin" />
              ) : (
                <Bell className="h-4 w-4 mr-2" />
              )}
              Enable Push Notifications
            </Button>
          )}
          
          {permission === 'granted' && !isSubscribed && (
            <Button
              onClick={handleToggleNotifications}
              disabled={isLoading || isToggling}
              className="flex-1"
            >
              {isToggling ? (
                <RefreshCw className="h-4 w-4 mr-2 animate-spin" />
              ) : (
                <BellRing className="h-4 w-4 mr-2" />
              )}
              Subscribe to Notifications
            </Button>
          )}
          
          {permission === 'granted' && isSubscribed && (
            <Button
              variant="destructive"
              onClick={handleToggleNotifications}
              disabled={isLoading || isToggling}
              className="flex-1"
            >
              {isToggling ? (
                <RefreshCw className="h-4 w-4 mr-2 animate-spin" />
              ) : (
                <BellOff className="h-4 w-4 mr-2" />
              )}
              Unsubscribe
            </Button>
          )}
        </div>

        {/* Secondary actions */}
        {permission === 'granted' && isSubscribed && showTestButton && (
          <>
            <Separator />
            <div className="flex items-center gap-2">
              <Button
                variant="outline"
                size="sm"
                onClick={handleTestNotification}
                className="flex-1"
              >
                <BellRing className="h-4 w-4 mr-2" />
                Send Test Notification
              </Button>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setShowDetails(!showDetails)}
                className="px-3"
              >
                {showDetails ? 'Hide' : 'Show'} Details
              </Button>
            </div>
          </>
        )}
      </div>

      {/* Technical details (collapsible) */}
      {showDetails && subscriptionInfo && (
        <>
          <Separator className="my-4" />
          <div className="space-y-2">
            <h4 className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">
              Subscription Details
            </h4>
            <div className="p-3 rounded-lg bg-muted/50 border">
              <div className="space-y-2 text-xs">
                <div className="flex justify-between items-start gap-2">
                  <span className="text-muted-foreground font-medium">Endpoint:</span>
                  <span className="text-right font-mono break-all text-[10px]">
                    {subscriptionInfo.endpoint}
                  </span>
                </div>
                <div className="flex justify-between items-center gap-2">
                  <span className="text-muted-foreground font-medium">Keys:</span>
                  <span className="text-muted-foreground">
                    p256dh & auth configured
                  </span>
                </div>
              </div>
            </div>
          </div>
        </>
      )}
    </GlassCard>
  );
}