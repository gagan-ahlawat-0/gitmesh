import ignore from 'ignore';
import { useRepoContext } from '~/lib/contexts/RepoContext';
import { useGit } from '~/lib/hooks/useGit';
import type { Message } from 'ai';
import { detectProjectCommands, createCommandsMessage, escapegitmeshTags } from '~/utils/projectCommands';
import { generateId } from '~/utils/fileUtils';
import { useState } from 'react';
import { toast } from 'react-toastify';
import { LoadingOverlay } from '~/components/ui/LoadingOverlay';

import { classNames } from '~/utils/classNames';
import { Button } from '~/components/ui/Button';
import type { IChatMetadata } from '~/lib/persistence/db';
import { X, Github, GitBranch } from 'lucide-react';

// Import the new repository selector components
import { GitHubRepositorySelector } from '~/components/@settings/tabs/github/components/GitHubRepositorySelector';
import { GitLabRepositorySelector } from '~/components/@settings/tabs/gitlab/components/GitLabRepositorySelector';
import { useGitHubConnection, useGitLabConnection } from '~/lib/hooks';

const IGNORE_PATTERNS = [
  'node_modules/**',
  '.git/**',
  '.github/**',
  '.vscode/**',
  'dist/**',
  'build/**',
  '.next/**',
  'coverage/**',
  '.cache/**',
  '.idea/**',
  '**/*.log',
  '**/.DS_Store',
  '**/npm-debug.log*',
  '**/yarn-debug.log*',
  '**/yarn-error.log*',

  // Include this so npm install runs much faster '**/*lock.json',
  '**/*lock.yaml',
];

const ig = ignore().add(IGNORE_PATTERNS);

const MAX_FILE_SIZE = 100 * 1024; // 100KB limit per file
const MAX_TOTAL_SIZE = 500 * 1024; // 500KB total limit

interface GitCloneButtonProps {
  className?: string;
  importChat?: (description: string, messages: Message[], metadata?: IChatMetadata) => Promise<void>;
}

