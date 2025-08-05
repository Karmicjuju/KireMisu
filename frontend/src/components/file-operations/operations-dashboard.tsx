"use client";

/**
 * File Operations Dashboard Component
 * 
 * Provides a comprehensive view of file operations with:
 * - Real-time operation status
 * - Operation history
 * - Quick actions for common operations
 * - Cleanup and management tools
 */

import React, { useState, useEffect } from 'react';
import { 
  FileX, 
  Edit3, 
  FolderOpen, 
  CheckCircle, 
  XCircle, 
  Clock, 
  AlertTriangle,
  RotateCcw,
  Trash2,
  RefreshCw,
  Filter,
  Eye,
  MoreHorizontal
} from 'lucide-react';
import { useFileOperations } from '../../hooks/use-file-operations';

interface OperationsDashboardProps {
  className?: string;
}

const OperationsDashboard: React.FC<OperationsDashboardProps> = ({ className = '' }) => {
  const {
    operations,
    loading,
    error,
    clearError,
    refreshOperations,
    rollbackOperation,
    cleanupOldOperations,
    listOperations,
  } = useFileOperations();

  const [statusFilter, setStatusFilter] = useState<string>('');
  const [typeFilter, setTypeFilter] = useState<string>('');
  const [showFilters, setShowFilters] = useState(false);
  const [selectedOperation, setSelectedOperation] = useState<string | null>(null);

  // Filter operations based on current filters
  const filteredOperations = operations.filter(op => {
    if (statusFilter && op.status !== statusFilter) return false;
    if (typeFilter && op.operation_type !== typeFilter) return false;
    return true;
  });

  // Get operation icon
  const getOperationIcon = (type: string) => {
    switch (type) {
      case 'rename': return <Edit3 className="w-4 h-4" />;
      case 'delete': return <FileX className="w-4 h-4" />;
      case 'move': return <FolderOpen className="w-4 h-4" />;
      default: return <MoreHorizontal className="w-4 h-4" />;
    }
  };

  // Get status icon and color
  const getStatusDisplay = (status: string) => {
    switch (status) {
      case 'completed':
        return { icon: <CheckCircle className="w-4 h-4" />, color: 'text-green-600', bg: 'bg-green-100' };
      case 'failed':
        return { icon: <XCircle className="w-4 h-4" />, color: 'text-red-600', bg: 'bg-red-100' };
      case 'in_progress':
        return { icon: <Clock className="w-4 h-4 animate-pulse" />, color: 'text-blue-600', bg: 'bg-blue-100' };
      case 'validated':
        return { icon: <CheckCircle className="w-4 h-4" />, color: 'text-yellow-600', bg: 'bg-yellow-100' };
      case 'rolled_back':
        return { icon: <RotateCcw className="w-4 h-4" />, color: 'text-purple-600', bg: 'bg-purple-100' };
      default:
        return { icon: <Clock className="w-4 h-4" />, color: 'text-gray-600', bg: 'bg-gray-100' };
    }
  };

  // Handle rollback
  const handleRollback = async (operationId: string) => {
    if (confirm('Are you sure you want to rollback this operation?')) {
      try {
        await rollbackOperation(operationId);
      } catch (err) {
        console.error('Rollback failed:', err);
      }
    }
  };

  // Handle cleanup
  const handleCleanup = async () => {
    if (confirm('Are you sure you want to clean up old operations? This will remove completed operations older than 30 days.')) {
      try {
        const result = await cleanupOldOperations(30);
        alert(`Cleaned up ${result.cleaned_count} old operations.`);
      } catch (err) {
        console.error('Cleanup failed:', err);
      }
    }
  };

  // Apply filters
  const applyFilters = async () => {
    try {
      await listOperations({
        status_filter: statusFilter || undefined,
        operation_type_filter: typeFilter || undefined,
        limit: 50,
      });
    } catch (err) {
      console.error('Failed to apply filters:', err);
    }
  };

  // Clear filters
  const clearFilters = async () => {
    setStatusFilter('');
    setTypeFilter('');
    await refreshOperations();
  };

  useEffect(() => {
    if (statusFilter || typeFilter) {
      applyFilters();
    }
  }, [statusFilter, typeFilter]);

  return (
    <div className={`bg-white rounded-lg shadow-sm border border-gray-200 ${className}`}>
      {/* Header */}
      <div className="p-6 border-b border-gray-200">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-xl font-semibold text-gray-900">File Operations</h2>
            <p className="text-sm text-gray-500 mt-1">
              Manage and monitor safe file operations
            </p>
          </div>
          <div className="flex items-center space-x-2">
            <button
              onClick={() => setShowFilters(!showFilters)}
              className="p-2 text-gray-400 hover:text-gray-600 transition-colors"
              title="Toggle filters"
            >
              <Filter className="w-5 h-5" />
            </button>
            <button
              onClick={refreshOperations}
              disabled={loading}
              className="p-2 text-gray-400 hover:text-gray-600 transition-colors disabled:opacity-50"
              title="Refresh"
            >
              <RefreshCw className={`w-5 h-5 ${loading ? 'animate-spin' : ''}`} />
            </button>
            <button
              onClick={handleCleanup}
              className="p-2 text-gray-400 hover:text-gray-600 transition-colors"
              title="Cleanup old operations"
            >
              <Trash2 className="w-5 h-5" />
            </button>
          </div>
        </div>

        {/* Error Display */}
        {error && (
          <div className="mt-4 p-3 bg-red-100 border border-red-300 rounded-md flex items-center justify-between">
            <div className="flex items-center space-x-2">
              <XCircle className="w-5 h-5 text-red-600" />
              <span className="text-red-700">{error}</span>
            </div>
            <button
              onClick={clearError}
              className="text-red-600 hover:text-red-800 transition-colors"
            >
              <XCircle className="w-4 h-4" />
            </button>
          </div>
        )}

        {/* Filters */}
        {showFilters && (
          <div className="mt-4 p-4 bg-gray-50 rounded-md">
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Status
                </label>
                <select
                  value={statusFilter}
                  onChange={(e) => setStatusFilter(e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                >
                  <option value="">All Statuses</option>
                  <option value="pending">Pending</option>
                  <option value="validated">Validated</option>
                  <option value="in_progress">In Progress</option>
                  <option value="completed">Completed</option>
                  <option value="failed">Failed</option>
                  <option value="rolled_back">Rolled Back</option>
                </select>
              </div>
              
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Operation Type
                </label>
                <select
                  value={typeFilter}
                  onChange={(e) => setTypeFilter(e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                >
                  <option value="">All Types</option>
                  <option value="rename">Rename</option>
                  <option value="delete">Delete</option>
                  <option value="move">Move</option>
                </select>
              </div>
              
              <div className="flex items-end space-x-2">
                <button
                  onClick={clearFilters}
                  className="px-4 py-2 text-gray-600 border border-gray-300 rounded-md hover:bg-gray-50 transition-colors"
                >
                  Clear
                </button>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Operations List */}
      <div className="divide-y divide-gray-200">
        {filteredOperations.length === 0 ? (
          <div className="p-8 text-center">
            <FileX className="w-12 h-12 mx-auto text-gray-400 mb-4" />
            <h3 className="text-lg font-medium text-gray-900 mb-2">No Operations Found</h3>
            <p className="text-gray-500">
              {statusFilter || typeFilter 
                ? 'No operations match your current filters.' 
                : 'No file operations have been performed yet.'
              }
            </p>
          </div>
        ) : (
          filteredOperations.map((operation) => {
            const statusDisplay = getStatusDisplay(operation.status);
            const isExpanded = selectedOperation === operation.id;
            
            return (
              <div key={operation.id} className="p-4 hover:bg-gray-50 transition-colors">
                <div className="flex items-center justify-between">
                  <div className="flex items-center space-x-3 flex-1 min-w-0">
                    <div className="flex-shrink-0">
                      {getOperationIcon(operation.operation_type)}
                    </div>
                    
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center space-x-2 mb-1">
                        <h3 className="text-sm font-medium text-gray-900 capitalize">
                          {operation.operation_type}
                        </h3>
                        <span className={`inline-flex items-center px-2 py-1 rounded-full text-xs font-medium ${statusDisplay.bg} ${statusDisplay.color}`}>
                          {statusDisplay.icon}
                          <span className="ml-1 capitalize">{operation.status.replace('_', ' ')}</span>
                        </span>
                      </div>
                      
                      <p className="text-sm text-gray-600 truncate">
                        {operation.source_path}
                        {operation.target_path && (
                          <span className="text-gray-400"> → {operation.target_path}</span>
                        )}
                      </p>
                      
                      <div className="flex items-center space-x-4 mt-1 text-xs text-gray-500">
                        <span>Created: {new Date(operation.created_at).toLocaleString()}</span>
                        {operation.completed_at && (
                          <span>Completed: {new Date(operation.completed_at).toLocaleString()}</span>
                        )}
                      </div>
                    </div>
                  </div>
                  
                  <div className="flex items-center space-x-2">
                    {operation.status === 'completed' && operation.backup_path && (
                      <button
                        onClick={() => handleRollback(operation.id)}
                        className="p-2 text-gray-400 hover:text-purple-600 transition-colors"
                        title="Rollback operation"
                      >
                        <RotateCcw className="w-4 h-4" />
                      </button>
                    )}
                    
                    <button
                      onClick={() => setSelectedOperation(isExpanded ? null : operation.id)}
                      className="p-2 text-gray-400 hover:text-gray-600 transition-colors"
                      title="View details"
                    >
                      <Eye className="w-4 h-4" />
                    </button>
                  </div>
                </div>
                
                {/* Expanded Details */}
                {isExpanded && (
                  <div className="mt-4 pt-4 border-t border-gray-200">
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      <div>
                        <h4 className="text-sm font-medium text-gray-900 mb-2">Operation Details</h4>
                        <dl className="space-y-1 text-sm">
                          <div className="flex justify-between">
                            <dt className="text-gray-500">ID:</dt>
                            <dd className="text-gray-900 font-mono text-xs">{operation.id}</dd>
                          </div>
                          <div className="flex justify-between">
                            <dt className="text-gray-500">Type:</dt>
                            <dd className="text-gray-900 capitalize">{operation.operation_type}</dd>
                          </div>
                          <div className="flex justify-between">
                            <dt className="text-gray-500">Status:</dt>
                            <dd className="text-gray-900 capitalize">{operation.status.replace('_', ' ')}</dd>
                          </div>
                        </dl>
                      </div>
                      
                      <div>
                        <h4 className="text-sm font-medium text-gray-900 mb-2">Affected Records</h4>
                        <dl className="space-y-1 text-sm">
                          <div className="flex justify-between">
                            <dt className="text-gray-500">Series:</dt>
                            <dd className="text-gray-900">{operation.affected_series_ids.length}</dd>
                          </div>
                          <div className="flex justify-between">
                            <dt className="text-gray-500">Chapters:</dt>
                            <dd className="text-gray-900">{operation.affected_chapter_ids.length}</dd>
                          </div>
                          {operation.backup_path && (
                            <div className="flex justify-between">
                              <dt className="text-gray-500">Backup:</dt>
                              <dd className="text-gray-900 text-green-600">✓ Created</dd>
                            </div>
                          )}
                        </dl>
                      </div>
                    </div>
                    
                    {operation.error_message && (
                      <div className="mt-4 p-3 bg-red-50 border border-red-200 rounded-md">
                        <div className="flex items-center space-x-2">
                          <AlertTriangle className="w-4 h-4 text-red-600" />
                          <span className="text-sm font-medium text-red-800">Error</span>
                        </div>
                        <p className="text-sm text-red-700 mt-1">{operation.error_message}</p>
                      </div>
                    )}
                    
                    {operation.backup_path && (
                      <div className="mt-4 p-3 bg-blue-50 border border-blue-200 rounded-md">
                        <div className="flex items-center space-x-2">
                          <CheckCircle className="w-4 h-4 text-blue-600" />
                          <span className="text-sm font-medium text-blue-800">Backup Available</span>
                        </div>
                        <p className="text-sm text-blue-700 mt-1 font-mono">{operation.backup_path}</p>
                      </div>
                    )}
                  </div>
                )}
              </div>
            );
          })
        )}
      </div>
      
      {/* Footer with summary */}
      {filteredOperations.length > 0 && (
        <div className="px-6 py-3 bg-gray-50 border-t border-gray-200 text-sm text-gray-500">
          Showing {filteredOperations.length} operation{filteredOperations.length !== 1 ? 's' : ''}
          {(statusFilter || typeFilter) && (
            <span> (filtered from {operations.length} total)</span>
          )}
        </div>
      )}
    </div>
  );
};

export default OperationsDashboard;