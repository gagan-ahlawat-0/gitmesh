import { useState, useEffect } from 'react';
import { useSearchParams, useNavigate } from '@remix-run/react';

interface RepoInfo {
  cloneUrl: string;
  repoName: string;
  repoFullName: string;
  provider: 'github' | 'gitlab';
  fromHub: boolean;
}

const REPO_STORAGE_KEY = 'gitmesh-repo-context';

export function usePersistedRepoContext() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const [repoInfo, setRepoInfo] = useState<RepoInfo | null>(null);

  // Extract repository information from search params
  const urlCloneUrl = searchParams.get('clone');
  const urlRepoName = searchParams.get('repo');
  const urlRepoFullName = searchParams.get('fullName');
  const urlProvider = searchParams.get('provider') as 'github' | 'gitlab' | null;
  const urlFromHub = searchParams.get('from') === 'hub';

  useEffect(() => {
    // Priority: URL params > localStorage > null
    if (urlCloneUrl && urlRepoName && urlRepoFullName && urlProvider) {
      // We have URL params - use them and store for future
      const newRepoInfo: RepoInfo = {
        cloneUrl: urlCloneUrl,
        repoName: urlRepoName,
        repoFullName: urlRepoFullName,
        provider: urlProvider,
        fromHub: urlFromHub,
      };

      setRepoInfo(newRepoInfo);

      // Persist to localStorage
      try {
        localStorage.setItem(REPO_STORAGE_KEY, JSON.stringify(newRepoInfo));
      } catch (error) {
        console.warn('Failed to persist repo context:', error);
      }
    } else {
      // No URL params - try to restore from localStorage
      try {
        const stored = localStorage.getItem(REPO_STORAGE_KEY);

        if (stored) {
          const parsedRepoInfo: RepoInfo = JSON.parse(stored);
          setRepoInfo(parsedRepoInfo);

          // Update URL to reflect the restored state (without triggering navigation)
          const currentUrl = new URL(window.location.href);
          currentUrl.searchParams.set('clone', parsedRepoInfo.cloneUrl);
          currentUrl.searchParams.set('repo', parsedRepoInfo.repoName);
          currentUrl.searchParams.set('fullName', parsedRepoInfo.repoFullName);
          currentUrl.searchParams.set('provider', parsedRepoInfo.provider);

          if (parsedRepoInfo.fromHub) {
            currentUrl.searchParams.set('from', 'hub');
          }

          // Update URL without causing a reload
          window.history.replaceState({}, '', currentUrl.toString());
        }
      } catch (error) {
        console.warn('Failed to restore repo context:', error);
      }
    }
  }, [urlCloneUrl, urlRepoName, urlRepoFullName, urlProvider, urlFromHub]);

  const clearRepoContext = () => {
    setRepoInfo(null);

    try {
      localStorage.removeItem(REPO_STORAGE_KEY);
    } catch (error) {
      console.warn('Failed to clear repo context:', error);
    }

    // Navigate to clean chat page
    navigate('/chat');
  };

  // Transform to the format expected by RepoProvider
  const selectedRepo = repoInfo
    ? {
        clone_url: repoInfo.cloneUrl,
        name: repoInfo.repoName,
        full_name: repoInfo.repoFullName,
        provider: repoInfo.provider,
      }
    : undefined;

  return {
    selectedRepo,
    fromHub: repoInfo?.fromHub ?? false,
    clearRepoContext,
  };
}
