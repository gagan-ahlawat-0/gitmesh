import { useState } from 'react';
import { useStore } from '@nanostores/react';
import { motion } from 'framer-motion';
import { Button } from '~/components/ui/Button';
import { toast } from 'react-toastify';
import GitHubTab from '~/components/@settings/tabs/github/GitHubTab';
import GitLabTab from '~/components/@settings/tabs/gitlab/GitLabTab';
import { githubConnectionStore, isGitHubConnected } from '~/lib/stores/githubConnection';
import { gitlabConnectionStore, isGitLabConnected } from '~/lib/stores/gitlabConnection';

type IntegrationType = 'github' | 'gitlab' | null;

export default function HubSettingsIntegrations() {
  const [selectedIntegration, setSelectedIntegration] = useState<IntegrationType>(null);
  const isGithubConnected = useStore(isGitHubConnected);
  const isGitlabConnected = useStore(isGitLabConnected);

  const handleDisconnect = async (type: 'github' | 'gitlab') => {
    const hasOtherConnection = type === 'github' ? isGitlabConnected : isGithubConnected;

    if (!hasOtherConnection) {
      toast.error('You must keep at least one integration connected.');
      return;
    }

    try {
      if (type === 'github') {
        githubConnectionStore.disconnect();
        toast.success('GitHub disconnected successfully');
      } else {
        gitlabConnectionStore.disconnect();
        toast.success('GitLab disconnected successfully');
      }
    } catch (error) {
      console.error('Failed to disconnect:', error);
      toast.error(`Failed to disconnect ${type}`);
    }
  };

  const IntegrationCard = ({
    type: _type,
    title,
    description,
    icon,
    isConnected,
    onConnect,
    onDisconnect,
  }: {
    type: 'github' | 'gitlab';
    title: string;
    description: string;
    icon: React.ReactNode;
    isConnected: boolean;
    onConnect: () => void;
    onDisconnect: () => void;
  }) => (
    <motion.div
      whileHover={{ scale: 1.01 }}
      className="bg-gitmesh-elements-background-depth-1 rounded-lg border border-gitmesh-elements-borderColor p-6"
    >
      <div className="flex items-start justify-between">
        <div className="flex items-center gap-4">
          <div className="w-12 h-12 rounded-lg bg-gitmesh-elements-background-depth-1 flex items-center justify-center">
            {icon}
          </div>
          <div>
            <h3 className="font-semibold text-gitmesh-elements-textPrimary">{title}</h3>
            <p className="text-sm text-gitmesh-elements-textSecondary mt-1">{description}</p>
            <div className="flex items-center gap-2 mt-2">
              <div className={`w-2 h-2 rounded-full ${isConnected ? 'bg-green-500' : 'bg-gray-400'}`} />
              <span className="text-xs text-gitmesh-elements-textSecondary">
                {isConnected ? 'Connected' : 'Not connected'}
              </span>
            </div>
          </div>
        </div>

        <div className="flex gap-2">
          {isConnected ? (
            <>
              <Button variant="outline" size="sm" onClick={onConnect}>
                Manage
              </Button>
              <Button
                variant="outline"
                size="sm"
                onClick={onDisconnect}
                className="text-red-600 hover:text-red-700 hover:border-red-300"
              >
                Disconnect
              </Button>
            </>
          ) : (
            <Button size="sm" 
            onClick={onConnect}
            className='text-gray-600 hover:text-gray-400'>
              Connect
            </Button>
          )}
        </div>
      </div>
    </motion.div>
  );

  if (selectedIntegration) {
    return (
      <div className="p-6">
        <div className="flex items-center gap-3 mb-6">
          <button
            onClick={() => setSelectedIntegration(null)}
            className="p-2 hover:bg-gitmesh-elements-background-depth-1 rounded-lg transition-colors"
          >
            <div className="i-ph:arrow-left w-5 h-5 text-gitmesh-elements-textSecondary" />
          </button>
          <h2 className="text-lg font-semibold text-gitmesh-elements-textPrimary">
            {selectedIntegration === 'github' ? 'GitHub' : 'GitLab'} Integration
          </h2>
        </div>

        {selectedIntegration === 'github' ? <GitHubTab /> : <GitLabTab />}
      </div>
    );
  }

  return (
    <div className="p-6">
      <div className="space-y-6">
        <div>
          <h2 className="text-lg font-semibold text-gitmesh-elements-textPrimary mb-2">Integration Management</h2>
          <p className="text-gitmesh-elements-textSecondary">
            Connect and manage your GitHub and GitLab integrations. You must keep at least one integration active.
          </p>
        </div>

        <div className="space-y-4">
          <IntegrationCard
            type="github"
            title="GitHub"
            description="Connect to GitHub for repository management and code collaboration"
            icon={
              <svg viewBox="0 0 24 24" className="w-6 h-6 text-gray-900 dark:text-white">
                <path
                  fill="currentColor"
                  d="M12 0c-6.626 0-12 5.373-12 12 0 5.302 3.438 9.8 8.207 11.387.599.111.793-.261.793-.577v-2.234c-3.338.726-4.033-1.416-4.033-1.416-.546-1.387-1.333-1.756-1.333-1.756-1.089-.745.083-.729.083-.729 1.205.084 1.839 1.237 1.839 1.237 1.07 1.834 2.807 1.304 3.492.997.107-.775.418-1.305.762-1.604-2.665-.305-5.467-1.334-5.467-5.931 0-1.311.469-2.381 1.236-3.221-.124-.303-.535-1.524.117-3.176 0 0 1.008-.322 3.301 1.23.957-.266 1.983-.399 3.003-.404 1.02.005 2.047.138 3.006.404 2.291-1.552 3.297-1.23 3.297-1.23.653 1.653.242 2.874.118 3.176.77.84 1.235 1.911 1.235 3.221 0 4.609-2.807 5.624-5.479 5.921.43.372.823 1.102.823 2.222v3.293c0 .319.192.694.801.576 4.765-1.589 8.199-6.086 8.199-11.386 0-6.627-5.373-12-12-12z"
                />
              </svg>
            }
            isConnected={isGithubConnected}
            onConnect={() => setSelectedIntegration('github')}
            onDisconnect={() => handleDisconnect('github')}
          />

          <IntegrationCard
            type="gitlab"
            title="GitLab"
            description="Connect to GitLab for project management and DevOps integration"
            icon={
              <svg viewBox="0 0 24 24" className="w-6 h-6 text-orange-500">
                <path
                  fill="currentColor"
                  d="M22.65 14.39L12 22.13 1.35 14.39a.84.84 0 0 1-.3-.94l1.22-3.78 2.44-7.51A.42.42 0 0 1 4.82 2a.43.43 0 0 1 .58 0 .42.42 0 0 1 .11.18l2.44 7.49h8.1l2.44-7.51A.42.42 0 0 1 18.6 2a.43.43 0 0 1 .58 0 .42.42 0 0 1 .11.18l2.44 7.51L23 13.45a.84.84 0 0 1-.35.94z"
                />
              </svg>
            }
            isConnected={isGitlabConnected}
            onConnect={() => setSelectedIntegration('gitlab')}
            onDisconnect={() => handleDisconnect('gitlab')}
          />
        </div>

        <div className="bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800 rounded-lg p-4">
          <div className="flex items-start gap-3">
            <div className="i-ph:warning w-5 h-5 text-yellow-600 dark:text-yellow-400 mt-0.5" />
            <div>
              <h4 className="font-medium text-yellow-800 dark:text-yellow-300">Important</h4>
              <p className="text-sm text-yellow-700 dark:text-yellow-400 mt-1">
                You must maintain at least one active integration (GitHub or GitLab) to continue using GitMesh Hub. You
                can have both connected simultaneously for enhanced functionality.
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
