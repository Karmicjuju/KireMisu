/**
 * Custom hook for keyboard navigation in manga reader
 */

import { useEffect, useCallback } from 'react';

export interface KeyboardNavigationOptions {
  onNextPage: () => void;
  onPrevPage: () => void;
  onFirstPage?: () => void;
  onLastPage?: () => void;
  onToggleFullscreen?: () => void;
  onExit?: () => void;
  disabled?: boolean;
}

export function useKeyboardNavigation({
  onNextPage,
  onPrevPage,
  onFirstPage,
  onLastPage,
  onToggleFullscreen,
  onExit,
  disabled = false,
}: KeyboardNavigationOptions) {
  const handleKeyDown = useCallback(
    (event: KeyboardEvent) => {
      if (disabled) return;

      // Prevent default behavior for navigation keys
      const navigationKeys = [
        'ArrowLeft',
        'ArrowRight',
        'ArrowUp',
        'ArrowDown',
        'Space',
        'PageUp',
        'PageDown',
        'Home',
        'End',
        'f',
        'F',
        'Escape',
      ];

      if (navigationKeys.includes(event.key)) {
        event.preventDefault();
      }

      // Handle keyboard shortcuts
      switch (event.key) {
        case 'ArrowRight':
        case ' ': // Space bar
        case 'PageDown':
          onNextPage();
          break;

        case 'ArrowLeft':
        case 'PageUp':
          onPrevPage();
          break;

        case 'ArrowDown':
          // For vertical scrolling mode, this could be next page
          onNextPage();
          break;

        case 'ArrowUp':
          // For vertical scrolling mode, this could be prev page
          onPrevPage();
          break;

        case 'Home':
          if (onFirstPage) {
            onFirstPage();
          }
          break;

        case 'End':
          if (onLastPage) {
            onLastPage();
          }
          break;

        case 'f':
        case 'F':
          if (onToggleFullscreen) {
            onToggleFullscreen();
          }
          break;

        case 'Escape':
          if (onExit) {
            onExit();
          }
          break;
      }
    },
    [onNextPage, onPrevPage, onFirstPage, onLastPage, onToggleFullscreen, onExit, disabled]
  );

  useEffect(() => {
    if (disabled) return;

    // Add event listener
    document.addEventListener('keydown', handleKeyDown);

    // Cleanup
    return () => {
      document.removeEventListener('keydown', handleKeyDown);
    };
  }, [handleKeyDown, disabled]);

  // Return keyboard shortcuts for display in UI
  return {
    shortcuts: {
      nextPage: ['→', 'Space', 'Page Down', '↓'],
      prevPage: ['←', 'Page Up', '↑'],
      firstPage: ['Home'],
      lastPage: ['End'],
      fullscreen: ['F'],
      exit: ['Escape'],
    },
  };
}
