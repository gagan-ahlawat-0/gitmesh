import { useMemo } from 'react';
import { useStore } from '@nanostores/react';
import { workbenchStore } from '~/lib/stores/workbench';

/**
 * Centralized hook for accessing modified files information
 * Provides reactive updates when files change
 * Optimized to prevent multiple calls to getModifiedFiles()
 */
export const useModifiedFiles = () => {
  // Subscribe to file changes for reactivity
  useStore(workbenchStore.files);

  // Get modified files once per render
  const modifiedFilesObj = workbenchStore.getModifiedFiles();

  return useMemo(() => {
    const filePaths = modifiedFilesObj ? Object.keys(modifiedFilesObj) : [];

    return {
      // Original object with file contents
      files: modifiedFilesObj || {},
      // Count of modified files
      count: filePaths.length,
      // Boolean check for convenience
      hasFiles: filePaths.length > 0,
      // Array of file paths
      filePaths,
      // Set of file paths (for components that need Set)
      filePathsSet: new Set(filePaths),
    };
  }, [modifiedFilesObj]);
};
