import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import * as Dialog from '@radix-ui/react-dialog';
import { Button } from '~/components/ui/Button';
import { Input } from '~/components/ui/Input';
import { toast } from 'react-toastify';
import { githubConnectionStore } from '~/lib/stores/githubConnection';
import { gitlabConnectionStore } from '~/lib/stores/gitlabConnection';

interface IntegrationSelectionModalProps {
  isOpen: boolean;
  onClose: () => void;
  hasGitHub: boolean;
  hasGitLab: boolean;
}

export function IntegrationSelectionModal({ isOpen, onClose, hasGitHub, hasGitLab }: IntegrationSelectionModalProps) {
  const [selectedIntegration, setSelectedIntegration] = useState<'github' | 'gitlab' | null>(null);
  const [token, setToken] = useState('');
  const [gitlabUrl, setGitlabUrl] = useState('https://gitlab.com');
  const [isConnecting, setIsConnecting] = useState(false);

  const hasAnyIntegration = hasGitHub || hasGitLab;

  const handleConnect = async () => {
    if (!selectedIntegration || !token.trim()) {
      toast.error('Please enter a valid token');
      return;
    }

    setIsConnecting(true);

    try {
      if (selectedIntegration === 'github') {
        await githubConnectionStore.connect(token.trim());
        toast.success('Successfully connected to GitHub!');
      } else if (selectedIntegration === 'gitlab') {
        await gitlabConnectionStore.connect(token.trim(), gitlabUrl.trim());
        toast.success('Successfully connected to GitLab!');
      }

      // Reset form
      setToken('');
      setSelectedIntegration(null);

      // Close modal if this provides the first integration
      if (!hasAnyIntegration) {
        onClose();
      }
    } catch (error) {
      console.error('Connection failed:', error);
      toast.error(`Failed to connect: ${error instanceof Error ? error.message : 'Unknown error'}`);
    } finally {
      setIsConnecting(false);
    }
  };

  const handleCancel = () => {
    if (hasAnyIntegration) {
      onClose();
    } else {
      // If no integrations exist, they must connect at least one
      toast.warning('You must connect at least one integration to proceed.');
    }
  };

  const GitHubCard = () => (
    <motion.div
      whileHover={{ scale: 1.02 }}
      whileTap={{ scale: 0.98 }}
      onClick={() => setSelectedIntegration('github')}
      className={`
        relative p-6 rounded-xl cursor-pointer transition-all duration-200 border-2
        ${
          selectedIntegration === 'github'
            ? 'border-gitmesh-elements-button-primary-background bg-gitmesh-elements-button-primary-background/5'
            : 'border-gitmesh-elements-borderColor hover:border-gitmesh-elements-borderColorActive bg-gitmesh-elements-background-depth-1'
        }
      `}
    >
      {hasGitHub && (
        <div className="absolute top-3 right-3">
          <div className="flex items-center gap-1 px-2 py-1 bg-green-500/10 rounded-lg">
            <div className="i-ph:check-circle w-3 h-3 text-green-500" />
            <span className="text-xs text-green-600 dark:text-green-400">Connected</span>
          </div>
        </div>
      )}

      <div className="flex flex-col items-center text-center space-y-4">
        <div className="w-12 h-12 bg-gray-900 dark:bg-white rounded-lg flex items-center justify-center">
          <svg viewBox="0 0 24 24" className="w-6 h-6 text-white dark:text-gray-900">
            <path
              fill="currentColor"
              d="M12 0c-6.626 0-12 5.373-12 12 0 5.302 3.438 9.8 8.207 11.387.599.111.793-.261.793-.577v-2.234c-3.338.726-4.033-1.416-4.033-1.416-.546-1.387-1.333-1.756-1.333-1.756-1.089-.745.083-.729.083-.729 1.205.084 1.839 1.237 1.839 1.237 1.07 1.834 2.807 1.304 3.492.997.107-.775.418-1.305.762-1.604-2.665-.305-5.467-1.334-5.467-5.931 0-1.311.469-2.381 1.236-3.221-.124-.303-.535-1.524.117-3.176 0 0 1.008-.322 3.301 1.23.957-.266 1.983-.399 3.003-.404 1.02.005 2.047.138 3.006.404 2.291-1.552 3.297-1.23 3.297-1.23.653 1.653.242 2.874.118 3.176.77.84 1.235 1.911 1.235 3.221 0 4.609-2.807 5.624-5.479 5.921.43.372.823 1.102.823 2.222v3.293c0 .319.192.694.801.576 4.765-1.589 8.199-6.086 8.199-11.386 0-6.627-5.373-12-12-12z"
            />
          </svg>
        </div>
        <div>
          <h3 className="text-lg font-semibold text-gitmesh-elements-textPrimary">GitHub</h3>
          <p className="text-sm text-gitmesh-elements-textSecondary mt-1">
            Connect to GitHub for repository management and code collaboration
          </p>
        </div>
      </div>
    </motion.div>
  );

  const GitLabCard = () => (
    <motion.div
      whileHover={{ scale: 1.02 }}
      whileTap={{ scale: 0.98 }}
      onClick={() => setSelectedIntegration('gitlab')}
      className={`
        relative p-6 rounded-xl cursor-pointer transition-all duration-200 border-2
        ${
          selectedIntegration === 'gitlab'
            ? 'border-orange-500 bg-orange-500/5'
            : 'border-gitmesh-elements-borderColor hover:border-gitmesh-elements-borderColorActive bg-gitmesh-elements-background-depth-1'
        }
      `}
    >
      {hasGitLab && (
        <div className="absolute top-3 right-3">
          <div className="flex items-center gap-1 px-2 py-1 bg-green-500/10 rounded-lg">
            <div className="i-ph:check-circle w-3 h-3 text-green-500" />
            <span className="text-xs text-green-600 dark:text-green-400">Connected</span>
          </div>
        </div>
      )}

      <div className="flex flex-col items-center text-center space-y-4">
        <div className="w-12 h-12 bg-orange-500 rounded-lg flex items-center justify-center">
          <svg viewBox="0 0 24 24" className="w-6 h-6 text-white">
            <path
              fill="currentColor"
              d="M22.65 14.39L12 22.13 1.35 14.39a.84.84 0 0 1-.3-.94l1.22-3.78 2.44-7.51A.42.42 0 0 1 4.82 2a.43.43 0 0 1 .58 0 .42.42 0 0 1 .11.18l2.44 7.49h8.1l2.44-7.51A.42.42 0 0 1 18.6 2a.43.43 0 0 1 .58 0 .42.42 0 0 1 .11.18l2.44 7.51L23 13.45a.84.84 0 0 1-.35.94z"
            />
          </svg>
        </div>
        <div>
          <h3 className="text-lg font-semibold text-gitmesh-elements-textPrimary">GitLab</h3>
          <p className="text-sm text-gitmesh-elements-textSecondary mt-1">
            Connect to GitLab for project management and DevOps integration
          </p>
        </div>
      </div>
    </motion.div>
  );

  return (
    <Dialog.Root open={isOpen} onOpenChange={() => {}}>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 bg-black/50 z-50" />
        <Dialog.Content className="fixed top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2 z-50 w-full max-w-2xl">
          <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 0.95 }}
            className="bg-gitmesh-elements-background-depth-1 rounded-xl border border-gitmesh-elements-borderColor shadow-2xl p-8"
          >
            <div className="text-center mb-8">
              <Dialog.Title className="text-2xl font-bold text-gitmesh-elements-textPrimary mb-2">
                {hasAnyIntegration ? 'Manage Integrations' : 'Connect Your First Integration'}
              </Dialog.Title>
              <Dialog.Description className="text-gitmesh-elements-textSecondary">
                {hasAnyIntegration
                  ? 'Add additional integrations or manage existing connections.'
                  : 'You need at least one integration to use GitMesh Hub. Choose GitHub, GitLab, or both.'}
              </Dialog.Description>
            </div>

            <AnimatePresence mode="wait">
              {!selectedIntegration ? (
                <motion.div
                  key="selection"
                  initial={{ opacity: 0, x: -20 }}
                  animate={{ opacity: 1, x: 0 }}
                  exit={{ opacity: 0, x: 20 }}
                  className="space-y-6"
                >
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <GitHubCard />
                    <GitLabCard />
                  </div>

                  {hasAnyIntegration && (
                    <div className="flex justify-center">
                      <Button variant="outline" onClick={onClose}>
                        Cancel
                      </Button>
                    </div>
                  )}
                </motion.div>
              ) : (
                <motion.div
                  key="form"
                  initial={{ opacity: 0, x: 20 }}
                  animate={{ opacity: 1, x: 0 }}
                  exit={{ opacity: 0, x: -20 }}
                  className="space-y-6"
                >
                  <div className="flex items-center gap-3 mb-6">
                    <button
                      onClick={() => setSelectedIntegration(null)}
                      className="p-2 hover:bg-gitmesh-elements-background-depth-1 rounded-lg transition-colors"
                    >
                      <div className="i-ph:arrow-left w-5 h-5 text-gitmesh-elements-textSecondary" />
                    </button>
                    <h3 className="text-lg font-semibold text-gitmesh-elements-textPrimary">
                      Connect to {selectedIntegration === 'github' ? 'GitHub' : 'GitLab'}
                    </h3>
                  </div>

                  <div className="space-y-4">
                    {selectedIntegration === 'gitlab' && (
                      <div>
                        <label className="block text-sm font-medium text-gitmesh-elements-textPrimary mb-2">
                          GitLab URL
                        </label>
                        <Input
                          type="url"
                          value={gitlabUrl}
                          onChange={(e) => setGitlabUrl(e.target.value)}
                          placeholder="https://gitlab.com"
                          className="w-full"
                        />
                      </div>
                    )}

                    <div>
                      <label className="block text-sm font-medium text-gitmesh-elements-textPrimary mb-2">
                        {selectedIntegration === 'github' ? 'GitHub' : 'GitLab'} Access Token
                      </label>
                      <Input
                        type="password"
                        value={token}
                        onChange={(e) => setToken(e.target.value)}
                        placeholder={`Enter your ${selectedIntegration === 'github' ? 'GitHub' : 'GitLab'} token`}
                        className="w-full"
                      />
                      <p className="text-sm text-gitmesh-elements-textSecondary mt-2">
                        {selectedIntegration === 'github'
                          ? 'Create a token at GitHub Settings > Developer settings > Personal access tokens'
                          : 'Create a token at GitLab User Settings > Access Tokens'}
                      </p>
                    </div>
                  </div>

                  <div className="flex gap-3 justify-end">
                    <Button variant="outline" onClick={handleCancel}>
                      Cancel
                    </Button>
                    <Button onClick={handleConnect} disabled={!token.trim() || isConnecting}>
                      {isConnecting ? (
                        <>
                          <div className="i-ph:spinner-gap animate-spin w-4 h-4 mr-2" />
                          Connecting...
                        </>
                      ) : (
                        'Connect'
                      )}
                    </Button>
                  </div>
                </motion.div>
              )}
            </AnimatePresence>
          </motion.div>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}
