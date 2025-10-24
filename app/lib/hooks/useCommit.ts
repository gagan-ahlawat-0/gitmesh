import { useCallback } from 'react';
import { useStore } from '@nanostores/react';
import { commitDialogOpen, commitProvider, resetCommitState } from '~/lib/stores/commit';
import { workbenchStore } from '~/lib/stores/workbench';
import { toast } from 'react-toastify';
import { useModifiedFiles } from '~/lib/hooks';

export const useCommit = () => {
  const commitDialogIsOpen = useStore(commitDialogOpen);
  const provider = useStore(commitProvider);
  const { files: modifiedFilesObj } = useModifiedFiles();

  const handleCommitToGitHub = useCallback(() => {
    commitProvider.set('github');
    commitDialogOpen.set(true);
  }, []);

  const handleCommitToGitLab = useCallback(() => {
    commitProvider.set('gitlab');
    commitDialogOpen.set(true);
  }, []);

  const executeCommit = useCallback(
    async (
      provider: 'github' | 'gitlab',
      repoName: string,
      commitMessage: string,
      username: string,
      token: string,
      isPrivate: boolean = false,
      branchName: string = 'main',
    ) => {
      try {
        if (Object.keys(modifiedFilesObj).length === 0) {
          toast.info('No files to commit');
          return null;
        }

        // Get modified files content (already available in modifiedFilesObj)
        const files: Record<string, string> = {};

        for (const [filePath, file] of Object.entries(modifiedFilesObj)) {
          if (file?.type === 'file' && file.content !== undefined) {
            files[filePath] = file.content;
          }
        }

        // Use existing pushToRepository method
        const repoUrl = await workbenchStore.pushToRepository(
          provider,
          repoName,
          commitMessage,
          username,
          token,
          isPrivate,
          branchName,
        );

        // Clear modified files after successful commit
        workbenchStore.resetAllFileModifications();

        return repoUrl;
      } catch (error) {
        console.error('Error executing commit:', error);
        throw error;
      }
    },
    [],
  );

  const closeCommitDialog = useCallback(() => {
    resetCommitState();
  }, []);

  return {
    handleCommitToGitHub,
    handleCommitToGitLab,
    executeCommit,
    closeCommitDialog,
    commitDialogIsOpen,
    provider,
  };
};
