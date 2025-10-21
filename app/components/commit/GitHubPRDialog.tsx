import { useState, useEffect } from 'react';
import * as Dialog from '@radix-ui/react-dialog';
import { toast } from 'react-toastify';
import { workbenchStore, type RepositoryContext } from '~/lib/stores/workbench';
import { getLocalStorage } from '~/lib/persistence/localStorage';
import { logStore } from '~/lib/stores/logs';
import { useModifiedFiles } from '~/lib/hooks';

interface GitHubPullRequestDialogProps {
  isOpen: boolean;
  onClose: () => void;
}

/**
 * Validates repository context for GitHub operations
 */
function validateGitHubRepository(repo: RepositoryContext | null): void {
  if (!repo) {
    throw new Error('No repository is currently open');
  }

  if (!repo.owner) {
    throw new Error('GitHub repository owner is required');
  }

  if (!repo.name) {
    throw new Error('Repository name is required');
  }

  if (!repo.fullName) {
    throw new Error('Repository full name is required');
  }
}

export function GitHubPullRequestDialog({ isOpen, onClose }: GitHubPullRequestDialogProps) {
  const [prTitle, setPRTitle] = useState('');
  const [prDescription, setPRDescription] = useState('');
  const [sourceBranch, setSourceBranch] = useState('');
  const [targetBranch, setTargetBranch] = useState('main');
  const [isLoading, setIsLoading] = useState(false);
  const [showSuccessDialog, setShowSuccessDialog] = useState(false);
  const [createdPRUrl, setCreatedPRUrl] = useState('');
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
        // On main branch: Create a NEW feature branch for the PR
        const timestamp = new Date().toISOString().replace(/[:.]/g, '-').split('T')[0];
        const newBranch = `feature/update-${timestamp}-${Date.now().toString().slice(-6)}`;
        setSourceBranch(newBranch);
        setTargetBranch(workingBranch); // PR back to main

        logStore.logProvider('PR: Creating new feature branch from main', {
          component: 'GitHubPRDialog',
          currentBranch: workingBranch,
          newBranch,
        });
      } else {
        // On feature branch: Use current branch as source
        setSourceBranch(workingBranch);
        setTargetBranch('main'); // PR to main

        logStore.logProvider('PR: Using current feature branch', {
          component: 'GitHubPRDialog',
          currentBranch: workingBranch,
          targetBranch: 'main',
        });
      }
    }
  }, [isOpen, currentRepo]);

  // Auto-generate PR title from modified files
  useEffect(() => {
    if (isOpen && !prTitle && Object.keys(modifiedFiles).length > 0) {
      const fileCount = Object.keys(modifiedFiles).length;
      setPRTitle(`Update ${fileCount} file${fileCount > 1 ? 's' : ''}`);
    }
  }, [isOpen, modifiedFiles]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);

    try {
      // Validate repository context first
      validateGitHubRepository(currentRepo);

      // TypeScript doesn't know validation passed, so we assert non-null
      if (!currentRepo) {
        throw new Error('Repository validation failed');
      }

      const connection = getLocalStorage('github_connection');

      if (!connection?.token || !connection?.user) {
        toast.error('GitHub connection not found. Please connect your account first.');
        return;
      }

      // Step 1: Push changes to a new branch
      toast.info('Pushing changes to branch...');

      const pushResponse = await workbenchStore.pushToRepository(
        'github',
        currentRepo.name || 'repository',
        `Prepare PR: ${prTitle}`,
        connection.user.login,
        connection.token,
        false,
        sourceBranch,
      );

      if (!pushResponse) {
        throw new Error('Failed to push changes to branch');
      }

      toast.info('Creating pull request...');

      /*
       * Step 2: Create pull request
       * Note: For same repo, head should just be the branch name
       * For cross-repo (fork), it should be 'username:branch'
       */
      const headBranch =
        currentRepo.owner === connection.user.login ? sourceBranch : `${connection.user.login}:${sourceBranch}`;

      const prResponse = await fetch('/api/github-create-pr', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          owner: currentRepo.owner,
          repo: currentRepo.name,
          title: prTitle,
          body: prDescription,
          head: headBranch,
          base: targetBranch,
          token: connection.token,
        }),
      });

      if (!prResponse.ok) {
        const errorData = (await prResponse.json()) as { error?: string };
        throw new Error(errorData.error || 'Failed to create pull request');
      }

      const prData = (await prResponse.json()) as {
        success: boolean;
        pr: {
          number: number;
          url: string;
          title: string;
          head: string;
          base: string;
          state: string;
          created_at: string;
        };
      };

      if (!prData.success) {
        throw new Error('Failed to create pull request');
      }

      logStore.logProvider('Pull request created successfully', {
        component: 'GitHubPRDialog',
        prNumber: prData.pr.number,
        prUrl: prData.pr.url,
        prHead: prData.pr.head,
        prBase: prData.pr.base,
      });

      setCreatedPRUrl(prData.pr.url);
      setShowSuccessDialog(true);
      toast.success('Pull request created successfully!');

      // Reset form
      setPRTitle('');
      setPRDescription('');
      setSourceBranch('');
      setTargetBranch('main');
    } catch (error: any) {
      console.error('Error creating pull request:', error);
      toast.error(error.message || 'Failed to create pull request');
      logStore.logError('Failed to create pull request', { error: error.message });
    } finally {
      setIsLoading(false);
    }
  };

  const handleClose = () => {
    setShowSuccessDialog(false);
    onClose();
  };

  if (showSuccessDialog) {
    return (
      <Dialog.Root open={showSuccessDialog} onOpenChange={setShowSuccessDialog}>
        <Dialog.Portal>
          <Dialog.Overlay className="fixed inset-0 bg-black/60 backdrop-blur-sm z-[9999] animate-in fade-in duration-200" />
          <Dialog.Content className="fixed left-1/2 top-1/2 w-full max-w-md -translate-x-1/2 -translate-y-1/2 rounded-2xl bg-white dark:bg-gray-800 shadow-2xl z-[10000] overflow-hidden animate-in zoom-in-95 fade-in duration-200">
            {/* Success Header */}
            <div className="bg-gradient-to-r from-purple-500 to-blue-500 px-6 py-5 text-center">
              <div className="flex justify-center mb-3">
                <div className="w-16 h-16 rounded-full bg-white/20 backdrop-blur-sm flex items-center justify-center animate-bounce">
                  <span className="i-ph:check-circle-fill text-white text-4xl" />
                </div>
              </div>
              <Dialog.Title className="text-2xl font-bold text-white mb-1">Pull Request Created!</Dialog.Title>
              <p className="text-purple-50 text-sm">Your changes are ready for review</p>
            </div>

            {/* Success Content */}
            <div className="p-6">
              <div className="bg-gradient-to-br from-purple-50 to-blue-50 dark:from-purple-900/20 dark:to-blue-900/20 rounded-xl p-4 border-2 border-purple-200 dark:border-purple-800 mb-4">
                <div className="flex items-start gap-3">
                  <span className="i-ph:git-pull-request text-purple-600 dark:text-purple-400 text-xl flex-shrink-0 mt-0.5" />
                  <div className="flex-1">
                    <p className="text-sm text-purple-800 dark:text-purple-200 font-medium mb-1">
                      Pull request created successfully
                    </p>
                    <p className="text-xs text-purple-700 dark:text-purple-300">
                      Your changes have been pushed to a new branch and a PR has been opened
                    </p>
                  </div>
                </div>
              </div>

              {createdPRUrl && (
                <a
                  href={createdPRUrl}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex items-center justify-center gap-2 w-full rounded-xl bg-gradient-to-r from-purple-600 to-blue-600 hover:from-purple-700 hover:to-blue-700 px-4 py-3 text-white font-semibold shadow-lg hover:shadow-xl transition-all group mb-3"
                >
                  <span className="i-ph:github-logo-fill text-xl" />
                  View Pull Request on GitHub
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
    <Dialog.Root open={isOpen} onOpenChange={onClose}>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 bg-black/60 backdrop-blur-sm z-[9999] animate-in fade-in duration-200" />
        <Dialog.Content className="fixed left-1/2 top-1/2 w-full max-w-2xl -translate-x-1/2 -translate-y-1/2 rounded-2xl bg-white dark:bg-gray-800 shadow-2xl z-[10000] max-h-[90vh] overflow-hidden animate-in zoom-in-95 fade-in duration-200">
          {/* Header */}
          <div className="bg-gradient-to-r from-purple-600 to-blue-600 px-6 py-5">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-full bg-white/20 backdrop-blur-sm flex items-center justify-center">
                  <span className="i-ph:git-pull-request text-white text-2xl" />
                </div>
                <Dialog.Title className="text-2xl font-bold text-white">Create GitHub Pull Request</Dialog.Title>
              </div>
              <button
                type="button"
                onClick={onClose}
                className="text-white/80 hover:text-white hover:bg-white/20 rounded-lg p-2 transition-all"
              >
                <span className="i-ph:x text-xl" />
              </button>
            </div>
          </div>

          {/* Content */}
          <div className="p-6 overflow-y-auto max-h-[calc(90vh-80px)]">
            <form onSubmit={handleSubmit} className="space-y-6">
              {/* Current Repository Banner */}
              {currentRepo && (
                <div className="rounded-xl bg-gradient-to-r from-purple-50 to-blue-50 dark:from-purple-900/20 dark:to-blue-900/20 border-2 border-purple-200 dark:border-purple-800 p-5 shadow-sm">
                  <div className="flex items-start gap-4">
                    <div className="flex-shrink-0 w-10 h-10 rounded-full bg-purple-100 dark:bg-purple-900/40 flex items-center justify-center">
                      <div className="i-ph:git-branch-fill text-purple-600 dark:text-purple-400 text-2xl" />
                    </div>
                    <div className="flex-1 min-w-0">
                      <h4 className="text-base font-bold text-purple-900 dark:text-purple-100 mb-2">
                        Repository: {currentRepo.fullName}
                      </h4>
                      <p className="text-sm text-purple-700 dark:text-purple-300">
                        Creating a pull request for this repository
                      </p>
                    </div>
                  </div>
                </div>
              )}

              {/* Branch Configuration */}
              <div className="space-y-4">
                <h3 className="text-lg font-semibold text-gray-900 dark:text-white flex items-center gap-2">
                  <span className="i-ph:git-branch text-purple-500" />
                  Branch Configuration
                </h3>

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
                          A new feature branch will be created from your changes, then a PR will be opened back to{' '}
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
                          Your changes will be pushed to this branch, then a PR will be created to merge into{' '}
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
                      className="w-full rounded-xl border-2 border-gray-300 dark:border-gray-600 px-4 py-2 text-gray-900 dark:text-white bg-white dark:bg-gray-700 focus:border-purple-500 dark:focus:border-purple-400 focus:outline-none focus:ring-2 focus:ring-purple-500/20 dark:focus:ring-purple-400/20 transition-all font-mono text-sm"
                      placeholder="feature/my-changes"
                      required
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
                      className="w-full rounded-xl border-2 border-gray-300 dark:border-gray-600 px-4 py-2 text-gray-900 dark:text-white bg-white dark:bg-gray-700 focus:border-purple-500 dark:focus:border-purple-400 focus:outline-none focus:ring-2 focus:ring-purple-500/20 dark:focus:ring-purple-400/20 transition-all font-mono text-sm"
                      placeholder="main"
                      required
                    />
                    <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">PR will merge into this branch</p>
                  </div>
                </div>
              </div>

              {/* PR Title */}
              <div className="space-y-2">
                <label className="flex items-center gap-2 text-sm font-semibold text-gray-700 dark:text-gray-300">
                  <span className="i-ph:text-aa text-lg text-purple-500" />
                  Pull Request Title
                  <span className="text-red-500">*</span>
                </label>
                <input
                  type="text"
                  value={prTitle}
                  onChange={(e) => setPRTitle(e.target.value)}
                  className="w-full rounded-xl border-2 border-gray-300 dark:border-gray-600 px-4 py-3 text-gray-900 dark:text-white bg-white dark:bg-gray-700 focus:border-purple-500 dark:focus:border-purple-400 focus:outline-none focus:ring-2 focus:ring-purple-500/20 dark:focus:ring-purple-400/20 transition-all"
                  placeholder="Add new feature or fix bug"
                  required
                />
              </div>

              {/* PR Description */}
              <div className="space-y-2">
                <label className="flex items-center gap-2 text-sm font-semibold text-gray-700 dark:text-gray-300">
                  <span className="i-ph:note-pencil text-lg text-purple-500" />
                  Description
                </label>
                <textarea
                  value={prDescription}
                  onChange={(e) => setPRDescription(e.target.value)}
                  rows={5}
                  className="w-full rounded-xl border-2 border-gray-300 dark:border-gray-600 px-4 py-3 text-gray-900 dark:text-white bg-white dark:bg-gray-700 focus:border-purple-500 dark:focus:border-purple-400 focus:outline-none focus:ring-2 focus:ring-purple-500/20 dark:focus:ring-purple-400/20 transition-all resize-none"
                  placeholder="Describe your changes..."
                />
              </div>

              {/* Modified Files Preview */}
              <div className="space-y-2">
                <label className="flex items-center gap-2 text-sm font-semibold text-gray-700 dark:text-gray-300">
                  <span className="i-ph:file-code-fill text-lg text-purple-500" />
                  Files to Include
                  <span className="ml-1 inline-flex items-center justify-center px-2 py-0.5 text-xs font-bold text-purple-700 dark:text-purple-300 bg-purple-100 dark:bg-purple-900/40 rounded-full">
                    {Object.keys(modifiedFiles).length}
                  </span>
                </label>
                <div className="rounded-xl border-2 border-gray-200 dark:border-gray-700 bg-gradient-to-br from-gray-50 to-gray-100 dark:from-gray-800 dark:to-gray-900 shadow-inner">
                  <div className="max-h-40 overflow-y-auto p-4">
                    {Object.keys(modifiedFiles).length > 0 ? (
                      <div className="space-y-2">
                        {Object.keys(modifiedFiles).map((filePath) => (
                          <div
                            key={filePath}
                            className="flex items-center gap-3 text-sm bg-white dark:bg-gray-800 rounded-lg px-3 py-2 shadow-sm border border-gray-200 dark:border-gray-700"
                          >
                            <span className="flex-shrink-0 w-2 h-2 rounded-full bg-purple-500 dark:bg-purple-400" />
                            <span className="i-ph:file-fill text-gray-400 dark:text-gray-500 text-base" />
                            <span className="flex-1 font-mono text-xs text-gray-700 dark:text-gray-300 truncate">
                              {filePath}
                            </span>
                          </div>
                        ))}
                      </div>
                    ) : (
                      <div className="flex flex-col items-center justify-center py-8 text-gray-400 dark:text-gray-500">
                        <span className="i-ph:files text-4xl mb-2 opacity-50" />
                        <p className="text-sm">No files to include</p>
                      </div>
                    )}
                  </div>
                </div>
              </div>

              {/* Action Buttons */}
              <div className="flex justify-end gap-3 pt-2">
                <button
                  type="button"
                  onClick={onClose}
                  className="group flex items-center gap-2 rounded-xl border-2 border-gray-300 dark:border-gray-600 px-6 py-2.5 text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 transition-all font-medium shadow-sm hover:shadow"
                >
                  <span className="i-ph:x text-lg group-hover:rotate-90 transition-transform" />
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isLoading || !prTitle.trim() || Object.keys(modifiedFiles).length === 0}
                  className="group flex items-center gap-2 rounded-xl bg-gradient-to-r from-purple-600 to-blue-600 hover:from-purple-700 hover:to-blue-700 px-6 py-2.5 text-white font-semibold shadow-lg hover:shadow-xl disabled:cursor-not-allowed disabled:opacity-50 disabled:shadow-none transition-all disabled:from-gray-400 disabled:to-gray-500"
                >
                  {isLoading ? (
                    <>
                      <span className="i-ph:circle-notch animate-spin text-lg" />
                      Creating PR...
                    </>
                  ) : (
                    <>
                      <span className="i-ph:git-pull-request text-lg group-hover:scale-110 transition-transform" />
                      Create Pull Request
                    </>
                  )}
                </button>
              </div>
            </form>
          </div>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}
