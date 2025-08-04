/**
 * Custom hook for touch/swipe navigation in manga reader
 */

import { useEffect, useRef, useCallback } from 'react';

export interface TouchNavigationOptions {
  onNextPage: () => void;
  onPrevPage: () => void;
  onToggleControls?: () => void;
  disabled?: boolean;
  threshold?: number; // Minimum distance for swipe to register
  preventScroll?: boolean;
}

interface TouchData {
  startX: number;
  startY: number;
  startTime: number;
  isMoving: boolean;
}

export function useTouchNavigation({
  onNextPage,
  onPrevPage,
  onToggleControls,
  disabled = false,
  threshold = 50,
  preventScroll = true,
}: TouchNavigationOptions) {
  const touchData = useRef<TouchData | null>(null);
  const containerRef = useRef<HTMLElement | null>(null);

  const handleTouchStart = useCallback(
    (event: TouchEvent) => {
      if (disabled || event.touches.length !== 1) return;

      const touch = event.touches[0];
      touchData.current = {
        startX: touch.clientX,
        startY: touch.clientY,
        startTime: Date.now(),
        isMoving: false,
      };

      if (preventScroll) {
        event.preventDefault();
      }
    },
    [disabled, preventScroll]
  );

  const handleTouchMove = useCallback(
    (event: TouchEvent) => {
      if (disabled || !touchData.current || event.touches.length !== 1) return;

      const touch = event.touches[0];
      const deltaX = Math.abs(touch.clientX - touchData.current.startX);
      const deltaY = Math.abs(touch.clientY - touchData.current.startY);

      // Mark as moving if threshold is exceeded
      if (deltaX > 10 || deltaY > 10) {
        touchData.current.isMoving = true;
      }

      if (preventScroll) {
        event.preventDefault();
      }
    },
    [disabled, preventScroll]
  );

  const handleTouchEnd = useCallback(
    (event: TouchEvent) => {
      if (disabled || !touchData.current) return;

      const touch = event.changedTouches[0];
      const deltaX = touch.clientX - touchData.current.startX;
      const deltaY = touch.clientY - touchData.current.startY;
      const deltaTime = Date.now() - touchData.current.startTime;
      const absDeltaX = Math.abs(deltaX);
      const absDeltaY = Math.abs(deltaY);

      // Tap detection (no movement, quick release)
      if (!touchData.current.isMoving && deltaTime < 300) {
        if (onToggleControls) {
          onToggleControls();
        }
        touchData.current = null;
        return;
      }

      // Swipe detection
      if (absDeltaX > threshold && absDeltaX > absDeltaY) {
        // Horizontal swipe
        if (deltaX > 0) {
          // Swipe right - previous page (like turning a book page backward)
          onPrevPage();
        } else {
          // Swipe left - next page (like turning a book page forward)
          onNextPage();
        }
      } else if (absDeltaY > threshold && absDeltaY > absDeltaX) {
        // Vertical swipe
        if (deltaY < 0) {
          // Swipe up - next page (for vertical reading)
          onNextPage();
        } else {
          // Swipe down - previous page (for vertical reading)
          onPrevPage();
        }
      }

      touchData.current = null;

      if (preventScroll) {
        event.preventDefault();
      }
    },
    [disabled, threshold, onNextPage, onPrevPage, onToggleControls, preventScroll]
  );

  const setContainer = useCallback((element: HTMLElement | null) => {
    containerRef.current = element;
  }, []);

  useEffect(() => {
    const container = containerRef.current;
    if (disabled || !container) return;

    // Add touch event listeners with passive: false to allow preventDefault
    const options = { passive: false };

    container.addEventListener('touchstart', handleTouchStart, options);
    container.addEventListener('touchmove', handleTouchMove, options);
    container.addEventListener('touchend', handleTouchEnd, options);

    // Cleanup
    return () => {
      container.removeEventListener('touchstart', handleTouchStart);
      container.removeEventListener('touchmove', handleTouchMove);
      container.removeEventListener('touchend', handleTouchEnd);
    };
  }, [handleTouchStart, handleTouchMove, handleTouchEnd, disabled]);

  return {
    setContainer,
    gestures: {
      swipeLeft: 'Next page',
      swipeRight: 'Previous page',
      swipeUp: 'Next page (vertical)',
      swipeDown: 'Previous page (vertical)',
      tap: 'Toggle controls',
    },
  };
}
