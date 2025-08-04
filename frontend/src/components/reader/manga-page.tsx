/**
 * Individual manga page component with optimized loading
 */

'use client';

import React, { useState, useCallback } from 'react';
import Image from 'next/image';
import { cn } from '@/lib/utils';
import { Loader2, ImageOff } from 'lucide-react';

export interface MangaPageProps {
  src: string;
  alt: string;
  pageNumber: number;
  priority?: boolean;
  className?: string;
  onLoad?: () => void;
  onError?: () => void;
  style?: React.CSSProperties;
}

export function MangaPage({
  src,
  alt,
  pageNumber,
  priority = false,
  className,
  onLoad,
  onError,
  style,
}: MangaPageProps) {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);

  const handleLoad = useCallback(() => {
    setLoading(false);
    setError(false);
    onLoad?.();
  }, [onLoad]);

  const handleError = useCallback(() => {
    setLoading(false);
    setError(true);
    onError?.();
  }, [onError]);

  if (error) {
    return (
      <div
        className={cn(
          'flex min-h-[600px] items-center justify-center rounded-lg bg-slate-800/50',
          className
        )}
        style={style}
      >
        <div className="flex flex-col items-center gap-3 text-white/60">
          <ImageOff className="h-12 w-12" />
          <div className="text-center">
            <p className="text-sm font-medium">Failed to load page {pageNumber}</p>
            <p className="text-xs">Check your connection and try again</p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className={cn('relative overflow-hidden rounded-lg', className)} style={style}>
      {loading && (
        <div className="absolute inset-0 z-10 flex items-center justify-center bg-slate-800/50">
          <div className="flex flex-col items-center gap-3 text-white/60">
            <Loader2 className="h-8 w-8 animate-spin" />
            <p className="text-sm">Loading page {pageNumber}...</p>
          </div>
        </div>
      )}

      <Image
        src={src}
        alt={alt}
        width={0}
        height={0}
        sizes="100vw"
        priority={priority}
        onLoad={handleLoad}
        onError={handleError}
        className={cn(
          'h-auto w-full object-contain transition-opacity duration-200',
          loading ? 'opacity-0' : 'opacity-100'
        )}
        style={{
          maxHeight: '100vh',
          objectFit: 'contain',
        }}
        // Disable dragging
        draggable={false}
        // Add cache control headers
        unoptimized={true}
      />
    </div>
  );
}

export default MangaPage;
