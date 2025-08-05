"use client";

/**
 * Safe File Operation Dialog Component
 * 
 * Provides a comprehensive UI for safe file operations with:
 * - Pre-operation validation
 * - Risk assessment display
 * - User confirmation dialogs
 * - Progress tracking
 * - Rollback capabilities
 */

import React, { useState, useEffect } from 'react';
import { AlertTriangle, CheckCircle, XCircle, RotateCcw, Loader2, FileX, Edit3, FolderOpen } from 'lucide-react';

// Types matching the backend schemas
interface FileOperationRequest {
  operation_type: 'rename' | 'delete' | 'move';
  source_path: string;
  target_path?: string;
  force?: boolean;
  create_backup?: boolean;
  skip_validation?: boolean;
  validate_database_consistency?: boolean;
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

interface FileOperationResponse {
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
}

interface FileOperationDialogProps {
  isOpen: boolean;
  onClose: () => void;
  operationType: 'rename' | 'delete' | 'move';
  sourcePath: string;
  initialTargetPath?: string;
  onSuccess?: (operation: FileOperationResponse) => void;
  onError?: (error: string) => void;
}

const FileOperationDialog: React.FC<FileOperationDialogProps> = ({
  isOpen,
  onClose,
  operationType,
  sourcePath,
  initialTargetPath = '',
  onSuccess,
  onError,
}) => {
  const [step, setStep] = useState<'configure' | 'validate' | 'confirm' | 'execute' | 'complete'>('configure');
  const [targetPath, setTargetPath] = useState(initialTargetPath);
  const [createBackup, setCreateBackup] = useState(true);
  const [validateConsistency, setValidateConsistency] = useState(true);
  
  const [operation, setOperation] = useState<FileOperationResponse | null>(null);
  const [validation, setValidation] = useState<ValidationResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Reset state when dialog opens/closes
  useEffect(() => {
    if (isOpen) {
      setStep('configure');
      setTargetPath(initialTargetPath);
      setCreateBackup(true);
      setValidateConsistency(true);
      setOperation(null);
      setValidation(null);
      setLoading(false);
      setError(null);
    }
  }, [isOpen, initialTargetPath]);

  const handleCreateOperation = async () => {
    setLoading(true);
    setError(null);

    try {
      const request: FileOperationRequest = {
        operation_type: operationType,
        source_path: sourcePath,
        target_path: operationType !== 'delete' ? targetPath : undefined,
        create_backup: createBackup,
        validate_database_consistency: validateConsistency,
      };

      const response = await fetch('/api/file-operations/', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(request),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Failed to create operation');
      }

      const operationData = await response.json();
      setOperation(operationData);
      setStep('validate');

      // Automatically start validation
      await handleValidateOperation(operationData.id);
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Unknown error occurred';
      setError(errorMessage);
      onError?.(errorMessage);
    } finally {
      setLoading(false);
    }
  };

  const handleValidateOperation = async (operationId: string) => {
    setLoading(true);
    setError(null);

    try {
      const response = await fetch(`/api/file-operations/${operationId}/validate`, {
        method: 'POST',
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Validation failed');
      }

      const validationData = await response.json();
      setValidation(validationData);
      
      if (validationData.is_valid) {
        setStep('confirm');
      } else {
        setError('Operation validation failed. Please check the errors and try again.');
      }
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Validation error occurred';
      setError(errorMessage);
      onError?.(errorMessage);
    } finally {
      setLoading(false);
    }
  };

  const handleExecuteOperation = async () => {
    if (!operation) return;

    setLoading(true);
    setError(null);
    setStep('execute');

    try {
      const response = await fetch(`/api/file-operations/${operation.id}/execute`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          operation_id: operation.id,
          confirmed: true,
          confirmation_message: 'User confirmed via UI',
        }),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Execution failed');
      }

      const executionData = await response.json();
      setOperation(executionData);
      setStep('complete');
      onSuccess?.(executionData);
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Execution error occurred';
      setError(errorMessage);
      onError?.(errorMessage);
    } finally {
      setLoading(false);
    }
  };

