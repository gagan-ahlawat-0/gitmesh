import React, { createContext, useContext, useEffect, useState } from 'react';
import { useStore } from '@nanostores/react';
import { workbenchStore } from '~/lib/stores/workbench';

interface FileModificationContextType {
  hasModifiedFiles: boolean;
  modifiedFilesCount: number;
  modifiedFiles: Set<string>;
  lastModificationTime: Date | null;
}

const FileModificationContext = createContext<FileModificationContextType | null>(null);

export const FileModificationProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [lastModificationTime, setLastModificationTime] = useState<Date | null>(null);

  // Subscribe to file changes for reactivity
  useStore(workbenchStore.files);

  // Get modified files using the working system
  const modifiedFilesObj = workbenchStore.getModifiedFiles();
  const modifiedFilesSet = new Set(modifiedFilesObj ? Object.keys(modifiedFilesObj) : []);
  const modifiedFilesCount = modifiedFilesSet.size;

  // Update last modification time when files change
  useEffect(() => {
    if (modifiedFilesCount > 0) {
      setLastModificationTime(new Date());
    }
  }, [modifiedFilesCount]);

  const contextValue: FileModificationContextType = {
    hasModifiedFiles: modifiedFilesCount > 0,
    modifiedFilesCount,
    modifiedFiles: modifiedFilesSet,
    lastModificationTime,
  };

  return <FileModificationContext.Provider value={contextValue}>{children}</FileModificationContext.Provider>;
};

export const useFileModificationContext = () => {
  const context = useContext(FileModificationContext);

  if (!context) {
    throw new Error('useFileModificationContext must be used within a FileModificationProvider');
  }

  return context;
};

// Global function to get file modification status for AI prompts
export const getFileModificationStatus = (): string => {
  const modifiedFilesObj = workbenchStore.getModifiedFiles();
  const modifiedFiles = modifiedFilesObj ? Object.keys(modifiedFilesObj) : [];

  if (modifiedFiles.length === 0) {
    return 'No files have been modified.';
  }

  const filesList = modifiedFiles.join(', ');

  return `Files have been modified (${modifiedFiles.length} files): ${filesList}`;
};
