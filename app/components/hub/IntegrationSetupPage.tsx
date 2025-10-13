import { useState } from 'react';
import { motion } from 'framer-motion';
import { useStore } from '@nanostores/react';
import { Button } from '~/components/ui/Button';
import { Input } from '~/components/ui/Input';
import { toast } from 'react-toastify';
import { useGitHubConnection } from '~/lib/hooks/useGitHubConnection';
import { useGitLabConnection } from '~/lib/hooks/useGitLabConnection';
import { isGitHubConnected } from '~/lib/stores/githubConnection';
import { isGitLabConnected } from '~/lib/stores/gitlabConnection';
import BackgroundRays from '~/components/ui/BackgroundRays';

interface IntegrationCardProps {
  type: 'github' | 'gitlab';
  title: string;
  description: string;
  icon: React.ReactNode;
  isConnected: boolean;
  isConnecting: boolean;
  onConnect: (token: string, url?: string) => Promise<void>;
  tokenPlaceholder: string;
  tokenHelp: string;
  showUrlField?: boolean;
}

function IntegrationCard({
  type: _type,
  title,
  description,
  icon,
  isConnected,
  isConnecting,
  onConnect,
  tokenPlaceholder,
  tokenHelp,
  showUrlField = false,
}: IntegrationCardProps) {
  const [token, setToken] = useState('');
  const [url, setUrl] = useState('https://gitlab.com');
  const [showForm, setShowForm] = useState(false);

  const handleConnect = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!token.trim()) {
      toast.error('Please enter a valid token');
      return;
    }

    try {
      await onConnect(token.trim(), showUrlField ? url.trim() : undefined);
      setToken('');
      setShowForm(false);
      toast.success(`Successfully connected to ${title}!`);
    } catch (error) {
      console.error(`${title} connection failed:`, error);
      toast.error(`Failed to connect to ${title}: ${error instanceof Error ? error.message : 'Unknown error'}`);
    }
  };

  if (isConnected) {
    return (
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="bg-gitmesh-elements-background-depth-1 rounded-xl border-2 border-green-500/30 p-6 relative"
      >
        <div className="absolute top-4 right-4">
          <div className="flex items-center gap-2 px-3 py-1 bg-green-500/10 rounded-lg">
            <div className="i-ph:check-circle w-4 h-4 text-green-500" />
            <span className="text-sm text-green-600 dark:text-green-400 font-medium">Connected</span>
          </div>
        </div>

        <div className="flex items-center gap-4">
          <div className="w-16 h-16 rounded-xl bg-gitmesh-elements-background-depth-1 flex items-center justify-center">
            {icon}
          </div>
          <div>
            <h3 className="text-xl font-semibold text-gitmesh-elements-textPrimary">{title}</h3>
            <p className="text-gitmesh-elements-textSecondary mt-1">{description}</p>
            <p className="text-sm text-green-600 dark:text-green-400 mt-2">
              ✓ Successfully integrated and ready to use
            </p>
          </div>
        </div>
      </motion.div>
    );
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="bg-gitmesh-elements-background-depth-1 rounded-xl border border-gitmesh-elements-borderColor p-6 hover:border-gitmesh-elements-borderColorActive transition-all duration-200"
    >
      <div className="flex items-center gap-4 mb-4">
        <div className="w-16 h-16 rounded-xl bg-gitmesh-elements-background-depth-1 flex items-center justify-center">
          {icon}
        </div>
        <div className="flex-1">
          <h3 className="text-xl font-semibold text-gitmesh-elements-textPrimary">{title}</h3>
          <p className="text-gitmesh-elements-textSecondary mt-1">{description}</p>
        </div>
      </div>

      {!showForm ? (
        <Button onClick={() => setShowForm(true)} className="w-full">
          Connect to {title}
        </Button>
      ) : (
        <form onSubmit={handleConnect} className="space-y-4">
          {showUrlField && (
            <div>
              <label className="block text-sm font-medium text-gitmesh-elements-textPrimary mb-2">GitLab URL</label>
              <Input
                type="url"
                value={url}
                onChange={(e) => setUrl(e.target.value)}
                placeholder="https://gitlab.com"
                className="w-full"
              />
              <p className="text-xs text-gitmesh-elements-textSecondary mt-1">
                Enter your GitLab instance URL (leave default for GitLab.com)
              </p>
            </div>
          )}

          <div>
            <label className="block text-sm font-medium text-gitmesh-elements-textPrimary mb-2">
              {title} Access Token
            </label>
            <Input
              type="password"
              value={token}
              onChange={(e) => setToken(e.target.value)}
              placeholder={tokenPlaceholder}
              className="w-full"
            />
            <p className="text-xs text-gitmesh-elements-textSecondary mt-1">{tokenHelp}</p>
          </div>

          <div className="flex gap-3">
            <Button
              type="button"
              variant="outline"
              onClick={() => {
                setShowForm(false);
                setToken('');
              }}
              className="flex-1"
            >
              Cancel
            </Button>
            <Button type="submit" disabled={!token.trim() || isConnecting} className="flex-1">
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
        </form>
      )}
    </motion.div>
  );
}