export default function GitCloneButton({ importChat, className }: GitCloneButtonProps) {
  const { ready, gitClone } = useGit();
  const { isConnected: isGitHubConnected } = useGitHubConnection();
  const { isConnected: isGitLabConnected } = useGitLabConnection();
  const { selectedRepo, fromHub } = useRepoContext();
  const [loading, setLoading] = useState(false);
  const [isDialogOpen, setIsDialogOpen] = useState(false);
  const [selectedProvider, setSelectedProvider] = useState<'github' | 'gitlab' | null>(null);

  const handleClone = async (repoUrl: string) => {
    if (!ready) {
      return;
    }

    setLoading(true);
    setIsDialogOpen(false);
    setSelectedProvider(null);

    try {
      const { workdir, data } = await gitClone(repoUrl);

      if (importChat) {
        const filePaths = Object.keys(data).filter((filePath) => !ig.ignores(filePath));
        const textDecoder = new TextDecoder('utf-8');

        let totalSize = 0;
        const skippedFiles: string[] = [];
        const fileContents = [];

        for (const filePath of filePaths) {
          const { data: content, encoding } = data[filePath];

          // Skip binary files
          if (
            content instanceof Uint8Array &&
            !filePath.match(/\.(txt|md|astro|mjs|js|jsx|ts|tsx|json|html|css|scss|less|yml|yaml|xml|svg|vue|svelte)$/i)
          ) {
            skippedFiles.push(filePath);
            continue;
          }

          try {
            const textContent =
              encoding === 'utf8' ? content : content instanceof Uint8Array ? textDecoder.decode(content) : '';

            if (!textContent || typeof textContent !== 'string') {
              continue;
            }

            // Check file size
            const fileSize = new TextEncoder().encode(textContent).length;

            if (fileSize > MAX_FILE_SIZE) {
              skippedFiles.push(`${filePath} (too large: ${Math.round(fileSize / 1024)}KB)`);
              continue;
            }

            // Check total size
            if (totalSize + fileSize > MAX_TOTAL_SIZE) {
              skippedFiles.push(`${filePath} (would exceed total size limit)`);
              continue;
            }

            totalSize += fileSize;
            fileContents.push({
              path: filePath,
              content: textContent,
            });
          } catch (e: any) {
            skippedFiles.push(`${filePath} (error: ${e.message})`);
          }
        }

        const commands = await detectProjectCommands(fileContents);
        const commandsMessage = createCommandsMessage(commands);

        const filesMessage: Message = {
          role: 'assistant',
          content: `Cloning the repo ${repoUrl} into ${workdir}
${
  skippedFiles.length > 0
    ? `\nSkipped files (${skippedFiles.length}):
${skippedFiles.map((f) => `- ${f}`).join('\n')}`
    : ''
}

<gitmeshArtifact id="imported-files" title="Git Cloned Files" type="bundled">
${fileContents
  .map(
    (file) =>
      `<gitmeshAction type="file" filePath="${file.path}">
${escapegitmeshTags(typeof file.content === 'string' ? file.content : '')}
</gitmeshAction>`,
  )
  .join('\n')}
</gitmeshArtifact>`,
          id: generateId(),
          createdAt: new Date(),
        };

        const messages = [filesMessage];

        if (commandsMessage) {
          messages.push(commandsMessage);
        }

        await importChat(`Git Project:${repoUrl.split('/').slice(-1)[0]}`, messages);
      }
    } catch (error) {
      console.error('Error during import:', error);
      toast.error('Failed to import repository');
    } finally {
      setLoading(false);
    }
  };

  return (
    <>
      {/* Always show clone button unless we're coming from hub and already have a repo */}
      {!(selectedRepo && fromHub) && (
        <Button
          onClick={() => {
            // If we have a selected repo from hub, clone it directly
            if (selectedRepo) {
              handleClone(selectedRepo.clone_url);
              return;
            }

            // Auto-select provider based on what's connected
            if (isGitHubConnected) {
              setSelectedProvider('github');
            } else if (isGitLabConnected) {
              setSelectedProvider('gitlab');
            } else {
              setSelectedProvider(null); // Will show provider selection
            }

            setIsDialogOpen(true);
          }}
          title={selectedRepo ? `Clone ${selectedRepo.name}` : 'Clone a repo'}
          variant="default"
          size="lg"
          className={classNames(
            'gap-2 bg-gitmesh-elements-background-depth-1',
            'text-gitmesh-elements-textPrimary',
            'hover:bg-gitmesh-elements-background-depth-1',
            'border border-gitmesh-elements-borderColor',
            'h-10 px-4 py-2 min-w-[120px] justify-center',
            'transition-all duration-200 ease-in-out',
            className,
          )}
          disabled={!ready || loading}
        >
          {selectedRepo ? (
            <>
              Clone {selectedRepo.name}
              <div className="flex items-center gap-1 ml-2">
                {selectedRepo.provider === 'github' ? (
                  <Github className="w-4 h-4" />
                ) : (
                  <GitBranch className="w-4 h-4" />
                )}
              </div>
            </>
          ) : (
            <>
              Clone a repo
              <div className="flex items-center gap-1 ml-2">
                <Github className="w-4 h-4" />
                <GitBranch className="w-4 h-4" />
              </div>
            </>
          )}
        </Button>
      )}

      {/* Provider Selection Dialog - only show when no providers are connected and no repo is selected */}
      {isDialogOpen && !selectedProvider && !selectedRepo && !isGitHubConnected && !isGitLabConnected && (
        <div className="fixed inset-0 bg-black/50 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-white dark:bg-gray-950 rounded-xl shadow-xl border border-gitmesh-elements-borderColor dark:border-gitmesh-elements-borderColor max-w-md w-full">
            <div className="p-6">
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-lg font-semibold text-gitmesh-elements-textPrimary dark:text-gitmesh-elements-textPrimary">
                  Choose Repository Provider
                </h3>
                <button
                  onClick={() => setIsDialogOpen(false)}
                  className="p-2 rounded-lg bg-transparent hover:bg-gitmesh-elements-background-depth-1 dark:hover:bg-gitmesh-elements-background-depth-1 text-gitmesh-elements-textSecondary dark:text-gitmesh-elements-textSecondary hover:text-gitmesh-elements-textPrimary dark:hover:text-gitmesh-elements-textPrimary transition-all duration-200 hover:scale-105 active:scale-95"
                >
                  <X className="w-5 h-5 transition-transform duration-200 hover:rotate-90" />
                </button>
              </div>

              <div className="space-y-3">
                <button
                  onClick={() => setSelectedProvider('github')}
                  className="w-full p-4 rounded-lg bg-gitmesh-elements-background-depth-1 dark:bg-gitmesh-elements-background-depth-1 hover:bg-gitmesh-elements-background-depth-1 dark:hover:bg-gitmesh-elements-background-depth-1 border border-gitmesh-elements-borderColor dark:border-gitmesh-elements-borderColor hover:border-gitmesh-elements-borderColorActive dark:hover:border-gitmesh-elements-borderColorActive transition-all duration-200 text-left group"
                >
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 rounded-lg bg-blue-500/10 dark:bg-blue-500/20 flex items-center justify-center group-hover:bg-blue-500/20 dark:group-hover:bg-blue-500/30 transition-colors">
                      <Github className="w-6 h-6 text-blue-600 dark:text-blue-400" />
                    </div>
                    <div>
                      <div className="font-medium text-gitmesh-elements-textPrimary dark:text-gitmesh-elements-textPrimary">
                        GitHub
                      </div>
                      <div className="text-sm text-gitmesh-elements-textSecondary dark:text-gitmesh-elements-textSecondary">
                        Clone from GitHub repositories
                      </div>
                    </div>
                  </div>
                </button>

                <button
                  onClick={() => setSelectedProvider('gitlab')}
                  className="w-full p-4 rounded-lg bg-gitmesh-elements-background-depth-1 dark:bg-gitmesh-elements-background-depth-1 hover:bg-gitmesh-elements-background-depth-1 dark:hover:bg-gitmesh-elements-background-depth-1 border border-gitmesh-elements-borderColor dark:border-gitmesh-elements-borderColor hover:border-gitmesh-elements-borderColorActive dark:hover:border-gitmesh-elements-borderColorActive transition-all duration-200 text-left group"
                >
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 rounded-lg bg-orange-500/10 dark:bg-orange-500/20 flex items-center justify-center group-hover:bg-orange-500/20 dark:group-hover:bg-orange-500/30 transition-colors">
                      <GitBranch className="w-6 h-6 text-orange-600 dark:text-orange-400" />
                    </div>
                    <div>
                      <div className="font-medium text-gitmesh-elements-textPrimary dark:text-gitmesh-elements-textPrimary">
                        GitLab
                      </div>
                      <div className="text-sm text-gitmesh-elements-textSecondary dark:text-gitmesh-elements-textSecondary">
                        Clone from GitLab repositories
                      </div>
                    </div>
                  </div>
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Repository Selection - only show when no repo is selected */}
      {isDialogOpen && selectedProvider && !selectedRepo && (
        <div className="fixed inset-0 bg-black/50 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-white dark:bg-gray-950 rounded-xl shadow-xl border border-gitmesh-elements-borderColor dark:border-gitmesh-elements-borderColor w-full max-w-4xl max-h-[90vh] overflow-hidden">
            <div className="p-6 border-b border-gitmesh-elements-borderColor dark:border-gitmesh-elements-borderColor flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div
                  className={`w-10 h-10 rounded-lg ${selectedProvider === 'github' ? 'bg-blue-500/10 dark:bg-blue-500/20' : 'bg-orange-500/10 dark:bg-orange-500/20'} flex items-center justify-center`}
                >
                  {selectedProvider === 'github' ? (
                    <Github className="w-6 h-6 text-blue-600 dark:text-blue-400" />
                  ) : (
                    <GitBranch className="w-6 h-6 text-orange-600 dark:text-orange-400" />
                  )}
                </div>
                <div>
                  <h3 className="text-lg font-semibold text-gitmesh-elements-textPrimary dark:text-gitmesh-elements-textPrimary">
                    Import {selectedProvider === 'github' ? 'GitHub' : 'GitLab'} Repository
                  </h3>
                  <p className="text-sm text-gitmesh-elements-textSecondary dark:text-gitmesh-elements-textSecondary">
                    Clone a repository from {selectedProvider === 'github' ? 'GitHub' : 'GitLab'} to your workspace
                  </p>
                </div>
              </div>
              <div className="flex items-center gap-2">
                {/* Provider Toggle - only show if both providers are connected */}
                {isGitHubConnected && isGitLabConnected && (
                  <div className="flex items-center gap-1 bg-gitmesh-elements-background-depth-1 rounded-lg p-1">
                    <button
                      onClick={() => setSelectedProvider('github')}
                      className={`flex items-center gap-2 px-3 py-1.5 rounded-md text-sm font-medium transition-colors ${
                        selectedProvider === 'github'
                          ? 'bg-blue-500 text-white'
                          : 'text-gitmesh-elements-textSecondary hover:text-gitmesh-elements-textPrimary'
                      }`}
                    >
                      <Github className="w-4 h-4" />
                      GitHub
                    </button>
                    <button
                      onClick={() => setSelectedProvider('gitlab')}
                      className={`flex items-center gap-2 px-3 py-1.5 rounded-md text-sm font-medium transition-colors ${
                        selectedProvider === 'gitlab'
                          ? 'bg-orange-500 text-white'
                          : 'text-gitmesh-elements-textSecondary hover:text-gitmesh-elements-textPrimary'
                      }`}
                    >
                      <GitBranch className="w-4 h-4" />
                      GitLab
                    </button>
                  </div>
                )}
                <button
                  onClick={() => {
                    setIsDialogOpen(false);
                    setSelectedProvider(null);
                  }}
                  className="p-2 rounded-lg bg-transparent hover:bg-gitmesh-elements-background-depth-1 dark:hover:bg-gitmesh-elements-background-depth-1 text-gitmesh-elements-textSecondary dark:text-gitmesh-elements-textSecondary hover:text-gitmesh-elements-textPrimary dark:hover:text-gitmesh-elements-textPrimary transition-all duration-200 hover:scale-105 active:scale-95"
                >
                  <X className="w-5 h-5 transition-transform duration-200 hover:rotate-90" />
                </button>
              </div>
            </div>

            <div className="p-6 max-h-[calc(90vh-140px)] overflow-y-auto">
              {selectedProvider === 'github' ? (
                <GitHubRepositorySelector onClone={handleClone} />
              ) : (
                <GitLabRepositorySelector onClone={handleClone} />
              )}
            </div>
          </div>
        </div>
      )}

      {loading && <LoadingOverlay message="Please wait while we clone the repository..." />}
    </>
  );
}
