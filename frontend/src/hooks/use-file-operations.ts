"use client";

/**
 * Hook for managing file operations
 * 
 * Provides a clean interface for:
 * - Creating and managing file operations
 * - Tracking operation status
 * - Handling errors and retries
 * - Managing operation history
 */

import { useState, useCallback, useEffect } from 'react';

interface FileOperation {
  id: string;
  operation_type: string;
  status: string;
  source_path: string;
  target_path?: string;
  backup_path?: string;
  affected_series_ids: string[];
  affected_chapter_ids: string[];
  error_message?: string;
  started_at?: string;
  completed_at?: string;
  created_at: string;
  updated_at: string;
}

interface ValidationResult {
  is_valid: boolean;
  warnings: string[];
  errors: string[];
  conflicts: Array<{
    type: string;
    path: string;
    message: string;
  }>;
  affected_series_count: number;
  affected_chapter_count: number;
  risk_level: 'low' | 'medium' | 'high';
  requires_confirmation: boolean;
  estimated_duration_seconds?: number;
  estimated_disk_usage_mb?: number;
}

interface UseFileOperationsReturn {
  // Current operations
  operations: FileOperation[];
  activeOperation: FileOperation | null;
  
  // Loading states
  loading: boolean;
  validating: boolean;
  executing: boolean;
  
  // Error handling
  error: string | null;
  validation: ValidationResult | null;
  
  // Actions
  createOperation: (request: {
    operation_type: 'rename' | 'delete' | 'move';
    source_path: string;
    target_path?: string;
    create_backup?: boolean;
    validate_database_consistency?: boolean;
  }) => Promise<FileOperation>;
  
  validateOperation: (operationId: string) => Promise<ValidationResult>;
  executeOperation: (operationId: string, confirmed: boolean) => Promise<FileOperation>;
  rollbackOperation: (operationId: string) => Promise<FileOperation>;
  getOperation: (operationId: string) => Promise<FileOperation>;
  listOperations: (filters?: {
    status_filter?: string;
    operation_type_filter?: string;
    limit?: number;
    offset?: number;
  }) => Promise<FileOperation[]>;
  
  // Utility actions
  clearError: () => void;
  refreshOperations: () => Promise<void>;
  cleanupOldOperations: (daysOld?: number) => Promise<{ cleaned_count: number }>;
}

