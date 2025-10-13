import { json, type MetaFunction } from '@remix-run/cloudflare';
import { useEffect } from 'react';
import { useStore } from '@nanostores/react';
import { Navigate } from '@remix-run/react';
import { Header } from '~/components/header/Header';
import BackgroundRays from '~/components/ui/BackgroundRays';
import { authStore, initializeAuth } from '~/lib/stores/auth';
import { ChatWithClone } from '~/components/chat/ChatWithClone';
import { RepoProvider } from '~/lib/contexts/RepoContext';
import { usePersistedRepoContext } from '~/lib/hooks/usePersistedRepoContext';

export const meta: MetaFunction = () => {
  return [{ title: 'Chat - GitMesh' }, { name: 'description', content: 'GitMesh: Git Collaboration Network for OSS' }];
};

export const loader = () => json({});

const isDevelopment = import.meta.env.DEV;

/**
 * Chat page component for GitMesh
 * Note: Settings functionality should ONLY be accessed through the sidebar menu.
 * Do not add settings button/panel to this chat page as it was intentionally removed
 * to keep the UI clean and consistent with the design system.
 */
export default function ChatPage() {
  const { user, loading, initialized } = useStore(authStore);
  const { selectedRepo, fromHub, clearRepoContext } = usePersistedRepoContext();

  useEffect(() => {
    if (!initialized) {
      initializeAuth();
    }
  }, [initialized]);

  // Show loading state while checking auth
  if (!initialized || loading) {
    return (
      <div className="flex items-center justify-center min-h-screen bg-gitmesh-elements-background-depth-1">
        <div className="text-gitmesh-elements-textPrimary">Loading...</div>
      </div>
    );
  }

  // In production, redirect to landing page if not authenticated
  if (!isDevelopment && !user) {
    return <Navigate to="/" replace />;
  }

  return (
    <RepoProvider value={{ selectedRepo, fromHub, clearRepoContext }}>
      <div className="flex flex-col h-full w-full bg-gitmesh-elements-background-depth-1">
        <BackgroundRays />
        <Header />
        <ChatWithClone />
      </div>
    </RepoProvider>
  );
}
