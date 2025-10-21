import { atom } from 'nanostores';

// Commit dialog state
export const commitDialogOpen = atom(false);

// Commit provider (github/gitlab)
export const commitProvider = atom<'github' | 'gitlab' | null>(null);

// Commit message
export const commitMessage = atom('');

// Selected repository/project
export const selectedRepository = atom<string | null>(null);

// Selected branch
export const selectedBranch = atom<string>('main');

// Loading state during commit operations
export const isCommitting = atom(false);

// Chat ID for logging
export const chatId = atom<string | null>(null);

// Reset all commit state
export const resetCommitState = () => {
  commitDialogOpen.set(false);
  commitProvider.set(null);
  commitMessage.set('');
  selectedRepository.set(null);
  selectedBranch.set('main');
  isCommitting.set(false);
  chatId.set(null);
};