  const handleRollback = async () => {
    if (!operation) return;

    setLoading(true);
    setError(null);

    try {
      const response = await fetch(`/api/file-operations/${operation.id}/rollback`, {
        method: 'POST',
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Rollback failed');
      }

      const rollbackData = await response.json();
      setOperation(rollbackData);
      onSuccess?.(rollbackData);
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Rollback error occurred';
      setError(errorMessage);
      onError?.(errorMessage);
    } finally {
      setLoading(false);
    }
  };

  const getRiskColor = (riskLevel: string) => {
    switch (riskLevel) {
      case 'low': return 'text-green-600 bg-green-100';
      case 'medium': return 'text-yellow-600 bg-yellow-100';
      case 'high': return 'text-red-600 bg-red-100';
      default: return 'text-gray-600 bg-gray-100';
    }
  };

  const getOperationIcon = () => {
    switch (operationType) {
      case 'rename': return <Edit3 className="w-5 h-5" />;
      case 'delete': return <FileX className="w-5 h-5" />;
      case 'move': return <FolderOpen className="w-5 h-5" />;
    }
  };

  const getOperationTitle = () => {
    switch (operationType) {
      case 'rename': return 'Rename File/Directory';
      case 'delete': return 'Delete File/Directory';
      case 'move': return 'Move File/Directory';
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-xl max-w-2xl w-full mx-4 max-h-[90vh] overflow-y-auto">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b">
          <div className="flex items-center space-x-2">
            {getOperationIcon()}
            <h2 className="text-xl font-semibold">{getOperationTitle()}</h2>
          </div>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600 transition-colors"
          >
            <XCircle className="w-6 h-6" />
          </button>
        </div>

        {/* Content */}
        <div className="p-6">
          {/* Error Display */}
          {error && (
            <div className="mb-4 p-3 bg-red-100 border border-red-300 rounded-md flex items-center space-x-2">
              <XCircle className="w-5 h-5 text-red-600" />
              <span className="text-red-700">{error}</span>
            </div>
          )}

          {/* Step 1: Configure */}
          {step === 'configure' && (
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Source Path
                </label>
                <input
                  type="text"
                  value={sourcePath}
                  disabled
                  className="w-full px-3 py-2 bg-gray-100 border border-gray-300 rounded-md text-gray-600"
                />
              </div>

              {(operationType === 'rename' || operationType === 'move') && (
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Target Path
                  </label>
                  <input
                    type="text"
                    value={targetPath}
                    onChange={(e) => setTargetPath(e.target.value)}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                    placeholder="Enter the new path..."
                    required
                  />
                </div>
              )}

              <div className="space-y-3">
                <div className="flex items-center space-x-2">
                  <input
                    type="checkbox"
                    id="create-backup"
                    checked={createBackup}
                    onChange={(e) => setCreateBackup(e.target.checked)}
                    className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                  />
                  <label htmlFor="create-backup" className="text-sm text-gray-700">
                    Create backup before operation (recommended)
                  </label>
                </div>

                <div className="flex items-center space-x-2">
                  <input
                    type="checkbox"
                    id="validate-consistency"
                    checked={validateConsistency}
                    onChange={(e) => setValidateConsistency(e.target.checked)}
                    className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                  />
                  <label htmlFor="validate-consistency" className="text-sm text-gray-700">
                    Validate database consistency (recommended)
                  </label>
                </div>
              </div>
            </div>
          )}

          {/* Step 2: Validation Results */}
          {step === 'validate' && (
            <div className="space-y-4">
              <div className="text-center">
                <Loader2 className="w-8 h-8 animate-spin mx-auto text-blue-600" />
                <p className="mt-2 text-gray-600">Validating operation...</p>
              </div>
            </div>
          )}

          {/* Step 3: Confirmation */}
          {step === 'confirm' && validation && (
            <div className="space-y-4">
              <div className="bg-gray-50 p-4 rounded-md">
                <h3 className="font-medium text-gray-900 mb-2">Operation Summary</h3>
                <div className="text-sm text-gray-600 space-y-1">
                  <p><strong>Action:</strong> {operationType} {sourcePath}</p>
                  {targetPath && <p><strong>Target:</strong> {targetPath}</p>}
                  <p><strong>Backup:</strong> {createBackup ? 'Yes' : 'No'}</p>
                </div>
              </div>

              {/* Risk Assessment */}
              <div className="space-y-2">
                <div className="flex items-center space-x-2">
                  <span className="text-sm font-medium">Risk Level:</span>
                  <span className={`px-2 py-1 rounded-full text-sm font-medium ${getRiskColor(validation.risk_level)}`}>
                    {validation.risk_level.toUpperCase()}
                  </span>
                </div>

                {validation.affected_series_count > 0 && (
                  <p className="text-sm text-gray-600">
                    <strong>Affected Series:</strong> {validation.affected_series_count}
                  </p>
                )}

                {validation.affected_chapter_count > 0 && (
                  <p className="text-sm text-gray-600">
                    <strong>Affected Chapters:</strong> {validation.affected_chapter_count}
                  </p>
                )}

                {validation.estimated_disk_usage_mb && (
                  <p className="text-sm text-gray-600">
                    <strong>Backup Size:</strong> ~{validation.estimated_disk_usage_mb.toFixed(1)} MB
                  </p>
                )}
              </div>

              {/* Warnings */}
              {validation.warnings.length > 0 && (
                <div className="bg-yellow-50 border border-yellow-200 rounded-md p-3">
                  <div className="flex items-center space-x-2 mb-2">
                    <AlertTriangle className="w-5 h-5 text-yellow-600" />
                    <h4 className="font-medium text-yellow-800">Warnings</h4>
                  </div>
                  <ul className="list-disc list-inside text-sm text-yellow-700 space-y-1">
                    {validation.warnings.map((warning, index) => (
                      <li key={index}>{warning}</li>
                    ))}
                  </ul>
                </div>
              )}

              {/* Conflicts */}
              {validation.conflicts.length > 0 && (
                <div className="bg-orange-50 border border-orange-200 rounded-md p-3">
                  <div className="flex items-center space-x-2 mb-2">
                    <AlertTriangle className="w-5 h-5 text-orange-600" />
                    <h4 className="font-medium text-orange-800">Conflicts Detected</h4>
                  </div>
                  <ul className="list-disc list-inside text-sm text-orange-700 space-y-1">
                    {validation.conflicts.map((conflict, index) => (
                      <li key={index}>
                        <strong>{conflict.type}:</strong> {conflict.message}
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {/* Errors */}
              {validation.errors.length > 0 && (
                <div className="bg-red-50 border border-red-200 rounded-md p-3">
                  <div className="flex items-center space-x-2 mb-2">
                    <XCircle className="w-5 h-5 text-red-600" />
                    <h4 className="font-medium text-red-800">Errors</h4>
                  </div>
                  <ul className="list-disc list-inside text-sm text-red-700 space-y-1">
                    {validation.errors.map((error, index) => (
                      <li key={index}>{error}</li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          )}

          {/* Step 4: Execution */}
          {step === 'execute' && (
            <div className="space-y-4">
              <div className="text-center">
                <Loader2 className="w-8 h-8 animate-spin mx-auto text-blue-600" />
                <p className="mt-2 text-gray-600">Executing operation...</p>
                <p className="text-sm text-gray-500">Please do not close this dialog.</p>
              </div>
            </div>
          )}

          {/* Step 5: Complete */}
          {step === 'complete' && operation && (
            <div className="space-y-4">
              <div className="text-center">
                <CheckCircle className="w-12 h-12 mx-auto text-green-600" />
                <h3 className="mt-2 text-lg font-medium text-gray-900">
                  Operation {operation.status === 'completed' ? 'Completed' : 'Failed'}
                </h3>
                {operation.completed_at && (
                  <p className="text-sm text-gray-500">
                    Completed at {new Date(operation.completed_at).toLocaleString()}
                  </p>
                )}
              </div>

              {operation.backup_path && (
                <div className="bg-blue-50 border border-blue-200 rounded-md p-3">
                  <p className="text-sm text-blue-700">
                    <strong>Backup created:</strong> {operation.backup_path}
                  </p>
                </div>
              )}

              {operation.status === 'completed' && operation.backup_path && (
                <div className="bg-gray-50 p-3 rounded-md">
                  <p className="text-sm text-gray-600 mb-2">
                    If you need to undo this operation, you can rollback using the backup.
                  </p>
                  <button
                    onClick={handleRollback}
                    disabled={loading}
                    className="flex items-center space-x-2 px-3 py-2 bg-gray-600 text-white rounded-md hover:bg-gray-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                  >
                    <RotateCcw className="w-4 h-4" />
                    <span>Rollback Operation</span>
                  </button>
                </div>
              )}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="flex justify-end space-x-3 p-6 border-t bg-gray-50">
          {step === 'configure' && (
            <>
              <button
                onClick={onClose}
                className="px-4 py-2 text-gray-600 border border-gray-300 rounded-md hover:bg-gray-50 transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={handleCreateOperation}
                disabled={loading || (operationType !== 'delete' && !targetPath.trim())}
                className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors flex items-center space-x-2"
              >
                {loading && <Loader2 className="w-4 h-4 animate-spin" />}
                <span>Continue</span>
              </button>
            </>
          )}

          {step === 'confirm' && validation?.is_valid && (
            <>
              <button
                onClick={onClose}
                className="px-4 py-2 text-gray-600 border border-gray-300 rounded-md hover:bg-gray-50 transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={handleExecuteOperation}
                disabled={loading}
                className={`px-4 py-2 rounded-md transition-colors flex items-center space-x-2 ${
                  validation.risk_level === 'high'
                    ? 'bg-red-600 hover:bg-red-700 text-white'
                    : validation.risk_level === 'medium'
                    ? 'bg-yellow-600 hover:bg-yellow-700 text-white'
                    : 'bg-green-600 hover:bg-green-700 text-white'
                } disabled:opacity-50 disabled:cursor-not-allowed`}
              >
                {loading && <Loader2 className="w-4 h-4 animate-spin" />}
                <span>
                  {validation.risk_level === 'high' ? 'Execute (High Risk)' : 
                   validation.risk_level === 'medium' ? 'Execute (Medium Risk)' : 
                   'Execute'}
                </span>
              </button>
            </>
          )}

          {step === 'complete' && (
            <button
              onClick={onClose}
              className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 transition-colors"
            >
              Close
            </button>
          )}
        </div>
      </div>
    </div>
  );
};

export default FileOperationDialog;