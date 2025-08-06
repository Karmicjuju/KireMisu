/**
 * Reusable progress bar component with customizable styling and animations
 */

'use client';

import * as React from 'react';
import { cn } from '@/lib/utils';
import { cva, type VariantProps } from 'class-variance-authority';

const progressBarVariants = cva(
  'relative h-2 overflow-hidden rounded-full bg-white/10 transition-all duration-300',
  {
    variants: {
      size: {
        sm: 'h-1',
        default: 'h-2',
        lg: 'h-3',
        xl: 'h-4',
      },
      variant: {
        default: 'bg-white/10',
        subtle: 'bg-white/5',
        strong: 'bg-white/20',
      },
    },
    defaultVariants: {
      size: 'default',
      variant: 'default',
    },
  }
);

const progressFillVariants = cva('h-full transition-all duration-500 ease-out rounded-full', {
  variants: {
    colorScheme: {
      primary: 'bg-gradient-to-r from-orange-500 to-red-500',
      success: 'bg-gradient-to-r from-green-500 to-emerald-500',
      warning: 'bg-gradient-to-r from-yellow-500 to-orange-500',
      info: 'bg-gradient-to-r from-blue-500 to-cyan-500',
      purple: 'bg-gradient-to-r from-purple-500 to-pink-500',
      slate: 'bg-gradient-to-r from-slate-500 to-slate-400',
    },
  },
  defaultVariants: {
    colorScheme: 'primary',
  },
});

export interface ProgressBarProps
  extends React.HTMLAttributes<HTMLDivElement>,
    VariantProps<typeof progressBarVariants> {
  value: number;
  max?: number;
  colorScheme?: VariantProps<typeof progressFillVariants>['colorScheme'];
  showValue?: boolean;
  animated?: boolean;
  label?: string;
  description?: string;
}

const ProgressBar = React.forwardRef<HTMLDivElement, ProgressBarProps>(
  (
    {
      className,
      value,
      max = 100,
      size,
      variant,
      colorScheme = 'primary',
      showValue = false,
      animated = true,
      label,
      description,
      ...props
    },
    ref
  ) => {
    const percentage = Math.min(Math.max((value / max) * 100, 0), 100);
    const [displayValue, setDisplayValue] = React.useState(animated ? 0 : percentage);

    React.useEffect(() => {
      if (animated) {
        const timer = setTimeout(() => {
          setDisplayValue(percentage);
        }, 100);
        return () => clearTimeout(timer);
      } else {
        setDisplayValue(percentage);
      }
    }, [percentage, animated]);

    return (
      <div className="space-y-1">
        {(label || showValue || description) && (
          <div className="flex items-center justify-between text-sm">
            <div className="space-y-0.5">
              {label && <div className="font-medium text-white/90">{label}</div>}
              {description && <div className="text-xs text-white/60">{description}</div>}
            </div>
            {showValue && (
              <div className="font-mono text-xs text-white/70" data-testid="progress-percentage">{Math.round(displayValue)}%</div>
            )}
          </div>
        )}

        <div
          ref={ref}
          className={cn(progressBarVariants({ size, variant }), className)}
          role="progressbar"
          aria-valuenow={value}
          aria-valuemin={0}
          aria-valuemax={max}
          aria-label={label || `Progress: ${Math.round(percentage)}%`}
          data-testid="progress-bar"
          {...props}
        >
          <div
            className={cn(progressFillVariants({ colorScheme }))}
            style={{
              width: `${displayValue}%`,
              transition: animated ? 'width 500ms cubic-bezier(0.65, 0, 0.35, 1)' : 'none',
            }}
            data-testid="progress-fill"
          />

          {/* Shimmer effect for loading state */}
          {animated && displayValue < percentage && (
            <div className="absolute inset-0 overflow-hidden rounded-full">
              <div className="absolute inset-0 -translate-x-full animate-[shimmer_1s_ease-in-out_infinite] bg-gradient-to-r from-transparent via-white/20 to-transparent" />
            </div>
          )}
        </div>
      </div>
    );
  }
);

ProgressBar.displayName = 'ProgressBar';

// Compound component for more complex progress displays
export interface ProgressBarWithStatsProps extends ProgressBarProps {
  current: number;
  total: number;
  unit?: string;
}

const ProgressBarWithStats = React.forwardRef<HTMLDivElement, ProgressBarWithStatsProps>(
  (
    {
      current,
      total,
      unit = 'items',
      label,
      showValue = true,
      value: _value, // Extract value to avoid conflict
      ...props
    },
    ref
  ) => {
    const percentage = total > 0 ? (current / total) * 100 : 0;

    return (
      <ProgressBar
        ref={ref}
        value={percentage}
        label={label}
        description={`${current} / ${total} ${unit}`}
        showValue={showValue}
        {...props}
      />
    );
  }
);

ProgressBarWithStats.displayName = 'ProgressBarWithStats';

export { ProgressBar, ProgressBarWithStats, progressBarVariants };
