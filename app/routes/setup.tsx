import { useState, useEffect } from 'react';
import { useNavigate } from '@remix-run/react';
import { useStore } from '@nanostores/react';
import { motion, AnimatePresence } from 'framer-motion';
import { Button } from '~/components/ui/Button';
import { Input } from '~/components/ui/Input';
import { toast } from 'react-toastify';
import {
  githubConnectionStore,
  isGitHubConnected,
  isGitHubLoadingStats,
  githubConnectionAtom,
} from '~/lib/stores/githubConnection';
import { gitlabConnectionStore, isGitLabConnected } from '~/lib/stores/gitlabConnection';
import BackgroundRays from '~/components/ui/BackgroundRays';

export default function Setup() {
  const navigate = useNavigate();
  const [selectedIntegration, setSelectedIntegration] = useState<'github' | 'gitlab' | null>(null);
  const [token, setToken] = useState('');
  const [gitlabUrl, setGitlabUrl] = useState('https://gitlab.com');
  const [isConnecting, setIsConnecting] = useState(false);
  const [isLoadingData, setIsLoadingData] = useState(false);

  const isGithubConnected = useStore(isGitHubConnected);
  const isGitlabConnected = useStore(isGitLabConnected);
  const githubConnectionState = useStore(githubConnectionAtom);

  const hasAnyIntegration = isGithubConnected || isGitlabConnected;

  // If user already has integrations and data is ready, redirect to hub
  useEffect(() => {
    // Don't redirect if we're currently connecting or loading data
    if (isConnecting || isLoadingData) {
      return;
    }

    if (hasAnyIntegration) {
      // If GitHub is connected, check if we have basic user data
      if (isGithubConnected && githubConnectionState.user) {
        /*
         * We can navigate even if stats are still loading in background
         * Add timestamp to force refresh of overview page
         */
        navigate(`/hub/overview?t=${Date.now()}`, { replace: true });
      } else if (isGitlabConnected && !isGithubConnected) {
        // GitLab connected but not GitHub, can proceed
        navigate(`/hub/overview?t=${Date.now()}`, { replace: true });
      }
    }
  }, [
    hasAnyIntegration,
    isGithubConnected,
    isGitlabConnected,
    githubConnectionState.user,
    navigate,
    isConnecting,
    isLoadingData,
  ]);

  const handleConnect = async () => {
    if (!selectedIntegration || !token.trim()) {
      toast.error('Please enter a valid token');
      return;
    }

    setIsConnecting(true);
    setIsLoadingData(true);

    try {
      if (selectedIntegration === 'github') {
        // Connect to GitHub
        await githubConnectionStore.connect(token.trim());
        toast.success('Successfully connected to GitHub!');

        // Set a reasonable timeout for stats loading (10 seconds max)
        const timeout = setTimeout(() => {
          console.warn('GitHub stats loading timeout, proceeding to overview');
          setIsLoadingData(false);
        }, 10000);

        // Clear timeout if stats load quickly
        const checkStatsLoaded = () => {
          const currentConnection = githubConnectionAtom.get();
          const isStillFetching = isGitHubLoadingStats.get();

          if (currentConnection.user && (currentConnection.stats || !isStillFetching)) {
            clearTimeout(timeout);
            setIsLoadingData(false);
          }
        };

        // Check immediately and set up a brief interval
        checkStatsLoaded();

        const interval = setInterval(checkStatsLoaded, 500);

        // Clean up interval after timeout
        setTimeout(() => clearInterval(interval), 10000);
      } else if (selectedIntegration === 'gitlab') {
        await gitlabConnectionStore.connect(token.trim(), gitlabUrl.trim());
        toast.success('Successfully connected to GitLab!');
        setIsLoadingData(false);
      }

      // Reset form
      setToken('');
      setSelectedIntegration(null);

      // The navigation will happen via useEffect once data is ready
    } catch (error) {
      console.error('Connection failed:', error);
      toast.error(`Failed to connect: ${error instanceof Error ? error.message : 'Unknown error'}`);
      setIsLoadingData(false);
    } finally {
      setIsConnecting(false);
    }
  };

  const handleBack = () => {
    if (selectedIntegration) {
      setSelectedIntegration(null);
      setToken('');
    } else {
      navigate('/');
    }
  };

  const GitHubCard = () => (
    <motion.div
      whileHover={{ scale: 1.02 }}
      whileTap={{ scale: 0.98 }}
      onClick={() => setSelectedIntegration('github')}
      className="relative p-8 rounded-xl cursor-pointer transition-all duration-200 border-2 border-gitmesh-elements-borderColor hover:border-gitmesh-elements-borderColorActive bg-gitmesh-elements-background-depth-1"
    >
      <div className="flex flex-col items-center text-center space-y-6">
        <div className="w-16 h-16 bg-gray-900 dark:bg-white rounded-xl flex items-center justify-center">
          <svg viewBox="0 0 24 24" className="w-8 h-8 text-white dark:text-gray-900">
            <path
              fill="currentColor"
              d="M12 0c-6.626 0-12 5.373-12 12 0 5.302 3.438 9.8 8.207 11.387.599.111.793-.261.793-.577v-2.234c-3.338.726-4.033-1.416-4.033-1.416-.546-1.387-1.333-1.756-1.333-1.756-1.089-.745.083-.729.083-.729 1.205.084 1.839 1.237 1.839 1.237 1.07 1.834 2.807 1.304 3.492.997.107-.775.418-1.305.762-1.604-2.665-.305-5.467-1.334-5.467-5.931 0-1.311.469-2.381 1.236-3.221-.124-.303-.535-1.524.117-3.176 0 0 1.008-.322 3.301 1.23.957-.266 1.983-.399 3.003-.404 1.02.005 2.047.138 3.006.404 2.291-1.552 3.297-1.23 3.297-1.23.653 1.653.242 2.874.118 3.176.77.84 1.235 1.911 1.235 3.221 0 4.609-2.807 5.624-5.479 5.921.43.372.823 1.102.823 2.222v3.293c0 .319.192.694.801.576 4.765-1.589 8.199-6.086 8.199-11.386 0-6.627-5.373-12-12-12z"
            />
          </svg>
        </div>
        <div>
          <h3 className="text-2xl font-semibold text-gitmesh-elements-textPrimary mb-2">GitHub</h3>
          <p className="text-gitmesh-elements-textSecondary">
            Connect to GitHub for repository management, collaboration, and access to your projects.
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
      className="relative p-8 rounded-xl cursor-pointer transition-all duration-200 border-2 border-gitmesh-elements-borderColor hover:border-gitmesh-elements-borderColorActive bg-gitmesh-elements-background-depth-1"
    >
      <div className="flex flex-col items-center text-center space-y-6">
        <div className="w-16 h-16 bg-orange-500 rounded-xl flex items-center justify-center">
          <svg viewBox="0 0 24 24" className="w-8 h-8 text-white">
            <path
              fill="currentColor"
              d="M22.65 14.39L12 22.13 1.35 14.39a.84.84 0 0 1-.3-.94l1.22-3.78 2.44-7.51A.42.42 0 0 1 4.82 2a.43.43 0 0 1 .58 0 .42.42 0 0 1 .11.18l2.44 7.49h8.1l2.44-7.51A.42.42 0 0 1 18.6 2a.43.43 0 0 1 .58 0 .42.42 0 0 1 .11.18l2.44 7.51L23 13.45a.84.84 0 0 1-.35.94z"
            />
          </svg>
        </div>
        <div>
          <h3 className="text-2xl font-semibold text-gitmesh-elements-textPrimary mb-2">GitLab</h3>
          <p className="text-gitmesh-elements-textSecondary">
            Connect to GitLab for project management, DevOps integration, and CI/CD workflows.
          </p>
        </div>
      </div>
    </motion.div>
  );

  // Show loading screen while connecting or initially loading data
  if (isConnecting || isLoadingData) {
    return (
      <div className="min-h-screen bg-gitmesh-elements-background-depth-1 flex flex-col">
        <BackgroundRays />
        <main className="flex-1 flex items-center justify-center px-6 relative z-10">
          <div className="text-center space-y-6">
            <div className="w-16 h-16 mx-auto">
              <div className="w-16 h-16 border-4 border-gitmesh-elements-borderColor border-t-gitmesh-elements-button-primary-background rounded-full animate-spin"></div>
            </div>
            <div>
              <h2 className="text-2xl font-bold text-gitmesh-elements-textPrimary mb-2">Setting up your workspace</h2>
              <p className="text-gitmesh-elements-textSecondary">
                {isConnecting
                  ? `Connecting to ${selectedIntegration === 'github' ? 'GitHub' : selectedIntegration === 'gitlab' ? 'GitLab' : 'service'}...`
                  : isLoadingData
                    ? 'Fetching your data...'
                    : 'Loading your integrations...'}
              </p>
              <p className="text-sm text-gitmesh-elements-textSecondary mt-2">
                {isConnecting ? 'Authenticating with your credentials' : 'This should only take a few seconds'}
              </p>
            </div>
          </div>
        </main>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gitmesh-elements-background-depth-1 flex flex-col">
      <BackgroundRays />

      {/* Main Content */}
      <main className="flex-1 flex items-center justify-center px-6 relative z-10">
        <div className="w-full max-w-4xl">
          <AnimatePresence mode="wait">
            {!selectedIntegration ? (
              <motion.div
                key="selection"
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -20 }}
                className="text-center space-y-8"
              >
                <div>
                  <h2 className="text-4xl font-bold text-gitmesh-elements-textPrimary mb-4">
                    Connect Your First Integration
                  </h2>
                  <p className="text-xl text-gitmesh-elements-textSecondary max-w-2xl mx-auto">
                    Choose GitHub, GitLab, or both to get started with GitMesh Hub.
                  </p>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-8 max-w-4xl mx-auto">
                  <GitHubCard />
                  <GitLabCard />
                </div>
              </motion.div>
            ) : (
              <motion.div
                key="form"
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -20 }}
                className="max-w-2xl mx-auto"
              >
                <div className="bg-gitmesh-elements-background-depth-1 rounded-xl border border-gitmesh-elements-borderColor p-8">
                  <div className="text-center mb-8">
                    <div
                      className={`w-16 h-16 mx-auto mb-4 rounded-xl flex items-center justify-center ${
                        selectedIntegration === 'github' ? 'bg-gray-900 dark:bg-white' : 'bg-orange-500'
                      }`}
                    >
                      {selectedIntegration === 'github' ? (
                        <svg viewBox="0 0 24 24" className="w-8 h-8 text-white dark:text-gray-900">
                          <path
                            fill="currentColor"
                            d="M12 0c-6.626 0-12 5.373-12 12 0 5.302 3.438 9.8 8.207 11.387.599.111.793-.261.793-.577v-2.234c-3.338.726-4.033-1.416-4.033-1.416-.546-1.387-1.333-1.756-1.333-1.756-1.089-.745.083-.729.083-.729 1.205.084 1.839 1.237 1.839 1.237 1.07 1.834 2.807 1.304 3.492.997.107-.775.418-1.305.762-1.604-2.665-.305-5.467-1.334-5.467-5.931 0-1.311.469-2.381 1.236-3.221-.124-.303-.535-1.524.117-3.176 0 0 1.008-.322 3.301 1.23.957-.266 1.983-.399 3.003-.404 1.02.005 2.047.138 3.006.404 2.291-1.552 3.297-1.23 3.297-1.23.653 1.653.242 2.874.118 3.176.77.84 1.235 1.911 1.235 3.221 0 4.609-2.807 5.624-5.479 5.921.43.372.823 1.102.823 2.222v3.293c0 .319.192.694.801.576 4.765-1.589 8.199-6.086 8.199-11.386 0-6.627-5.373-12-12-12z"
                          />
                        </svg>
                      ) : (
                        <svg viewBox="0 0 24 24" className="w-8 h-8 text-white">
                          <path
                            fill="currentColor"
                            d="M22.65 14.39L12 22.13 1.35 14.39a.84.84 0 0 1-.3-.94l1.22-3.78 2.44-7.51A.42.42 0 0 1 4.82 2a.43.43 0 0 1 .58 0 .42.42 0 0 1 .11.18l2.44 7.49h8.1l2.44-7.51A.42.42 0 0 1 18.6 2a.43.43 0 0 1 .58 0 .42.42 0 0 1 .11.18l2.44 7.51L23 13.45a.84.84 0 0 1-.35.94z"
                          />
                        </svg>
                      )}
                    </div>
                    <h2 className="text-2xl font-bold text-gitmesh-elements-textPrimary mb-2">
                      Connect to {selectedIntegration === 'github' ? 'GitHub' : 'GitLab'}
                    </h2>
                    <p className="text-gitmesh-elements-textSecondary">
                      Enter your {selectedIntegration === 'github' ? 'GitHub' : 'GitLab'} access token to establish the
                      connection
                    </p>
                  </div>

                  <div className="space-y-6">
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
                        <p className="text-sm text-gitmesh-elements-textSecondary mt-2">
                          Use https://gitlab.com for GitLab.com or your self-hosted GitLab URL
                        </p>
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
                      <div className="mt-3 p-3 bg-gitmesh-elements-background-depth-1 rounded-lg">
                        <p className="text-sm font-medium text-gitmesh-elements-textPrimary mb-2">
                          How to create a token:
                        </p>
                        {selectedIntegration === 'github' ? (
                          <div className="text-sm text-gitmesh-elements-textSecondary space-y-1">
                            <p>1. Go to GitHub Settings → Developer settings → Personal access tokens</p>
                            <p>2. Click "Generate new token" → "Generate new token (classic)"</p>
                            <p>
                              3. Select scopes:{' '}
                              <code className="bg-gitmesh-elements-background-depth-1 px-1 rounded">repo</code>,{' '}
                              <code className="bg-gitmesh-elements-background-depth-1 px-1 rounded">user</code>,{' '}
                              <code className="bg-gitmesh-elements-background-depth-1 px-1 rounded">org</code>
                            </p>
                            <p>4. Copy the generated token and paste it above</p>
                          </div>
                        ) : (
                          <div className="text-sm text-gitmesh-elements-textSecondary space-y-1">
                            <p>1. Go to GitLab User Settings → Access Tokens</p>
                            <p>2. Create a new token with these scopes:</p>
                            <p>
                              3. Select scopes:{' '}
                              <code className="bg-gitmesh-elements-background-depth-1 px-1 rounded">api</code>,{' '}
                              <code className="bg-gitmesh-elements-background-depth-1 px-1 rounded">
                                read_repository
                              </code>
                            </p>
                            <p>4. Copy the generated token and paste it above</p>
                          </div>
                        )}
                      </div>
                    </div>

                    <div className="flex gap-3 pt-4">
                      <Button variant="outline" onClick={handleBack} className="flex-1">
                        Back
                      </Button>
                      <Button
                        variant="outline"
                        onClick={handleConnect}
                        disabled={!token.trim() || isConnecting}
                        className="flex-1"
                      >
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
                  </div>
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </main>

      {/* Footer */}
      <footer className="relative z-10 p-6 text-center">
        <p className="text-sm text-gitmesh-elements-textSecondary">
          Your tokens are stored securely and used only for GitMesh Hub functionality
        </p>
      </footer>
    </div>
  );
}