export const useFileOperations = (): UseFileOperationsReturn => {
  const [operations, setOperations] = useState<FileOperation[]>([]);
  const [activeOperation, setActiveOperation] = useState<FileOperation | null>(null);
  const [loading, setLoading] = useState(false);
  const [validating, setValidating] = useState(false);
  const [executing, setExecuting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [validation, setValidation] = useState<ValidationResult | null>(null);

  // Helper function for API calls
  const apiCall = useCallback(async <T>(url: string, options?: RequestInit): Promise<T> => {
    const response = await fetch(url, {
      headers: {
        'Content-Type': 'application/json',
        ...options?.headers,
      },
      ...options,
    });

    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(errorData.detail || `HTTP error! status: ${response.status}`);
    }

    return response.json();
  }, []);

  // Create a new file operation
  const createOperation = useCallback(async (request: {
    operation_type: 'rename' | 'delete' | 'move';
    source_path: string;
    target_path?: string;
    create_backup?: boolean;
    validate_database_consistency?: boolean;
  }): Promise<FileOperation> => {
    setLoading(true);
    setError(null);
    
    try {
      const operation = await apiCall<FileOperation>('/api/file-operations/', {
        method: 'POST',
        body: JSON.stringify(request),
      });
      
      setActiveOperation(operation);
      setOperations(prev => [operation, ...prev]);
      
      return operation;
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to create operation';
      setError(errorMessage);
      throw err;
    } finally {
      setLoading(false);
    }
  }, [apiCall]);

  // Validate an operation
  const validateOperation = useCallback(async (operationId: string): Promise<ValidationResult> => {
    setValidating(true);
    setError(null);
    
    try {
      const validationResult = await apiCall<ValidationResult>(
        `/api/file-operations/${operationId}/validate`,
        { method: 'POST' }
      );
      
      setValidation(validationResult);
      
      // Update operation status in local state
      setOperations(prev => prev.map(op => 
        op.id === operationId 
          ? { ...op, status: validationResult.is_valid ? 'validated' : 'failed' }
          : op
      ));
      
      if (activeOperation?.id === operationId) {
        setActiveOperation(prev => prev ? {
          ...prev,
          status: validationResult.is_valid ? 'validated' : 'failed'
        } : null);
      }
      
      return validationResult;
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Validation failed';
      setError(errorMessage);
      throw err;
    } finally {
      setValidating(false);
    }
  }, [apiCall, activeOperation]);

  // Execute an operation
  const executeOperation = useCallback(async (operationId: string, confirmed: boolean): Promise<FileOperation> => {
    setExecuting(true);
    setError(null);
    
    try {
      const operation = await apiCall<FileOperation>(
        `/api/file-operations/${operationId}/execute`,
        {
          method: 'POST',
          body: JSON.stringify({
            operation_id: operationId,
            confirmed,
            confirmation_message: 'Confirmed via UI'
          }),
        }
      );
      
      // Update operation in local state
      setOperations(prev => prev.map(op => op.id === operationId ? operation : op));
      
      if (activeOperation?.id === operationId) {
        setActiveOperation(operation);
      }
      
      return operation;
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Execution failed';
      setError(errorMessage);
      throw err;
    } finally {
      setExecuting(false);
    }
  }, [apiCall, activeOperation]);

  // Rollback an operation
  const rollbackOperation = useCallback(async (operationId: string): Promise<FileOperation> => {
    setLoading(true);
    setError(null);
    
    try {
      const operation = await apiCall<FileOperation>(
        `/api/file-operations/${operationId}/rollback`,
        { method: 'POST' }
      );
      
      // Update operation in local state
      setOperations(prev => prev.map(op => op.id === operationId ? operation : op));
      
      if (activeOperation?.id === operationId) {
        setActiveOperation(operation);
      }
      
      return operation;
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Rollback failed';
      setError(errorMessage);
      throw err;
    } finally {
      setLoading(false);
    }
  }, [apiCall, activeOperation]);

  // Get a specific operation
  const getOperation = useCallback(async (operationId: string): Promise<FileOperation> => {
    setLoading(true);
    setError(null);
    
    try {
      const operation = await apiCall<FileOperation>(`/api/file-operations/${operationId}`);
      
      // Update operation in local state if it exists
      setOperations(prev => {
        const exists = prev.some(op => op.id === operationId);
        if (exists) {
          return prev.map(op => op.id === operationId ? operation : op);
        } else {
          return [operation, ...prev];
        }
      });
      
      return operation;
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to get operation';
      setError(errorMessage);
      throw err;
    } finally {
      setLoading(false);
    }
  }, [apiCall]);

  // List operations with optional filters
  const listOperations = useCallback(async (filters?: {
    status_filter?: string;
    operation_type_filter?: string;
    limit?: number;
    offset?: number;
  }): Promise<FileOperation[]> => {
    setLoading(true);
    setError(null);
    
    try {
      const params = new URLSearchParams();
      if (filters?.status_filter) params.append('status_filter', filters.status_filter);
      if (filters?.operation_type_filter) params.append('operation_type_filter', filters.operation_type_filter);
      if (filters?.limit) params.append('limit', filters.limit.toString());
      if (filters?.offset) params.append('offset', filters.offset.toString());
      
      const url = `/api/file-operations/${params.toString() ? `?${params.toString()}` : ''}`;
      const response = await apiCall<{ operations: FileOperation[]; total: number }>(url);
      
      setOperations(response.operations);
      return response.operations;
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to list operations';
      setError(errorMessage);
      throw err;
    } finally {
      setLoading(false);
    }
  }, [apiCall]);

  // Refresh operations list
  const refreshOperations = useCallback(async (): Promise<void> => {
    await listOperations({ limit: 50 });
  }, [listOperations]);

  // Clean up old operations
  const cleanupOldOperations = useCallback(async (daysOld: number = 30): Promise<{ cleaned_count: number }> => {
    setLoading(true);
    setError(null);
    
    try {
      const result = await apiCall<{ cleaned_count: number }>(
        `/api/file-operations/cleanup?days_old=${daysOld}`,
        { method: 'DELETE' }
      );
      
      // Refresh operations list after cleanup
      await refreshOperations();
      
      return result;
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Cleanup failed';
      setError(errorMessage);
      throw err;
    } finally {
      setLoading(false);
    }
  }, [apiCall, refreshOperations]);

  // Clear error state
  const clearError = useCallback(() => {
    setError(null);
  }, []);

  // Convenience methods for common operations
  const renameFile = useCallback(async (sourcePath: string, targetPath: string, options?: {
    create_backup?: boolean;
    validate_database_consistency?: boolean;
  }): Promise<FileOperation> => {
    return createOperation({
      operation_type: 'rename',
      source_path: sourcePath,
      target_path: targetPath,
      create_backup: options?.create_backup ?? true,
      validate_database_consistency: options?.validate_database_consistency ?? true,
    });
  }, [createOperation]);

  const deleteFile = useCallback(async (sourcePath: string, options?: {
    create_backup?: boolean;
    validate_database_consistency?: boolean;
  }): Promise<FileOperation> => {
    return createOperation({
      operation_type: 'delete',
      source_path: sourcePath,
      create_backup: options?.create_backup ?? true,
      validate_database_consistency: options?.validate_database_consistency ?? true,
    });
  }, [createOperation]);

  const moveFile = useCallback(async (sourcePath: string, targetPath: string, options?: {
    create_backup?: boolean;
    validate_database_consistency?: boolean;
  }): Promise<FileOperation> => {
    return createOperation({
      operation_type: 'move',
      source_path: sourcePath,
      target_path: targetPath,
      create_backup: options?.create_backup ?? true,
      validate_database_consistency: options?.validate_database_consistency ?? true,
    });
  }, [createOperation]);

  // Auto-refresh operations every 30 seconds
  useEffect(() => {
    const interval = setInterval(() => {
      // Only refresh if we have operations and no active loading
      if (operations.length > 0 && !loading && !validating && !executing) {
        refreshOperations().catch(() => {
          // Silently fail for auto-refresh
        });
      }
    }, 30000);

    return () => clearInterval(interval);
  }, [operations.length, loading, validating, executing, refreshOperations]);

  // Load initial operations on mount
  useEffect(() => {
    refreshOperations().catch(() => {
      // Silently fail for initial load
    });
  }, []);

  return {
    // State
    operations,
    activeOperation,
    loading,
    validating,
    executing,
    error,
    validation,
    
    // Actions
    createOperation,
    validateOperation,
    executeOperation,
    rollbackOperation,
    getOperation,
    listOperations,
    
    // Utility actions
    clearError,
    refreshOperations,
    cleanupOldOperations,
    
    // Convenience methods (not part of the interface but useful)
    renameFile,
    deleteFile,
    moveFile,
  } as UseFileOperationsReturn & {
    renameFile: typeof renameFile;
    deleteFile: typeof deleteFile;
    moveFile: typeof moveFile;
  };
};