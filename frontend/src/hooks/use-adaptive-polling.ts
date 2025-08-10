'use client';

import { useCallback, useEffect, useRef, useState } from 'react';

/**
 * Polling strategy configuration
 */
interface PollingStrategy {
  /** Initial polling interval in milliseconds */
  initialInterval: number;
  /** Maximum polling interval in milliseconds */
  maxInterval: number;
  /** Multiplier for exponential backoff */
  backoffMultiplier: number;
  /** Minimum interval when active work is detected */
  activeInterval: number;
  /** How long to wait before considering activity "idle" */
  idleThreshold: number;
}

/**
 * Adaptive polling options
 */
interface AdaptivePollingOptions {
  /** Whether polling is enabled */
  enabled?: boolean;
  /** Function to determine if there's active work */
  hasActiveWork: () => boolean;
  /** Function to fetch data */
  fetchFunction: () => Promise<void>;
  /** Custom polling strategy */
  strategy?: Partial<PollingStrategy>;
  /** Maximum number of consecutive errors before backing off */
  maxConsecutiveErrors?: number;
  /** Whether to stop polling when component unmounts */
  stopOnUnmount?: boolean;
}

/**
 * Adaptive polling state
 */
interface PollingState {
  isPolling: boolean;
  currentInterval: number;
  consecutiveErrors: number;
  lastActivityTime: number | null;
  strategy: PollingStrategy;
}

/**
 * Default polling strategy - more conservative intervals
 */
const DEFAULT_STRATEGY: PollingStrategy = {
  initialInterval: 120000, // 2 minutes
  maxInterval: 600000,     // 10 minutes
  backoffMultiplier: 1.5,
  activeInterval: 60000,   // 1 minute when active (less aggressive)
  idleThreshold: 300000,   // 5 minutes of no activity = idle
};

/**
 * Enhanced adaptive polling hook with exponential backoff and smart frequency management
 */
