/**
 * Page navigation component for manga reader
 */

'use client';

import React from 'react';
import { Button } from '@/components/ui/button';
import { GlassCard } from '@/components/ui/glass-card';
import { cn } from '@/lib/utils';
import { ChevronLeft, ChevronRight, ChevronsLeft, ChevronsRight, Settings, X } from 'lucide-react';

export interface PageNavigationProps {
  currentPage: number;
  totalPages: number;
  onPageChange: (page: number) => void;
  onPrevPage: () => void;
  onNextPage: () => void;
  onFirstPage: () => void;
  onLastPage: () => void;
  onClose?: () => void;
  onSettings?: () => void;
  className?: string;
  show: boolean;
}

export function PageNavigation({
  currentPage,
  totalPages,
  onPageChange,
  onPrevPage,
  onNextPage,
  onFirstPage,
  onLastPage,
  onClose,
  onSettings,
  className,
  show,
}: PageNavigationProps) {
  const handlePageInputChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    const value = parseInt(event.target.value);
    if (!isNaN(value) && value >= 1 && value <= totalPages) {
      onPageChange(value);
    }
  };

  const handlePageInputKeyDown = (event: React.KeyboardEvent<HTMLInputElement>) => {
    if (event.key === 'Enter') {
      event.currentTarget.blur();
    }
  };

  return (
    <div
      className={cn(
        'fixed inset-x-0 bottom-0 z-50 p-4 transition-all duration-300',
        show ? 'translate-y-0 opacity-100' : 'translate-y-full opacity-0',
        className
      )}
    >
      <div className="mx-auto max-w-2xl">
        <GlassCard variant="strong" className="p-4">
          <div className="flex items-center justify-between gap-4">
            {/* Close button */}
            {onClose && (
              <Button
                variant="ghost"
                size="icon"
                onClick={onClose}
                className="shrink-0 hover:bg-white/20"
                aria-label="Close reader"
              >
                <X className="h-4 w-4" />
              </Button>
            )}

            {/* Navigation controls */}
            <div className="flex items-center gap-2">
              <Button
                variant="ghost"
                size="icon"
                onClick={onFirstPage}
                disabled={currentPage === 1}
                className="hover:bg-white/20"
                aria-label="First page"
              >
                <ChevronsLeft className="h-4 w-4" />
              </Button>

              <Button
                variant="ghost"
                size="icon"
                onClick={onPrevPage}
                disabled={currentPage === 1}
                className="hover:bg-white/20"
                aria-label="Previous page"
                data-testid="prev-page-button"
              >
                <ChevronLeft className="h-4 w-4" />
              </Button>

              {/* Page counter */}
              <div className="flex items-center gap-2 text-sm">
                <input
                  type="number"
                  min="1"
                  max={totalPages}
                  value={currentPage}
                  onChange={handlePageInputChange}
                  onKeyDown={handlePageInputKeyDown}
                  className="w-16 rounded border border-white/20 bg-white/10 px-2 py-1 text-center text-white placeholder-white/50 focus:border-white/40 focus:outline-none focus:ring-2 focus:ring-white/20"
                  aria-label={`Current page: ${currentPage}`}
                />
                <span className="text-white/70">/ {totalPages}</span>
              </div>

              <Button
                variant="ghost"
                size="icon"
                onClick={onNextPage}
                disabled={currentPage === totalPages}
                className="hover:bg-white/20"
                aria-label="Next page"
                data-testid="next-page-button"
              >
                <ChevronRight className="h-4 w-4" />
              </Button>

              <Button
                variant="ghost"
                size="icon"
                onClick={onLastPage}
                disabled={currentPage === totalPages}
                className="hover:bg-white/20"
                aria-label="Last page"
              >
                <ChevronsRight className="h-4 w-4" />
              </Button>
            </div>

            {/* Settings button */}
            {onSettings && (
              <Button
                variant="ghost"
                size="icon"
                onClick={onSettings}
                className="shrink-0 hover:bg-white/20"
                aria-label="Reader settings"
              >
                <Settings className="h-4 w-4" />
              </Button>
            )}
          </div>

          {/* Progress bar */}
          <div className="mt-3">
            <div className="h-1 w-full rounded bg-white/20">
              <div
                className="h-full rounded bg-white/60 transition-all duration-200"
                style={{
                  width: `${(currentPage / totalPages) * 100}%`,
                }}
                role="progressbar"
                aria-valuenow={currentPage}
                aria-valuemin={1}
                aria-valuemax={totalPages}
                aria-label={`Reading progress: ${currentPage} of ${totalPages} pages`}
              />
            </div>
          </div>
        </GlassCard>
      </div>
    </div>
  );
}
