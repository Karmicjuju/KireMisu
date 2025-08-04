import React from 'react';
import { Badge } from './badge';
import { JobResponse } from '@/lib/api';

interface JobStatusBadgeProps {
  status: JobResponse['status'];
  className?: string;
  size?: 'sm' | 'default';
}

const statusConfig = {
  pending: {
    variant: 'pending' as const,
    label: 'Pending',
  },
  running: {
    variant: 'running' as const,
    label: 'Running',
  },
  completed: {
    variant: 'success' as const,
    label: 'Completed',
  },
  failed: {
    variant: 'destructive' as const,
    label: 'Failed',
  },
};

export function JobStatusBadge({ status, className, size = 'default' }: JobStatusBadgeProps) {
  const config = statusConfig[status];

  return (
    <Badge
      variant={config.variant}
      className={className}
      style={size === 'sm' ? { fontSize: '0.65rem', padding: '0.125rem 0.5rem' } : undefined}
    >
      {config.label}
    </Badge>
  );
}

interface LibraryPathStatusIndicatorProps {
  isScanning: boolean;
  hasError?: boolean;
  className?: string;
}

export function LibraryPathStatusIndicator({
  isScanning,
  hasError = false,
  className,
}: LibraryPathStatusIndicatorProps) {
  if (isScanning) {
    return (
      <div className={`flex items-center gap-2 ${className}`}>
        <div className="h-2 w-2 animate-pulse rounded-full bg-orange-500" />
        <span className="text-sm text-orange-600">Scanning</span>
      </div>
    );
  }

  if (hasError) {
    return (
      <div className={`flex items-center gap-2 ${className}`}>
        <div className="h-2 w-2 rounded-full bg-red-500" />
        <span className="text-sm text-red-600">Error</span>
      </div>
    );
  }

  return (
    <div className={`flex items-center gap-2 ${className}`}>
      <div className="h-2 w-2 rounded-full bg-green-500" />
      <span className="text-sm text-green-600">Idle</span>
    </div>
  );
}
