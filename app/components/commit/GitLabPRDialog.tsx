import { useState, useEffect } from 'react';
import * as Dialog from '@radix-ui/react-dialog';
import { toast } from 'react-toastify';
import { workbenchStore, type RepositoryContext } from '~/lib/stores/workbench';
import { getLocalStorage } from '~/lib/persistence/localStorage';
import { logStore } from '~/lib/stores/logs';
import { useModifiedFiles } from '~/lib/hooks';

interface GitLabPullRequestDialogProps {
  isOpen: boolean;
  onClose: () => void;
}

/**
 * Validates repository context for GitLab operations
 */
function validateGitLabRepository(repo: RepositoryContext | null): void {
  if (!repo) {
    throw new Error('No repository is currently open');
  }

  if (!repo.name) {
    throw new Error('GitLab project name is required');
  }

  if (!repo.fullName) {
    throw new Error('Repository full name is required');
  }
}

export function GitLabPullRequestDialog({ isOpen, onClose }: GitLabPullRequestDialogProps) {
  const [mrTitle, setMRTitle] = useState('');
  const [mrDescription, setMRDescription] = useState('');
  const [sourceBranch, setSourceBranch] = useState('');
  const [targetBranch, setTargetBranch] = useState('main');
  const [isLoading, setIsLoading] = useState(false);
  const [showSuccessDialog, setShowSuccessDialog] = useState(false);
  const [createdMRUrl, setCreatedMRUrl] = useState('');
  const [isOnMainBranch, setIsOnMainBranch] = useState(false);
  const [currentBranchName, setCurrentBranchName] = useState('');

  const { files: modifiedFiles } = useModifiedFiles();
  const currentRepo = workbenchStore.getCurrentRepository();

  // Intelligently determine source and target branches based on current working branch
  useEffect(() => {
    if (isOpen && currentRepo) {
      const workingBranch = currentRepo.branch || 'main';
      setCurrentBranchName(workingBranch);

      // Check if we're on main/master branch
      const onMainBranch = workingBranch === 'main' || workingBranch === 'master';
      setIsOnMainBranch(onMainBranch);

      if (onMainBranch) {
        // On main branch: Create a NEW feature branch for the MR
        const timestamp = new Date().toISOString().replace(/[:.]/g, '-').split('T')[0];
        const newBranch = `feature/update-${timestamp}-${Date.now().toString().slice(-6)}`;
        setSourceBranch(newBranch);
        setTargetBranch(workingBranch); // MR back to main

        logStore.logProvider('MR: Creating new feature branch from main', {
          component: 'GitLabPRDialog',
          currentBranch: workingBranch,
          newBranch,
        });
      } else {
        // On feature branch: Use current branch as source
        setSourceBranch(workingBranch);
        setTargetBranch('main'); // MR to main

        logStore.logProvider('MR: Using current feature branch', {
          component: 'GitLabPRDialog',
          currentBranch: workingBranch,
          targetBranch: 'main',
        });
      }
    }
  }, [isOpen, currentRepo]);

  const handleClose = () => {
    setShowSuccessDialog(false);
    setCreatedMRUrl('');
    onClose();
  };

  const handleCreateMR = async () => {
    if (!mrTitle.trim()) {
      toast.error('Please enter a merge request title');
      return;
    }

    // Validate repository context
    try {
      validateGitLabRepository(currentRepo);
    } catch (error: any) {
      toast.error(error.message);
      return;
    }

    try {
      // Validate repository context first
      validateGitLabRepository(currentRepo);

      // TypeScript doesn't know validation passed, so we assert non-null
      if (!currentRepo) {
        throw new Error('Repository validation failed');
      }

      const connection = getLocalStorage('gitlab_connection');

      if (!connection?.token || !connection?.user) {
        toast.error('GitLab connection not found. Please authenticate first.');
        return;
      }

      setIsLoading(true);

      logStore.logProvider('Creating GitLab merge request', {
        component: 'GitLabPRDialog',
        sourceBranch,
        targetBranch,
        title: mrTitle,
      });

      // Step 1: Push changes to source branch
      toast.info('Pushing changes to branch...');

      const pushResponse = await workbenchStore.pushToRepository(
        'gitlab',
        currentRepo.name || 'project',
        `Prepare MR: ${mrTitle}`,
        connection.user.username || connection.user.name,
        connection.token,
        false,
        sourceBranch,
      );

      if (!pushResponse) {
        throw new Error('Failed to push changes to branch');
      }

      toast.info('Creating merge request...');

      // Step 2: Call the GitLab MR creation API
      const mrResponse = await fetch('/api/gitlab-create-mr', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          projectId: currentRepo.name || currentRepo.fullName,
          title: mrTitle,
          description: mrDescription,
          sourceBranch,
          targetBranch,
          token: connection.token,
        }),
      });

      if (!mrResponse.ok) {
        const errorData = (await mrResponse.json()) as { error?: string };
        throw new Error(errorData.error || 'Failed to create merge request');
      }

      const mrData = (await mrResponse.json()) as {
        success: boolean;
        mr: {
          iid: number;
          url: string;
          title: string;
          source_branch: string;
          target_branch: string;
          state: string;
          created_at: string;
        };
      };

      logStore.logProvider('Merge request created successfully', {
        component: 'GitLabPRDialog',
        mrIid: mrData.mr.iid,
        mrUrl: mrData.mr.url,
      });

      setCreatedMRUrl(mrData.mr.url);
      setShowSuccessDialog(true);
      toast.success('Merge request created successfully! 🎉');
    } catch (error: unknown) {
      const errorMessage = error instanceof Error ? error.message : 'Unknown error occurred';
      logStore.logError('Failed to create GitLab merge request', {
        component: 'GitLabPRDialog',
        error: errorMessage,
      });
      toast.error(`Failed to create merge request: ${errorMessage}`);
    } finally {
      setIsLoading(false);
    }
  };

  if (showSuccessDialog) {
    return (
      <Dialog.Root open={isOpen} onOpenChange={handleClose}>
        <Dialog.Portal>
          <Dialog.Overlay className="fixed inset-0 bg-black/50 backdrop-blur-sm z-50" />
          <Dialog.Content className="fixed top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2 bg-white dark:bg-gray-800 rounded-2xl shadow-2xl z-50 w-full max-w-md p-6">
            <Dialog.Title className="text-2xl font-bold text-transparent bg-clip-text bg-gradient-to-r from-orange-600 to-red-600 dark:from-orange-400 dark:to-red-400 mb-4">
              Success!
            </Dialog.Title>

            <div className="space-y-4">
              <div className="bg-gradient-to-br from-orange-50 to-red-50 dark:from-orange-900/20 dark:to-red-900/20 rounded-xl p-4 border-2 border-orange-200 dark:border-orange-700">
                <div className="flex items-start gap-3">
                  <span className="i-ph:git-merge text-orange-600 dark:text-orange-400 text-xl flex-shrink-0 mt-0.5" />
                  <div className="flex-1">
                    <p className="text-sm text-orange-800 dark:text-orange-200 font-medium mb-1">
                      Merge request created successfully
                    </p>
                    <p className="text-xs text-orange-700 dark:text-orange-300">
                      Your changes have been pushed to a new branch and an MR has been opened
                    </p>
                  </div>
                </div>
              </div>

              {createdMRUrl && (
                <a
                  href={createdMRUrl}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex items-center justify-center gap-2 w-full rounded-xl bg-gradient-to-r from-orange-600 to-red-600 hover:from-orange-700 hover:to-red-700 px-4 py-3 text-white font-semibold shadow-lg hover:shadow-xl transition-all group mb-3"
                >
                  <span className="i-ph:gitlab-logo-fill text-xl" />
                  View Merge Request on GitLab
                  <span className="i-ph:arrow-right text-lg group-hover:translate-x-1 transition-transform" />
                </a>
              )}

              <button
                onClick={handleClose}
                className="w-full rounded-xl border-2 border-gray-300 dark:border-gray-600 px-4 py-2.5 text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 font-medium transition-all"
              >
                Close
              </button>
            </div>
          </Dialog.Content>
        </Dialog.Portal>
      </Dialog.Root>
    );
  }

  return (
    <Dialog.Root open={isOpen} onOpenChange={handleClose}>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 bg-black/50 backdrop-blur-sm z-50" />
        <Dialog.Content className="fixed top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2 bg-white dark:bg-gray-800 rounded-2xl shadow-2xl z-50 w-full max-w-2xl max-h-[90vh] overflow-y-auto">
          <div className="sticky top-0 bg-gradient-to-r from-orange-600 to-red-600 dark:from-orange-700 dark:to-red-700 px-6 py-4 rounded-t-2xl">
            <Dialog.Title className="text-2xl font-bold text-white flex items-center gap-3">
              <span className="i-ph:gitlab-logo-fill text-3xl" />
              Create GitLab Merge Request
            </Dialog.Title>
            <p className="text-orange-100 text-sm mt-1">
              Create a merge request for {currentRepo?.name || 'your project'}
            </p>
          </div>

          <div className="p-6 space-y-6">
            {/* MR Title */}
            <div>
              <label className="block text-sm font-semibold text-gray-700 dark:text-gray-300 mb-2">
                Merge Request Title *
              </label>
              <input
                type="text"
                value={mrTitle}
                onChange={(e) => setMRTitle(e.target.value)}
                placeholder="feat: Add new feature"
                className="w-full px-4 py-3 rounded-xl border-2 border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 focus:border-orange-500 dark:focus:border-orange-400 focus:ring-2 focus:ring-orange-200 dark:focus:ring-orange-800 transition-all outline-none"
              />
            </div>

            {/* MR Description */}
            <div>
              <label className="block text-sm font-semibold text-gray-700 dark:text-gray-300 mb-2">Description</label>
              <textarea
                value={mrDescription}
                onChange={(e) => setMRDescription(e.target.value)}
                placeholder="Describe the changes in this merge request..."
                rows={4}
                className="w-full px-4 py-3 rounded-xl border-2 border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 focus:border-orange-500 dark:focus:border-orange-400 focus:ring-2 focus:ring-orange-200 dark:focus:ring-orange-800 transition-all outline-none resize-none"
              />
            </div>

            {/* Branch Configuration */}
            <div className="space-y-4">
              <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-300">Branch Configuration</h3>

              {/* Current Working Branch Info */}
              {currentBranchName && (
                <div className="bg-blue-50 dark:bg-blue-900/20 rounded-xl p-3 border-2 border-blue-200 dark:border-blue-800">
                  <div className="flex items-center gap-2 text-sm">
                    <span className="i-ph:info text-blue-600 dark:text-blue-400" />
                    <span className="text-blue-800 dark:text-blue-200 font-medium">
                      Current working branch:{' '}
                      <code className="font-mono bg-blue-100 dark:bg-blue-900 px-2 py-0.5 rounded">
                        {currentBranchName}
                      </code>
                    </span>
                  </div>
                </div>
              )}

              {/* Strategy Explanation */}
              {isOnMainBranch ? (
                <div className="bg-amber-50 dark:bg-amber-900/20 rounded-xl p-3 border-2 border-amber-200 dark:border-amber-800">
                  <div className="flex items-start gap-2">
                    <span className="i-ph:warning-circle text-amber-600 dark:text-amber-400 text-lg flex-shrink-0 mt-0.5" />
                    <div className="text-sm">
                      <p className="text-amber-800 dark:text-amber-200 font-medium mb-1">
                        You're on the{' '}
                        <code className="font-mono bg-amber-100 dark:bg-amber-900 px-1 rounded">
                          {currentBranchName}
                        </code>{' '}
                        branch
                      </p>
                      <p className="text-amber-700 dark:text-amber-300 text-xs">
                        A new feature branch will be created from your changes, then an MR will be opened back to{' '}
                        <code className="font-mono">{currentBranchName}</code>
                      </p>
                    </div>
                  </div>
                </div>
              ) : (
                <div className="bg-green-50 dark:bg-green-900/20 rounded-xl p-3 border-2 border-green-200 dark:border-green-800">
                  <div className="flex items-start gap-2">
                    <span className="i-ph:check-circle text-green-600 dark:text-green-400 text-lg flex-shrink-0 mt-0.5" />
                    <div className="text-sm">
                      <p className="text-green-800 dark:text-green-200 font-medium mb-1">
                        Working on feature branch{' '}
                        <code className="font-mono bg-green-100 dark:bg-green-900 px-1 rounded">
                          {currentBranchName}
                        </code>
                      </p>
                      <p className="text-green-700 dark:text-green-300 text-xs">
                        Your changes will be pushed to this branch, then an MR will be created to merge into{' '}
                        <code className="font-mono">{targetBranch}</code>
                      </p>
                    </div>
                  </div>
                </div>
              )}

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-semibold text-gray-700 dark:text-gray-300 mb-2">
                    Source Branch {isOnMainBranch && '(New)'}
                  </label>
                  <input
                    type="text"
                    value={sourceBranch}
                    onChange={(e) => setSourceBranch(e.target.value)}
                    className="w-full px-4 py-3 rounded-xl border-2 border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 focus:border-orange-500 dark:focus:border-orange-400 focus:ring-2 focus:ring-orange-200 dark:focus:ring-orange-800 transition-all outline-none font-mono text-sm"
                  />
                  <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                    {isOnMainBranch ? 'New branch will be created' : 'Changes will be pushed here'}
                  </p>
                </div>

                <div>
                  <label className="block text-sm font-semibold text-gray-700 dark:text-gray-300 mb-2">
                    Target Branch
                  </label>
                  <input
                    type="text"
                    value={targetBranch}
                    onChange={(e) => setTargetBranch(e.target.value)}
                    className="w-full px-4 py-3 rounded-xl border-2 border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 focus:border-orange-500 dark:focus:border-orange-400 focus:ring-2 focus:ring-orange-200 dark:focus:ring-orange-800 transition-all outline-none font-mono text-sm"
                  />
                  <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">MR will merge into this branch</p>
                </div>
              </div>
            </div>

            {/* Modified Files Preview */}
            {Object.keys(modifiedFiles).length > 0 && (
              <div>
                <label className="block text-sm font-semibold text-gray-700 dark:text-gray-300 mb-2">
                  Modified Files ({Object.keys(modifiedFiles).length})
                </label>
                <div className="bg-gray-50 dark:bg-gray-700/50 rounded-xl p-4 max-h-32 overflow-y-auto border-2 border-gray-200 dark:border-gray-600">
                  {Object.keys(modifiedFiles).map((file) => (
                    <div key={file} className="flex items-center gap-2 text-sm text-gray-700 dark:text-gray-300 py-1">
                      <span className="i-ph:file text-orange-600 dark:text-orange-400" />
                      {file}
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Action Buttons */}
            <div className="flex gap-3 pt-4">
              <button
                onClick={handleClose}
                disabled={isLoading}
                className="flex-1 px-6 py-3 rounded-xl border-2 border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 font-semibold transition-all disabled:opacity-50 disabled:cursor-not-allowed"
              >
                Cancel
              </button>
              <button
                onClick={handleCreateMR}
                disabled={isLoading || !mrTitle.trim()}
                className="flex-1 px-6 py-3 rounded-xl bg-gradient-to-r from-orange-600 to-red-600 hover:from-orange-700 hover:to-red-700 text-white font-semibold shadow-lg hover:shadow-xl transition-all disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
              >
                {isLoading ? (
                  <>
                    <span className="i-ph:circle-notch animate-spin text-lg" />
                    Creating MR...
                  </>
                ) : (
                  <>
                    <span className="i-ph:git-merge text-lg" />
                    Create Merge Request
                  </>
                )}
              </button>
            </div>
          </div>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}
