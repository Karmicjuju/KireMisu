/**
 * Mark read/unread toggle button component
 */

'use client';

import * as React from 'react';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';
import { Check, BookOpen, Eye, EyeOff, Loader2 } from 'lucide-react';
import { cva, type VariantProps } from 'class-variance-authority';

const markReadButtonVariants = cva(
  'relative transition-all duration-200 focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2',
  {
    variants: {
      variant: {
        default: '',
        subtle: 'border-0 bg-transparent hover:bg-white/10',
        ghost: 'border-0 bg-transparent hover:bg-white/5',
      },
      size: {
        sm: 'h-8 w-8 text-xs',
        default: 'h-9 w-9 text-sm',
        lg: 'h-10 w-10 text-base',
      },
      appearance: {
        icon: '',
        text: 'w-auto px-3',
        full: 'w-auto px-4',
      },
    },
    defaultVariants: {
      variant: 'default',
      size: 'default',
      appearance: 'icon',
    },
  }
);

export interface MarkReadButtonProps
  extends Omit<React.ButtonHTMLAttributes<HTMLButtonElement>, 'onClick' | 'onToggle'>,
    VariantProps<typeof markReadButtonVariants> {
  isRead: boolean;
  isLoading?: boolean;
  onToggle: (isRead: boolean) => void | Promise<void>;
  readLabel?: string;
  unreadLabel?: string;
  showTooltip?: boolean;
}

const MarkReadButton = React.forwardRef<HTMLButtonElement, MarkReadButtonProps>(
  (
    {
      className,
      variant = 'default',
      size = 'default',
      appearance = 'icon',
      isRead,
      isLoading = false,
      onToggle,
      readLabel = 'Mark as unread',
      unreadLabel = 'Mark as read',
      showTooltip = true,
      disabled,
      ...props
    },
    ref
  ) => {
    const [isPending, setIsPending] = React.useState(false);
    const loading = isLoading || isPending;

    const handleClick = async () => {
      if (loading || disabled) return;

      setIsPending(true);
      try {
        await onToggle(!isRead);
      } finally {
        setIsPending(false);
      }
    };

    const getIcon = () => {
      if (loading) {
        return <Loader2 className="h-4 w-4 animate-spin" />;
      }

      if (appearance === 'icon') {
        return isRead ? <Check className="h-4 w-4" /> : <BookOpen className="h-4 w-4" />;
      }

      return isRead ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />;
    };

    const getText = () => {
      if (appearance === 'icon') return null;

      if (appearance === 'text') {
        return isRead ? 'Unread' : 'Read';
      }

      return isRead ? 'Mark as unread' : 'Mark as read';
    };

    const buttonContent = (
      <>
        {getIcon()}
        {getText() && <span className="ml-2">{getText()}</span>}
      </>
    );

    const buttonProps = {
      ref,
      className: cn(
        markReadButtonVariants({ variant, size, appearance }),
        isRead && 'text-green-500 hover:text-green-400',
        !isRead && 'text-slate-400 hover:text-white',
        loading && 'pointer-events-none opacity-50',
        className
      ),
      onClick: handleClick,
      disabled: disabled || loading,
      'aria-label': isRead ? readLabel : unreadLabel,
      'aria-pressed': isRead,
      title: showTooltip ? (isRead ? readLabel : unreadLabel) : undefined,
      ...props,
    };

    if (variant === 'subtle' || variant === 'ghost') {
      return <button {...buttonProps}>{buttonContent}</button>;
    }

    return (
      <Button variant={isRead ? 'default' : 'outline'} size={size} {...buttonProps}>
        {buttonContent}
      </Button>
    );
  }
);

MarkReadButton.displayName = 'MarkReadButton';

// Compound component for batch operations
export interface MarkAllReadButtonProps extends Omit<MarkReadButtonProps, 'isRead' | 'onToggle'> {
  itemCount: number;
  readCount: number;
  onMarkAll: (markAsRead: boolean) => void | Promise<void>;
}

const MarkAllReadButton = React.forwardRef<HTMLButtonElement, MarkAllReadButtonProps>(
  ({ itemCount, readCount, onMarkAll, ...props }, ref) => {
    const allRead = readCount === itemCount;
    const someRead = readCount > 0;

    const handleToggle = (isRead: boolean) => {
      onMarkAll(isRead);
    };

    return (
      <MarkReadButton
        ref={ref}
        isRead={allRead}
        onToggle={handleToggle}
        readLabel={allRead ? 'Mark all as unread' : 'Mark all as read'}
        unreadLabel="Mark all as read"
        appearance="full"
        variant="default"
        className={cn(someRead && !allRead && 'border-orange-500/50 text-orange-500')}
        {...props}
      />
    );
  }
);

MarkAllReadButton.displayName = 'MarkAllReadButton';

export { MarkReadButton, MarkAllReadButton, markReadButtonVariants };