export function IntegrationSetupPage() {
  const isGithubConnected = useStore(isGitHubConnected);
  const isGitlabConnected = useStore(isGitLabConnected);

  const { connect: connectGitHub, isConnecting: isConnectingGitHub } = useGitHubConnection();
  const { connect: connectGitLab, isConnecting: isConnectingGitLab } = useGitLabConnection();

  const hasAnyIntegration = isGithubConnected || isGitlabConnected;

  const handleGitHubConnect = async (token: string) => {
    await connectGitHub(token, 'classic');
  };

  const handleGitLabConnect = async (token: string, url?: string) => {
    await connectGitLab(token, url || 'https://gitlab.com');
  };

  if (hasAnyIntegration) {
    return (
      <div className="min-h-screen bg-gitmesh-elements-background-depth-1 flex flex-col items-center justify-center p-6">
        <BackgroundRays />

        <motion.div
          initial={{ opacity: 0, scale: 0.95 }}
          animate={{ opacity: 1, scale: 1 }}
          className="text-center space-y-6 relative z-10"
        >
          <div className="w-16 h-16 mx-auto bg-green-500 rounded-full flex items-center justify-center">
            <div className="i-ph:check w-8 h-8 text-white" />
          </div>
          <div>
            <h1 className="text-3xl font-bold text-gitmesh-elements-textPrimary mb-2">Welcome to GitMesh Hub!</h1>
            <p className="text-gitmesh-elements-textSecondary">
              Your integrations are set up. Redirecting to the overview page...
            </p>
          </div>
        </motion.div>

        <script
          dangerouslySetInnerHTML={{
            __html: `setTimeout(() => window.location.href = '/hub/overview', 2000);`,
          }}
        />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gitmesh-elements-background-depth-1 flex flex-col">
      <BackgroundRays />

      <div className="flex-1 flex flex-col items-center justify-center p-6">
        <div className="w-full max-w-4xl relative z-10">
          {/* Header */}
          <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="text-center mb-12">
            <div className="w-20 h-20 mx-auto mb-6 bg-gradient-to-br from-gitmesh-elements-button-primary-background to-gitmesh-elements-button-primary-backgroundHover rounded-2xl flex items-center justify-center">
              <div className="i-ph:git-branch-duotone text-white text-2xl" />
            </div>
            <h1 className="text-4xl font-bold text-gitmesh-elements-textPrimary mb-4">Welcome to GitMesh Hub</h1>
            <p className="text-xl text-gitmesh-elements-textSecondary max-w-2xl mx-auto">
              Connect your Git platforms to get started. You need at least one integration (GitHub or GitLab) to
              continue.
            </p>
          </motion.div>

          {/* Integration Cards */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-8 mb-8">
            <IntegrationCard
              type="github"
              title="GitHub"
              description="Connect to GitHub for repository management and code collaboration"
              icon={
                <svg viewBox="0 0 24 24" className="w-8 h-8 text-gray-900 dark:text-white">
                  <path
                    fill="currentColor"
                    d="M12 0c-6.626 0-12 5.373-12 12 0 5.302 3.438 9.8 8.207 11.387.599.111.793-.261.793-.577v-2.234c-3.338.726-4.033-1.416-4.033-1.416-.546-1.387-1.333-1.756-1.333-1.756-1.089-.745.083-.729.083-.729 1.205.084 1.839 1.237 1.839 1.237 1.07 1.834 2.807 1.304 3.492.997.107-.775.418-1.305.762-1.604-2.665-.305-5.467-1.334-5.467-5.931 0-1.311.469-2.381 1.236-3.221-.124-.303-.535-1.524.117-3.176 0 0 1.008-.322 3.301 1.23.957-.266 1.983-.399 3.003-.404 1.02.005 2.047.138 3.006.404 2.291-1.552 3.297-1.23 3.297-1.23.653 1.653.242 2.874.118 3.176.77.84 1.235 1.911 1.235 3.221 0 4.609-2.807 5.624-5.479 5.921.43.372.823 1.102.823 2.222v3.293c0 .319.192.694.801.576 4.765-1.589 8.199-6.086 8.199-11.386 0-6.627-5.373-12-12-12z"
                  />
                </svg>
              }
              isConnected={isGithubConnected}
              isConnecting={isConnectingGitHub}
              onConnect={handleGitHubConnect}
              tokenPlaceholder="ghp_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
              tokenHelp="Create a token at GitHub Settings > Developer settings > Personal access tokens. Requires 'repo' scope."
            />

            <IntegrationCard
              type="gitlab"
              title="GitLab"
              description="Connect to GitLab for project management and DevOps integration"
              icon={
                <svg viewBox="0 0 24 24" className="w-8 h-8 text-orange-500">
                  <path
                    fill="currentColor"
                    d="M22.65 14.39L12 22.13 1.35 14.39a.84.84 0 0 1-.3-.94l1.22-3.78 2.44-7.51A.42.42 0 0 1 4.82 2a.43.43 0 0 1 .58 0 .42.42 0 0 1 .11.18l2.44 7.49h8.1l2.44-7.51A.42.42 0 0 1 18.6 2a.43.43 0 0 1 .58 0 .42.42 0 0 1 .11.18l2.44 7.51L23 13.45a.84.84 0 0 1-.35.94z"
                  />
                </svg>
              }
              isConnected={isGitlabConnected}
              isConnecting={isConnectingGitLab}
              onConnect={handleGitLabConnect}
              tokenPlaceholder="glpat-xxxxxxxxxxxxxxxxxxxx"
              tokenHelp="Create a token at GitLab User Settings > Access Tokens. Requires 'api' and 'read_repository' scopes."
              showUrlField={true}
            />
          </div>

          {/* Requirements Notice */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.3 }}
            className="bg-gitmesh-elements-background-depth-1 rounded-xl border border-gitmesh-elements-borderColor p-6"
          >
            <div className="flex items-start gap-4">
              <div className="w-10 h-10 bg-blue-500/10 rounded-lg flex items-center justify-center flex-shrink-0">
                <div className="i-ph:info w-5 h-5 text-blue-500" />
              </div>
              <div>
                <h3 className="font-medium text-gitmesh-elements-textPrimary mb-2">Requirements</h3>
                <ul className="space-y-2 text-sm text-gitmesh-elements-textSecondary">
                  <li className="flex items-center gap-2">
                    <div className="i-ph:check w-4 h-4 text-green-500" />
                    You must connect at least one Git platform (GitHub or GitLab)
                  </li>
                  <li className="flex items-center gap-2">
                    <div className="i-ph:check w-4 h-4 text-green-500" />
                    Both platforms can be connected for enhanced functionality
                  </li>
                  <li className="flex items-center gap-2">
                    <div className="i-ph:check w-4 h-4 text-green-500" />
                    Access tokens are stored securely and never shared
                  </li>
                  <li className="flex items-center gap-2">
                    <div className="i-ph:check w-4 h-4 text-green-500" />
                    You can manage connections in Settings after setup
                  </li>
                </ul>
              </div>
            </div>
          </motion.div>
        </div>
      </div>
    </div>
  );
}
