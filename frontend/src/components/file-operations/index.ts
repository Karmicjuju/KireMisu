/**
 * File Operations Components
 * 
 * Safe file operation components with comprehensive validation,
 * confirmation dialogs, and operation management.
 */

export { default as FileOperationDialog } from './file-operation-dialog';
export { default as OperationsDashboard } from './operations-dashboard';

// Re-export the hook for convenience
export { useFileOperations } from '../../hooks/use-file-operations';