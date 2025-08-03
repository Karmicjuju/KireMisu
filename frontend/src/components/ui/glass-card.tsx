import * as React from 'react';
import { cn } from '@/lib/utils';

export interface GlassCardProps extends React.HTMLAttributes<HTMLDivElement> {
  variant?: 'default' | 'subtle' | 'strong';
}

const GlassCard = React.forwardRef<HTMLDivElement, GlassCardProps>(
  ({ className, variant = 'default', ...props }, ref) => {
    const variants = {
      default:
        'backdrop-blur-md bg-white/10 border border-white/20 dark:bg-black/10 dark:border-white/10',
      subtle:
        'backdrop-blur-sm bg-white/5 border border-white/10 dark:bg-black/5 dark:border-white/5',
      strong:
        'backdrop-blur-xl bg-white/20 border border-white/30 dark:bg-black/20 dark:border-white/20',
    };

    return (
      <div
        ref={ref}
        className={cn(
          'rounded-2xl shadow-lg transition-all duration-300',
          'shadow-black/10 dark:shadow-black/50',
          variants[variant],
          className
        )}
        {...props}
      />
    );
  }
);
GlassCard.displayName = 'GlassCard';

export { GlassCard };
