import * as Dialog from '@radix-ui/react-dialog';
import { useState, useEffect } from 'react';
import { toast } from 'react-toastify';
import { classNames } from '~/utils/classNames';
import { getLocalStorage } from '~/lib/persistence/localStorage';
import type { GitHubUserResponse, GitHubRepoInfo } from '~/types/GitHub';
import { logStore } from '~/lib/stores/logs';
import { GitHubAuthDialog } from '~/components/@settings/tabs/github/components/GitHubAuthDialog';
import { SearchInput, StatusIndicator, Badge } from '~/components/ui';
import { BranchSelector } from '~/components/ui/BranchSelector';
import { workbenchStore } from '~/lib/stores/workbench';
import { useModifiedFiles } from '~/lib/hooks';

interface GitHubCommitDialogProps {
  isOpen: boolean;
  onClose: () => void;
}

export function GitHubCommitDialog({ isOpen, onClose }: GitHubCommitDialogProps) {
  const [repoName, setRepoName] = useState('');
  const [isPrivate, setIsPrivate] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [user, setUser] = useState<GitHubUserResponse | null>(null);
  const [recentRepos, setRecentRepos] = useState<GitHubRepoInfo[]>([]);
  const [filteredRepos, setFilteredRepos] = useState<GitHubRepoInfo[]>([]);
  const [repoSearchQuery, setRepoSearchQuery] = useState('');
  const [showSuccessDialog, setShowSuccessDialog] = useState(false);
  const [createdRepoUrl, setCreatedRepoUrl] = useState('');
  const [commitMessage, setCommitMessage] = useState('');
  const [selectedBranch, setSelectedBranch] = useState('main');
  const [showAuthDialog, setShowAuthDialog] = useState(false);
  const [selectedRepo, setSelectedRepo] = useState<GitHubRepoInfo | null>(null);
  const [isCurrentRepo, setIsCurrentRepo] = useState(false);

  // Use centralized hook for modified files
  const { filePathsSet: modifiedFiles } = useModifiedFiles();

  // Check if a repository is currently open
  const currentRepo = workbenchStore.getCurrentRepository();

  // Load GitHub connection on mount
  useEffect(() => {
    if (isOpen) {
      const connection = getLocalStorage('github_connection');

      if (connection?.user && connection?.token) {
        setUser(connection.user);

        // Check if we have a currently open GitHub repository
        if (currentRepo?.isOpen && currentRepo.provider === 'github') {
          setRepoName(currentRepo.name || 'my-repo');
          setSelectedBranch(currentRepo.branch || 'main');
          setIsCurrentRepo(true);

          // Pre-select the current repository if available
          if (currentRepo.owner && currentRepo.name) {
            setSelectedRepo({
              id: '0',
              name: currentRepo.name,
              full_name: currentRepo.fullName || `${currentRepo.owner}/${currentRepo.name}`,
              html_url: currentRepo.remoteUrl || '',
              description: '',
              stargazers_count: 0,
              forks_count: 0,
              default_branch: currentRepo.branch || 'main',
              updated_at: new Date().toISOString(),
              language: '',
              languages_url: '',
              private: false,
            });
          }
        } else {
          setRepoName('my-repo');
          setIsCurrentRepo(false);
        }

        // Only fetch if we have both user and token
        if (connection.token.trim()) {
          fetchRecentRepos(connection.token);
        }
      } else {
        setShowAuthDialog(true);
      }
    }
  }, [isOpen, currentRepo]);

  // Filter repos based on search query
  useEffect(() => {
    if (repoSearchQuery.trim()) {
      const filtered = recentRepos.filter(
        (repo) =>
          repo.name.toLowerCase().includes(repoSearchQuery.toLowerCase()) ||
          repo.full_name.toLowerCase().includes(repoSearchQuery.toLowerCase()),
      );
      setFilteredRepos(filtered);
    } else {
      setFilteredRepos(recentRepos);
    }
  }, [repoSearchQuery, recentRepos]);

  const fetchRecentRepos = async (token: string) => {
    try {
      setIsLoading(true);

      const response = await fetch('https://api.github.com/user/repos?sort=updated&per_page=20', {
        headers: {
          Authorization: `Bearer ${token}`,
          Accept: 'application/vnd.github.v3+json',
        },
      });

      if (response.ok) {
        const repos = (await response.json()) as GitHubRepoInfo[];
        setRecentRepos(repos);
        setFilteredRepos(repos);
      } else {
        console.error('Failed to fetch repositories:', response.statusText);
        toast.error('Failed to fetch repositories');
      }
    } catch (error) {
      console.error('Error fetching repositories:', error);
      toast.error('Error fetching repositories');
    } finally {
      setIsLoading(false);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!commitMessage.trim()) {
      toast.error('Please enter a commit message');
      return;
    }

    if (modifiedFiles.size === 0) {
      toast.error('No files to commit');
      return;
    }

    const connection = getLocalStorage('github_connection');

    if (!connection?.token) {
      toast.error('GitHub connection not found');
      return;
    }

    try {
      setIsLoading(true);

      let repoUrl: string;

      if (selectedRepo) {
        // Commit to existing repository
        repoUrl = await workbenchStore.pushToRepository(
          'github',
          selectedRepo.name,
          commitMessage,
          user!.login,
          connection.token,
          selectedRepo.private || false,
          selectedBranch,
        );
      } else {
        // Create new repository and commit
        repoUrl = await workbenchStore.pushToRepository(
          'github',
          repoName,
          commitMessage,
          user!.login,
          connection.token,
          isPrivate,
          selectedBranch,
        );
      }

      setCreatedRepoUrl(repoUrl);
      setShowSuccessDialog(true);

      logStore.logSystem('Files committed to GitHub repository', {
        repoUrl,
        commitMessage,
        branch: selectedBranch,
        filesCount: modifiedFiles.size,
      });

      toast.success('Files committed successfully!');
    } catch (error) {
      console.error('Error committing files:', error);
      toast.error('Failed to commit files');
    } finally {
      setIsLoading(false);
    }
  };

  const handleRepoSelect = (repo: GitHubRepoInfo) => {
    setSelectedRepo(repo);
    setRepoName(repo.name);
    setIsPrivate(repo.private || false);
    setSelectedBranch(repo.default_branch || 'main');
  };

  const handleCreateNewRepo = () => {
    setSelectedRepo(null);
    setRepoName('');
    setIsPrivate(false);
    setSelectedBranch('main');
  };

  const handleAuthSuccess = () => {
    setShowAuthDialog(false);

    const connection = getLocalStorage('github_connection');

    if (connection?.user && connection?.token) {
      setUser(connection.user);
      setRepoName('my-repo');
      fetchRecentRepos(connection.token);
    }
  };

  const handleClose = () => {
    setShowSuccessDialog(false);
    setCreatedRepoUrl('');
    setCommitMessage('');
    setSelectedBranch('main');
    setSelectedRepo(null);
    setRepoName('');
    setIsPrivate(false);
    setRepoSearchQuery('');
    onClose();
  };

  if (showAuthDialog) {
    return (
      <GitHubAuthDialog
        isOpen={showAuthDialog}
        onClose={() => setShowAuthDialog(false)}
        onSuccess={handleAuthSuccess}
      />
    );
  }

  if (showSuccessDialog) {
    return (
      <Dialog.Root open={showSuccessDialog} onOpenChange={setShowSuccessDialog}>
        <Dialog.Portal>
          <Dialog.Overlay className="fixed inset-0 bg-black/60 backdrop-blur-sm z-[9999] animate-in fade-in duration-200" />
          <Dialog.Content className="fixed left-1/2 top-1/2 w-full max-w-md -translate-x-1/2 -translate-y-1/2 rounded-2xl bg-white dark:bg-gray-800 shadow-2xl z-[10000] overflow-hidden animate-in zoom-in-95 fade-in duration-200">
            {/* Success Header */}
            <div className="bg-gradient-to-r from-green-500 to-emerald-500 px-6 py-5 text-center">
              <div className="flex justify-center mb-3">
                <div className="w-16 h-16 rounded-full bg-white/20 backdrop-blur-sm flex items-center justify-center animate-bounce">
                  <span className="i-ph:check-circle-fill text-white text-4xl" />
                </div>
              </div>
              <Dialog.Title className="text-2xl font-bold text-white mb-1">Commit Successful!</Dialog.Title>
              <p className="text-green-50 text-sm">Your changes have been pushed to GitHub</p>
            </div>

            {/* Success Content */}
            <div className="p-6">
              <div className="bg-gradient-to-br from-green-50 to-emerald-50 dark:from-green-900/20 dark:to-emerald-900/20 rounded-xl p-4 border-2 border-green-200 dark:border-green-800 mb-4">
                <div className="flex items-start gap-3">
                  <span className="i-ph:git-commit text-green-600 dark:text-green-400 text-xl flex-shrink-0 mt-0.5" />
                  <div className="flex-1">
                    <p className="text-sm text-green-800 dark:text-green-200 font-medium mb-1">
                      All modified files have been committed successfully
                    </p>
                    <p className="text-xs text-green-700 dark:text-green-300">
                      Your changes are now part of the repository history
                    </p>
                  </div>
                </div>
              </div>

              {createdRepoUrl && (
                <a
                  href={createdRepoUrl}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex items-center justify-center gap-2 w-full rounded-xl bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-700 hover:to-purple-700 px-4 py-3 text-white font-semibold shadow-lg hover:shadow-xl transition-all group mb-3"
                >
                  <span className="i-ph:github-logo-fill text-xl" />
                  View Repository on GitHub
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
          <div className="bg-gradient-to-r from-blue-600 to-purple-600 px-6 py-5">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-full bg-white/20 backdrop-blur-sm flex items-center justify-center">
                  <span className="i-ph:github-logo-fill text-white text-2xl" />
                </div>
                <Dialog.Title className="text-2xl font-bold text-white">Commit to GitHub</Dialog.Title>
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
              {isCurrentRepo && currentRepo && (
                <div className="rounded-xl bg-gradient-to-r from-green-50 to-emerald-50 dark:from-green-900/20 dark:to-emerald-900/20 border-2 border-green-200 dark:border-green-800 p-5 shadow-sm">
                  <div className="flex items-start gap-4">
                    <div className="flex-shrink-0 w-10 h-10 rounded-full bg-green-100 dark:bg-green-900/40 flex items-center justify-center">
                      <div className="i-ph:check-circle-fill text-green-600 dark:text-green-400 text-2xl" />
                    </div>
                    <div className="flex-1 min-w-0">
                      <h4 className="text-base font-bold text-green-900 dark:text-green-100 mb-2 flex items-center gap-2">
                        <span className="i-ph:git-branch-fill text-lg" />
                        Committing to Current Repository
                      </h4>
                      <div className="space-y-2">
                        <div className="flex items-center gap-2 text-sm text-green-800 dark:text-green-200">
                          <span className="i-ph:github-logo-fill text-base" />
                          <span className="font-mono font-semibold bg-green-100 dark:bg-green-900/60 px-2 py-0.5 rounded">
                            {currentRepo.fullName}
                          </span>
                        </div>
                        <div className="flex items-center gap-2 text-sm text-green-700 dark:text-green-300">
                          <span className="i-ph:git-branch text-base" />
                          <span>
                            Branch: <span className="font-semibold">{currentRepo.branch}</span>
                          </span>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              )}

              {/* Repository Selection - Only show if no current repo */}
              {!isCurrentRepo && (
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">Repository</label>
                  <div className="mt-2 space-y-3">
                    {/* Existing Repository Selection */}
                    <div>
                      <SearchInput
                        placeholder="Search existing repositories..."
                        value={repoSearchQuery}
                        onChange={(e) => setRepoSearchQuery(e.target.value)}
                        className="w-full"
                      />
                      {filteredRepos.length > 0 && (
                        <div className="mt-2 max-h-32 overflow-y-auto rounded border">
                          {filteredRepos.map((repo) => (
                            <div
                              key={repo.id}
                              className={classNames(
                                'cursor-pointer p-3 hover:bg-gray-50 dark:hover:bg-gray-700',
                                selectedRepo?.id === repo.id && 'bg-blue-50 dark:bg-blue-900/20',
                              )}
                              onClick={() => handleRepoSelect(repo)}
                            >
                              <div className="flex items-center justify-between">
                                <div>
                                  <p className="font-medium text-gray-900 dark:text-white">{repo.full_name}</p>
                                  {repo.description && (
                                    <p className="text-sm text-gray-500 dark:text-gray-400">{repo.description}</p>
                                  )}
                                </div>
                                <div className="flex items-center gap-2">
                                  <Badge variant={repo.private ? 'destructive' : 'secondary'}>
                                    {repo.private ? 'Private' : 'Public'}
                                  </Badge>
                                  <StatusIndicator status="success" />
                                </div>
                              </div>
                            </div>
                          ))}
                        </div>
                      )}
                    </div>

                    {/* Create New Repository */}
                    <div className="flex items-center gap-4">
                      <div className="flex-1">
                        <input
                          type="text"
                          placeholder="Repository name"
                          value={repoName}
                          onChange={(e) => setRepoName(e.target.value)}
                          className="w-full rounded-md border border-gray-300 px-3 py-2 text-gray-900 placeholder-gray-500 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500 dark:border-gray-600 dark:bg-gray-700 dark:text-white dark:placeholder-gray-400"
                          disabled={!!selectedRepo}
                        />
                      </div>
                      <label className="flex items-center gap-2">
                        <input
                          type="checkbox"
                          checked={isPrivate}
                          onChange={(e) => setIsPrivate(e.target.checked)}
                          className="rounded border-gray-300 text-blue-600 focus:ring-blue-500 dark:border-gray-600 dark:bg-gray-700"
                          disabled={!!selectedRepo}
                        />
                        <span className="text-sm text-gray-700 dark:text-gray-300">Private</span>
                      </label>
                    </div>

                    <button
                      type="button"
                      onClick={handleCreateNewRepo}
                      className="text-sm text-blue-600 hover:text-blue-800 dark:text-blue-400 dark:hover:text-blue-300"
                    >
                      Create new repository
                    </button>
                  </div>
                </div>
              )}

              {/* Branch Selection */}
              {(selectedRepo || isCurrentRepo) && (
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">Branch</label>
                  <div className="mt-2">
                    <BranchSelector
                      provider="github"
                      repoOwner={user?.login || ''}
                      repoName={selectedRepo?.name || repoName}
                      token={getLocalStorage('github_connection')?.token}
                      defaultBranch={selectedBranch}
                      onBranchSelect={setSelectedBranch}
                      onClose={() => {
                        /* BranchSelector onClose handler */
                      }}
                      isOpen={false}
                      className="w-full"
                    />
                  </div>
                </div>
              )}

              {/* Commit Message */}
              <div className="space-y-2">
                <label className="flex items-center gap-2 text-sm font-semibold text-gray-700 dark:text-gray-300">
                  <span className="i-ph:chat-text-fill text-lg text-blue-500" />
                  Commit Message
                  <span className="text-red-500">*</span>
                </label>
                <div className="relative">
                  <textarea
                    value={commitMessage}
                    onChange={(e) => setCommitMessage(e.target.value)}
                    placeholder="Describe your changes..."
                    rows={4}
                    className="w-full rounded-xl border-2 border-gray-300 dark:border-gray-600 px-4 py-3 text-gray-900 dark:text-white placeholder-gray-400 dark:placeholder-gray-500 bg-white dark:bg-gray-700 focus:border-blue-500 dark:focus:border-blue-400 focus:outline-none focus:ring-2 focus:ring-blue-500/20 dark:focus:ring-blue-400/20 transition-all resize-none shadow-sm"
                    required
                  />
                  <div className="absolute bottom-3 right-3 text-xs text-gray-400 dark:text-gray-500">
                    {commitMessage.length} characters
                  </div>
                </div>
                <p className="text-xs text-gray-500 dark:text-gray-400 flex items-center gap-1">
                  <span className="i-ph:info" />
                  Use a clear and descriptive message for your commit
                </p>
              </div>

              {/* Modified Files Preview */}
              <div className="space-y-2">
                <label className="flex items-center gap-2 text-sm font-semibold text-gray-700 dark:text-gray-300">
                  <span className="i-ph:file-code-fill text-lg text-purple-500" />
                  Files to Commit
                  <span className="ml-1 inline-flex items-center justify-center px-2 py-0.5 text-xs font-bold text-purple-700 dark:text-purple-300 bg-purple-100 dark:bg-purple-900/40 rounded-full">
                    {modifiedFiles.size}
                  </span>
                </label>
                <div className="rounded-xl border-2 border-gray-200 dark:border-gray-700 bg-gradient-to-br from-gray-50 to-gray-100 dark:from-gray-800 dark:to-gray-900 shadow-inner">
                  <div className="max-h-40 overflow-y-auto p-4">
                    {modifiedFiles.size > 0 ? (
                      <div className="space-y-2">
                        {Array.from(modifiedFiles).map((filePath) => (
                          <div
                            key={filePath}
                            className="flex items-center gap-3 text-sm bg-white dark:bg-gray-800 rounded-lg px-3 py-2 shadow-sm hover:shadow-md transition-shadow border border-gray-200 dark:border-gray-700"
                          >
                            <span className="flex-shrink-0 w-2 h-2 rounded-full bg-green-500 dark:bg-green-400 animate-pulse" />
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
                        <p className="text-sm">No files to commit</p>
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
                  disabled={isLoading || !commitMessage.trim() || modifiedFiles.size === 0}
                  className="group flex items-center gap-2 rounded-xl bg-gradient-to-r from-blue-600 to-blue-700 hover:from-blue-700 hover:to-blue-800 px-6 py-2.5 text-white font-semibold shadow-lg hover:shadow-xl disabled:cursor-not-allowed disabled:opacity-50 disabled:shadow-none transition-all disabled:from-gray-400 disabled:to-gray-500"
                >
                  {isLoading ? (
                    <>
                      <span className="i-ph:circle-notch animate-spin text-lg" />
                      Committing...
                    </>
                  ) : (
                    <>
                      <span className="i-ph:git-commit text-lg group-hover:scale-110 transition-transform" />
                      Commit Changes
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