export function useAdaptivePolling(options: AdaptivePollingOptions) {
  const {
    enabled = true,
    hasActiveWork,
    fetchFunction,
    strategy: customStrategy = {},
    maxConsecutiveErrors = 3,
    stopOnUnmount = true,
  } = options;

  const [pollingState, setPollingState] = useState<PollingState>(() => ({
    isPolling: false,
    currentInterval: DEFAULT_STRATEGY.initialInterval,
    consecutiveErrors: 0,
    lastActivityTime: null,
    strategy: { ...DEFAULT_STRATEGY, ...customStrategy },
  }));

  const intervalRef = useRef<NodeJS.Timeout | null>(null);
  const mountedRef = useRef(true);
  const lastFetchRef = useRef<number>(0);
  const abortControllerRef = useRef<AbortController | null>(null);

  /**
   * Calculate next polling interval based on current state
   */
  const calculateNextInterval = useCallback((currentState: PollingState): number => {
    const { strategy, consecutiveErrors, lastActivityTime } = currentState;
    const now = Date.now();

    // Check if there's currently active work
    const hasActive = hasActiveWork();

    // If there's active work, use the active interval
    if (hasActive) {
      return strategy.activeInterval;
    }

    // If we've had recent activity (within idle threshold), use initial interval
    if (lastActivityTime && (now - lastActivityTime) < strategy.idleThreshold) {
      return strategy.initialInterval;
    }

    // Apply exponential backoff based on consecutive errors or idle time
    const backoffMultiplier = Math.max(1, consecutiveErrors);
    const idleMultiplier = lastActivityTime 
      ? Math.min(3, Math.floor((now - lastActivityTime) / strategy.idleThreshold) + 1)
      : 1;

    const multiplier = Math.max(backoffMultiplier, idleMultiplier);
    const nextInterval = Math.min(
      strategy.maxInterval,
      strategy.initialInterval * Math.pow(strategy.backoffMultiplier, multiplier - 1)
    );

    return nextInterval;
  }, [hasActiveWork]);

  /**
   * Execute polling with error handling and state management
   */
  const executePoll = useCallback(async () => {
    if (!mountedRef.current || !enabled) return;

    // Prevent concurrent polling
    const now = Date.now();
    if (now - lastFetchRef.current < 1000) {
      return; // Minimum 1 second between polls
    }
    lastFetchRef.current = now;

    // Create abort controller for this request
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }
    abortControllerRef.current = new AbortController();

    try {
      await fetchFunction();

      if (!mountedRef.current) return;

      // Reset error count on success
      setPollingState(prev => ({
        ...prev,
        consecutiveErrors: 0,
        lastActivityTime: hasActiveWork() ? now : prev.lastActivityTime,
      }));

    } catch (error) {
      if (!mountedRef.current) return;

      // Only count non-abort errors
      if (error instanceof Error && error.name !== 'AbortError') {
        console.warn('Polling error:', error.message);
        
        setPollingState(prev => ({
          ...prev,
          consecutiveErrors: prev.consecutiveErrors + 1,
        }));
      }
    }
  }, [enabled, fetchFunction, hasActiveWork]);

  /**
   * Start or restart polling with current state
   */
  const startPolling = useCallback(() => {
    if (!enabled || !mountedRef.current) return;

    // Clear existing interval
    if (intervalRef.current) {
      clearInterval(intervalRef.current);
      intervalRef.current = null;
    }

    setPollingState(prev => {
      const nextInterval = calculateNextInterval(prev);
      const shouldPoll = prev.consecutiveErrors < maxConsecutiveErrors;

      if (shouldPoll) {
        // Set up new interval
        intervalRef.current = setInterval(() => {
          executePoll();
        }, nextInterval);

        return {
          ...prev,
          isPolling: true,
          currentInterval: nextInterval,
        };
      }

      return {
        ...prev,
        isPolling: false,
      };
    });
  }, [enabled, calculateNextInterval, executePoll, maxConsecutiveErrors]);

  /**
   * Stop polling
   */
  const stopPolling = useCallback(() => {
    if (intervalRef.current) {
      clearInterval(intervalRef.current);
      intervalRef.current = null;
    }

    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      abortControllerRef.current = null;
    }

    setPollingState(prev => ({
      ...prev,
      isPolling: false,
    }));
  }, []);

  /**
   * Force immediate poll
   */
  const pollNow = useCallback(async () => {
    await executePoll();
    // Restart polling with updated state
    startPolling();
  }, [executePoll, startPolling]);

  /**
   * Reset polling state (useful after errors or user actions)
   */
  const resetPolling = useCallback(() => {
    setPollingState(prev => ({
      ...prev,
      consecutiveErrors: 0,
      currentInterval: prev.strategy.initialInterval,
      lastActivityTime: hasActiveWork() ? Date.now() : null,
    }));
    startPolling();
  }, [hasActiveWork, startPolling]);

  // Effect to manage polling lifecycle
  useEffect(() => {
    if (enabled) {
      // Initial fetch
      executePoll();
      // Start polling
      startPolling();
    } else {
      stopPolling();
    }

    return stopPolling;
  }, [enabled, startPolling, stopPolling, executePoll]);

  // Effect to restart polling when state changes
  useEffect(() => {
    if (enabled && pollingState.isPolling) {
      startPolling();
    }
  }, [pollingState.consecutiveErrors, enabled, startPolling]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      mountedRef.current = false;
      if (stopOnUnmount) {
        stopPolling();
      }
    };
  }, [stopOnUnmount, stopPolling]);

  return {
    /**
     * Current polling state
     */
    isPolling: pollingState.isPolling,
    currentInterval: pollingState.currentInterval,
    consecutiveErrors: pollingState.consecutiveErrors,
    
    /**
     * Control functions
     */
    startPolling,
    stopPolling,
    pollNow,
    resetPolling,
    
    /**
     * Status helpers
     */
    isPaused: !pollingState.isPolling && enabled,
    hasRecentActivity: pollingState.lastActivityTime 
      ? (Date.now() - pollingState.lastActivityTime) < pollingState.strategy.idleThreshold
      : false,
  };
}