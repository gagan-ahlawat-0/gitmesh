import * as Dialog from '@radix-ui/react-dialog';
import { useState, useEffect } from 'react';
import { toast } from 'react-toastify';
import { classNames } from '~/utils/classNames';
import { getLocalStorage } from '~/lib/persistence/localStorage';
import type { GitLabUserResponse, GitLabProjectInfo } from '~/types/GitLab';
import { logStore } from '~/lib/stores/logs';
import { GitLabAuthDialog } from '~/components/@settings/tabs/gitlab/components/GitLabAuthDialog';
import { SearchInput, StatusIndicator, Badge } from '~/components/ui';
import { BranchSelector } from '~/components/ui/BranchSelector';
import { workbenchStore } from '~/lib/stores/workbench';
import { useModifiedFiles } from '~/lib/hooks';

interface GitLabCommitDialogProps {
  isOpen: boolean;
  onClose: () => void;
}

export function GitLabCommitDialog({ isOpen, onClose }: GitLabCommitDialogProps) {
  const [projectName, setProjectName] = useState('');
  const [isPrivate, setIsPrivate] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [user, setUser] = useState<GitLabUserResponse | null>(null);
  const [recentProjects, setRecentProjects] = useState<GitLabProjectInfo[]>([]);
  const [filteredProjects, setFilteredProjects] = useState<GitLabProjectInfo[]>([]);
  const [projectSearchQuery, setProjectSearchQuery] = useState('');
  const [showSuccessDialog, setShowSuccessDialog] = useState(false);
  const [createdProjectUrl, setCreatedProjectUrl] = useState('');
  const [commitMessage, setCommitMessage] = useState('');
  const [selectedBranch, setSelectedBranch] = useState('main');
  const [showAuthDialog, setShowAuthDialog] = useState(false);
  const [selectedProject, setSelectedProject] = useState<GitLabProjectInfo | null>(null);

  // Use centralized hook for modified files
  const { filePathsSet: modifiedFiles } = useModifiedFiles();

  // Load GitLab connection on mount and preselect current repo if available
  useEffect(() => {
    if (isOpen) {
      const connection = getLocalStorage('gitlab_connection');

      if (connection?.user && connection?.token) {
        setUser(connection.user);

        // Check if we have a current repository open
        const currentRepo = workbenchStore.getCurrentRepository();

        if (currentRepo?.isOpen && currentRepo.provider === 'gitlab') {
          // Auto-select the current repository
          setProjectName(currentRepo.name || 'my-project');
          setSelectedBranch(currentRepo.branch || 'main');

          // Create a mock project to mark it as selected (hides the selector)
          setSelectedProject({
            id: 0,
            name: currentRepo.name || '',
            path_with_namespace: currentRepo.fullName || '',
            description: '',
            http_url_to_repo: currentRepo.remoteUrl || '',
            star_count: 0,
            forks_count: 0,
            updated_at: new Date().toISOString(),
            default_branch: currentRepo.branch || 'main',
            visibility: 'private',
          });
        } else {
          setProjectName('my-project');
        }

        // Only fetch if we have both user and token
        if (connection.token.trim()) {
          fetchRecentProjects(connection.token, connection.gitlabUrl || 'https://gitlab.com');
        }
      } else {
        setShowAuthDialog(true);
      }
    }
  }, [isOpen]);

  // Filter projects based on search query
  useEffect(() => {
    if (!projectSearchQuery.trim()) {
      setFilteredProjects(recentProjects);
    } else {
      const filtered = recentProjects.filter((project) =>
        project.name.toLowerCase().includes(projectSearchQuery.toLowerCase()),
      );
      setFilteredProjects(filtered);
    }
  }, [projectSearchQuery, recentProjects]);

  const fetchRecentProjects = async (token: string, gitlabUrl: string) => {
    if (!token) {
      logStore.logError('No GitLab token available');
      return;
    }

    try {
      const response = await fetch(`${gitlabUrl}/api/v4/projects?membership=true&per_page=20&sort=last_activity_at`, {
        headers: {
          Authorization: `Bearer ${token}`,
          Accept: 'application/json',
          'User-Agent': 'gitmesh-app',
        },
      });

      if (!response.ok) {
        throw new Error(`GitLab API error: ${response.status}`);
      }

      const projects: GitLabProjectInfo[] = await response.json();
      setRecentProjects(projects);
      setFilteredProjects(projects);
    } catch (error) {
      console.error('Error fetching projects:', error);
      logStore.logError('Failed to fetch projects', error);
      toast.error('Failed to fetch projects');
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!user || !projectName.trim()) {
      toast.error('Please provide a project name');
      return;
    }

    if (!commitMessage.trim()) {
      toast.error('Please provide a commit message');
      return;
    }

    if (modifiedFiles.size === 0) {
      toast.error('No files to commit');
      return;
    }

    setIsLoading(true);

    try {
      const connection = getLocalStorage('gitlab_connection');

      if (!connection?.token) {
        throw new Error('No GitLab token found');
      }

      // Get modified files from workbench store
      const files: Record<string, string> = {};

      for (const filePath of modifiedFiles) {
        const file = workbenchStore.files.get()[filePath];

        if (file?.type === 'file' && file.content !== undefined) {
          files[filePath] = file.content;
        }
      }

      // Use existing pushToRepository method
      const projectUrl = await workbenchStore.pushToRepository(
        'gitlab',
        projectName,
        commitMessage,
        user.username,
        connection.token,
        isPrivate,
        selectedBranch,
      );

      setCreatedProjectUrl(projectUrl);
      setShowSuccessDialog(true);

      logStore.logSystem('Files committed to GitLab project', {
        projectName,
        commitMessage,
        filesCount: Object.keys(files).length,
        branch: selectedBranch,
      });
    } catch (error) {
      console.error('Error committing files:', error);
      logStore.logError('Failed to commit files', error);
      toast.error('Failed to commit files');
    } finally {
      setIsLoading(false);
    }
  };

  const handleProjectSelect = (project: GitLabProjectInfo) => {
    setSelectedProject(project);
    setProjectName(project.name);
    setIsPrivate(project.visibility === 'private');
    setSelectedBranch(project.default_branch || 'main');
  };

  const handleCreateNewProject = () => {
    setSelectedProject(null);
    setProjectName('');
    setIsPrivate(false);
    setSelectedBranch('main');
  };

  return (
    <>
      <Dialog.Root open={isOpen} onOpenChange={onClose}>
        <Dialog.Portal>
          <Dialog.Overlay className="fixed inset-0 bg-black/50 z-[9999]" />
          <Dialog.Content className="fixed top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2 bg-gitmesh-elements-background-depth-1 border border-gitmesh-elements-borderColor rounded-lg shadow-xl z-[10000] w-full max-w-2xl max-h-[90vh] overflow-hidden">
            <div className="flex flex-col h-full">
              <Dialog.Title className="text-lg font-semibold p-6 border-b border-gitmesh-elements-borderColor">
                Commit to GitLab
              </Dialog.Title>

              <div className="flex-1 overflow-y-auto p-6">
                <form onSubmit={handleSubmit} className="space-y-6">
                  {/* Project Selection */}
                  <div>
                    <label className="block text-sm font-medium mb-2">Project</label>
                    <div className="space-y-3">
                      {/* Search existing projects */}
                      <SearchInput
                        placeholder="Search projects..."
                        value={projectSearchQuery}
                        onChange={(e) => setProjectSearchQuery(e.target.value)}
                        className="w-full"
                      />

                      {/* Recent projects */}
                      {filteredProjects.length > 0 && (
                        <div className="border border-gitmesh-elements-borderColor rounded-md max-h-40 overflow-y-auto">
                          {filteredProjects.map((project) => (
                            <div
                              key={project.id}
                              className={classNames(
                                'p-3 cursor-pointer hover:bg-gitmesh-elements-background-depth-2 border-b border-gitmesh-elements-borderColor last:border-b-0',
                                selectedProject?.id === project.id && 'bg-gitmesh-elements-background-depth-2',
                              )}
                              onClick={() => handleProjectSelect(project)}
                            >
                              <div className="flex items-center justify-between">
                                <div>
                                  <div className="font-medium">{project.name}</div>
                                  {project.description && (
                                    <div className="text-sm text-gitmesh-elements-textSecondary">
                                      {project.description}
                                    </div>
                                  )}
                                </div>
                                <div className="flex items-center gap-2">
                                  <Badge variant="secondary">{project.visibility}</Badge>
                                  <StatusIndicator status="success" />
                                </div>
                              </div>
                            </div>
                          ))}
                        </div>
                      )}

                      {/* Create new project option */}
                      <div
                        className={classNames(
                          'p-3 cursor-pointer hover:bg-gitmesh-elements-background-depth-2 border border-gitmesh-elements-borderColor rounded-md',
                          !selectedProject && 'bg-gitmesh-elements-background-depth-2',
                        )}
                        onClick={handleCreateNewProject}
                      >
                        <div className="font-medium">+ Create new project</div>
                      </div>
                    </div>
                  </div>

                  {/* Project details for new project */}
                  {!selectedProject && (
                    <>
                      <div>
                        <label className="block text-sm font-medium mb-2">Project Name</label>
                        <input
                          type="text"
                          value={projectName}
                          onChange={(e) => setProjectName(e.target.value)}
                          className="w-full px-3 py-2 border border-gitmesh-elements-borderColor rounded-md bg-gitmesh-elements-background-depth-1 text-gitmesh-elements-textPrimary"
                          placeholder="Enter project name"
                          required
                        />
                      </div>

                      <div className="flex items-center gap-2">
                        <input
                          type="checkbox"
                          id="isPrivate"
                          checked={isPrivate}
                          onChange={(e) => setIsPrivate(e.target.checked)}
                          className="rounded"
                        />
                        <label htmlFor="isPrivate" className="text-sm">
                          Make this project private
                        </label>
                      </div>
                    </>
                  )}

                  {/* Branch Selection */}
                  {user && projectName && (
                    <BranchSelector
                      provider="gitlab"
                      repoOwner={user?.username || ''}
                      repoName={selectedProject?.name || projectName}
                      projectId={selectedProject?.id?.toString() || ''}
                      token={getLocalStorage('gitlab_connection')?.token || ''}
                      gitlabUrl={getLocalStorage('gitlab_connection')?.gitlabUrl || 'https://gitlab.com'}
                      defaultBranch={selectedBranch}
                      onBranchSelect={setSelectedBranch}
                      onClose={() => {
                        // Empty function for BranchSelector
                      }}
                      isOpen={false}
                      className="w-full"
                    />
                  )}

                  {/* Commit Message */}
                  <div>
                    <label className="block text-sm font-medium mb-2">Commit Message</label>
                    <textarea
                      value={commitMessage}
                      onChange={(e) => setCommitMessage(e.target.value)}
                      className="w-full px-3 py-2 border border-gitmesh-elements-borderColor rounded-md bg-gitmesh-elements-background-depth-1 text-gitmesh-elements-textPrimary h-20 resize-none"
                      placeholder="Enter commit message"
                      required
                    />
                  </div>

                  {/* Modified Files Preview */}
                  <div>
                    <label className="block text-sm font-medium mb-2">Files to Commit ({modifiedFiles.size})</label>
                    <div className="border border-gitmesh-elements-borderColor rounded-md max-h-32 overflow-y-auto">
                      {Array.from(modifiedFiles).map((filePath) => (
                        <div
                          key={filePath}
                          className="p-2 border-b border-gitmesh-elements-borderColor last:border-b-0"
                        >
                          <div className="text-sm text-gitmesh-elements-textPrimary">{filePath}</div>
                        </div>
                      ))}
                    </div>
                  </div>
                </form>
              </div>

              <div className="flex justify-end gap-3 p-6 border-t border-gitmesh-elements-borderColor">
                <button
                  type="button"
                  onClick={onClose}
                  className="px-4 py-2 text-sm border border-gitmesh-elements-borderColor rounded-md hover:bg-gitmesh-elements-background-depth-2"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  onClick={handleSubmit}
                  disabled={isLoading || !projectName.trim() || !commitMessage.trim() || modifiedFiles.size === 0}
                  className="px-4 py-2 text-sm bg-orange-500 text-white rounded-md hover:bg-orange-600 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {isLoading ? 'Committing...' : 'Commit Files'}
                </button>
              </div>
            </div>
          </Dialog.Content>
        </Dialog.Portal>
      </Dialog.Root>

      {/* GitLab Auth Dialog */}
      {showAuthDialog && (
        <GitLabAuthDialog
          isOpen={showAuthDialog}
          onClose={() => {
            setShowAuthDialog(false);

            // Reload connection after auth dialog closes
            const connection = getLocalStorage('gitlab_connection');

            if (connection?.user && connection?.token) {
              setUser(connection.user);
              setProjectName('my-project');
              fetchRecentProjects(connection.token, connection.gitlabUrl || 'https://gitlab.com');
            }

            onClose();
          }}
        />
      )}

      {/* Success Dialog */}
      {showSuccessDialog && (
        <Dialog.Root open={showSuccessDialog} onOpenChange={setShowSuccessDialog}>
          <Dialog.Portal>
            <Dialog.Overlay className="fixed inset-0 bg-black/50 z-[9999]" />
            <Dialog.Content className="fixed top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2 bg-gitmesh-elements-background-depth-1 border border-gitmesh-elements-borderColor rounded-lg shadow-xl z-[10000] w-full max-w-md">
              <div className="p-6">
                <div className="text-center">
                  <div className="w-12 h-12 bg-orange-500 rounded-full flex items-center justify-center mx-auto mb-4">
                    <div className="i-ph:check text-white text-xl" />
                  </div>
                  <h3 className="text-lg font-semibold mb-2">Commit Successful!</h3>
                  <p className="text-sm text-gitmesh-elements-textSecondary mb-4">
                    Your files have been committed to GitLab successfully.
                  </p>
                  <a
                    href={createdProjectUrl}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="inline-flex items-center gap-2 px-4 py-2 bg-blue-500 text-white rounded-md hover:bg-blue-600"
                  >
                    <div className="i-ph:external-link" />
                    View Project
                  </a>
                </div>
              </div>
            </Dialog.Content>
          </Dialog.Portal>
        </Dialog.Root>
      )}
    </>
  );
}
