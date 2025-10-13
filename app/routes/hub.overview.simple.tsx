import React, { useMemo } from 'react';
import { motion } from 'framer-motion';
import { useStore } from '@nanostores/react';
import { Button } from '~/components/ui/Button';
import { Link } from '@remix-run/react';
import { useGitHubConnection, useGitHubStats, useGitLabConnection } from '~/lib/hooks';
import { isGitHubConnected } from '~/lib/stores/githubConnection';
import { isGitLabConnected } from '~/lib/stores/gitlabConnection';

export default function HubOverviewSimple() {
  const isGithubConnected = useStore(isGitHubConnected);
  const isGitlabConnected = useStore(isGitLabConnected);

  const { connection: githubConnection } = useGitHubConnection();
  const { connection: gitlabConnection } = useGitLabConnection();

  const {
    stats: githubStats,
    isLoading: isGithubLoading,
    error: githubError,
  } = useGitHubStats(githubConnection, {
    autoFetch: true,
    cacheTimeout: 5 * 60 * 1000, // 5 minutes cache to reduce API calls
  });

  // Simple aggregated stats
  const aggregatedStats = useMemo(() => {
    let totalRepos = 0;
    let totalStars = 0;

    // GitHub Stats - use fallback values if stats are not loaded yet
    if (githubStats && !githubError) {
      totalRepos += (githubStats.publicRepos || 0) + (githubStats.privateRepos || 0);
      totalStars += githubStats.totalStars || 0;
    } else if (githubConnection?.user && !githubStats && !isGithubLoading) {
      // Fallback to basic user data if detailed stats failed
      totalRepos += githubConnection.user.public_repos || 0;
    }

    // GitLab Stats
    if (gitlabConnection?.stats) {
      totalRepos += (gitlabConnection.stats.publicProjects || 0) + (gitlabConnection.stats.privateProjects || 0);
      totalStars += gitlabConnection.stats.stars || 0;
    }

    return { totalRepos, totalStars };
  }, [githubStats, githubError, githubConnection?.user, isGithubLoading, gitlabConnection?.stats]);

  const hasAnyConnection = isGithubConnected || isGitlabConnected;

  return (
    <div className="p-8">
      <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="mb-8">
        <h1 className="text-3xl font-bold text-gitmesh-elements-textPrimary mb-4">Hub Overview</h1>
        <p className="text-gitmesh-elements-textSecondary">
          {hasAnyConnection
            ? 'Your repository statistics across all connected platforms.'
            : 'Welcome to GitMesh Hub! Connect your accounts to get started.'}
        </p>
        {/* Show loading or error state for GitHub stats */}
        {isGithubConnected && (
          <div className="mt-2">
            {isGithubLoading && (
              <p className="text-sm text-gitmesh-elements-textSecondary flex items-center">
                <div className="i-ph:spinner-gap animate-spin w-4 h-4 mr-2" />
                Loading GitHub statistics...
              </p>
            )}
            {githubError && (
              <p className="text-sm text-red-500 flex items-center">
                <div className="i-ph:warning w-4 h-4 mr-2" />
                Error loading GitHub stats: {githubError}
              </p>
            )}
          </div>
        )}
      </motion.div>

      {!hasAnyConnection ? (
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
          className="bg-gitmesh-elements-background-depth-1 rounded-lg border border-gitmesh-elements-borderColor p-8 text-center"
        >
          <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-gitmesh-elements-button-primary-background/10 flex items-center justify-center">
            <div className="i-ph:plugs w-8 h-8 text-gitmesh-elements-button-primary-background" />
          </div>
          <h2 className="text-xl font-semibold text-gitmesh-elements-textPrimary mb-2">No Integrations Connected</h2>
          <p className="text-gitmesh-elements-textSecondary mb-6">
            Connect GitHub or GitLab to start using GitMesh Hub.
          </p>
          <Link to="/hub/settings/integrations">
            <Button>
              <div className="i-ph:plug w-4 h-4 mr-2" />
              Connect Integrations
            </Button>
          </Link>
        </motion.div>
      ) : (
        <>
          {/* Simple Stats Cards */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.1 }}
            className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-8"
          >
            <div className="bg-gitmesh-elements-background-depth-1 rounded-lg border border-gitmesh-elements-borderColor p-6">
              <div className="flex items-center gap-4">
                <div className="p-3 rounded-lg bg-blue-500">
                  <div className="i-ph:folder w-6 h-6 text-white" />
                </div>
                <div>
                  <p className="text-sm text-gitmesh-elements-textSecondary">Total Repositories</p>
                  <p className="text-2xl font-bold text-gitmesh-elements-textPrimary">
                    {isGithubLoading ? '...' : aggregatedStats.totalRepos.toLocaleString()}
                  </p>
                </div>
              </div>
            </div>

            <div className="bg-gitmesh-elements-background-depth-1 rounded-lg border border-gitmesh-elements-borderColor p-6">
              <div className="flex items-center gap-4">
                <div className="p-3 rounded-lg bg-yellow-500">
                  <div className="i-ph:star w-6 h-6 text-white" />
                </div>
                <div>
                  <p className="text-sm text-gitmesh-elements-textSecondary">Total Stars</p>
                  <p className="text-2xl font-bold text-gitmesh-elements-textPrimary">
                    {isGithubLoading ? '...' : aggregatedStats.totalStars.toLocaleString()}
                  </p>
                </div>
              </div>
            </div>
          </motion.div>

          {/* Connected Platforms */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.2 }}
            className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-8"
          >
            {isGithubConnected && (
              <div className="bg-gitmesh-elements-background-depth-1 rounded-lg border border-gitmesh-elements-borderColor p-6">
                <div className="flex items-center gap-3 mb-3">
                  <div className="w-8 h-8 rounded-lg bg-gray-900 flex items-center justify-center">
                    <svg viewBox="0 0 24 24" className="w-5 h-5 text-white">
                      <path
                        fill="currentColor"
                        d="M12 0c-6.626 0-12 5.373-12 12 0 5.302 3.438 9.8 8.207 11.387.599.111.793-.261.793-.577v-2.234c-3.338.726-4.033-1.416-4.033-1.416-.546-1.387-1.333-1.756-1.333-1.756-1.089-.745.083-.729.083-.729 1.205.084 1.839 1.237 1.839 1.237 1.07 1.834 2.807 1.304 3.492.997.107-.775.418-1.305.762-1.604-2.665-.305-5.467-1.334-5.467-5.931 0-1.311.469-2.381 1.236-3.221-.124-.303-.535-1.524.117-3.176 0 0 1.008-.322 3.301 1.23.957-.266 1.983-.399 3.003-.404 1.02.005 2.047.138 3.006.404 2.291-1.552 3.297-1.23 3.297-1.23.653 1.653.242 2.874.118 3.176.77.84 1.235 1.911 1.235 3.221 0 4.609-2.807 5.624-5.479 5.921.43.372.823 1.102.823 2.222v3.293c0 .319.192.694.801.576 4.765-1.589 8.199-6.086 8.199-11.386 0-6.627-5.373-12-12-12z"
                      />
                    </svg>
                  </div>
                  <div>
                    <h3 className="font-semibold text-gitmesh-elements-textPrimary">GitHub</h3>
                    <p className="text-sm text-gitmesh-elements-textSecondary">Connected</p>
                  </div>
                </div>
                {githubConnection?.user && (
                  <p className="text-sm text-gitmesh-elements-textSecondary">
                    Logged in as{' '}
                    <span className="text-gitmesh-elements-textPrimary">{githubConnection.user.login}</span>
                  </p>
                )}
              </div>
            )}

            {isGitlabConnected && (
              <div className="bg-gitmesh-elements-background-depth-1 rounded-lg border border-gitmesh-elements-borderColor p-6">
                <div className="flex items-center gap-3 mb-3">
                  <div className="w-8 h-8 rounded-lg bg-orange-500 flex items-center justify-center">
                    <svg viewBox="0 0 24 24" className="w-5 h-5 text-white">
                      <path
                        fill="currentColor"
                        d="M22.65 14.39L12 22.13 1.35 14.39a.84.84 0 0 1-.3-.94l1.22-3.78 2.44-7.51A.42.42 0 0 1 4.82 2a.43.43 0 0 1 .58 0 .42.42 0 0 1 .11.18l2.44 7.49h8.1l2.44-7.51A.42.42 0 0 1 18.6 2a.43.43 0 0 1 .58 0 .42.42 0 0 1 .11.18l2.44 7.51L23 13.45a.84.84 0 0 1-.35.94z"
                      />
                    </svg>
                  </div>
                  <div>
                    <h3 className="font-semibold text-gitmesh-elements-textPrimary">GitLab</h3>
                    <p className="text-sm text-gitmesh-elements-textSecondary">Connected</p>
                  </div>
                </div>
                {gitlabConnection?.user && (
                  <p className="text-sm text-gitmesh-elements-textSecondary">
                    Logged in as{' '}
                    <span className="text-gitmesh-elements-textPrimary">{gitlabConnection.user.username}</span>
                  </p>
                )}
              </div>
            )}
          </motion.div>

          {/* Quick Actions */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.3 }}
            className="bg-gitmesh-elements-background-depth-1 rounded-lg border border-gitmesh-elements-borderColor p-6"
          >
            <h2 className="text-lg font-semibold text-gitmesh-elements-textPrimary mb-4">Quick Actions</h2>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <Link to="/hub/projects">
                <Button variant="outline" className="w-full justify-start">
                  <div className="i-ph:folder w-4 h-4 mr-2" />
                  View Projects
                </Button>
              </Link>
              <Link to="/hub/settings/integrations">
                <Button variant="outline" className="w-full justify-start">
                  <div className="i-ph:gear w-4 h-4 mr-2" />
                  Settings
                </Button>
              </Link>
              <Button variant="outline" className="w-full justify-start" onClick={() => window.location.reload()}>
                <div className="i-ph:arrows-clockwise w-4 h-4 mr-2" />
                Refresh
              </Button>
            </div>
          </motion.div>
        </>
      )}
    </div>
  );
}
