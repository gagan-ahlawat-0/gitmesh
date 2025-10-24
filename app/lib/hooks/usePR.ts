import { useCallback } from 'react';
import { useStore } from '@nanostores/react';
import { prDialogOpen, prProvider, resetPRState } from '~/lib/stores/pr';

export const usePR = () => {
  const prDialogIsOpen = useStore(prDialogOpen);
  const provider = useStore(prProvider);

  const handleCreateGitHubPR = useCallback(() => {
    prProvider.set('github');
    prDialogOpen.set(true);
  }, []);

  const handleCreateGitLabPR = useCallback(() => {
    prProvider.set('gitlab');
    prDialogOpen.set(true);
  }, []);

  const closePRDialog = useCallback(() => {
    resetPRState();
  }, []);

  return {
    handleCreateGitHubPR,
    handleCreateGitLabPR,
    closePRDialog,
    prDialogIsOpen,
    provider,
  };
};
