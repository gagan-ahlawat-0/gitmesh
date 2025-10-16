import type { LoaderFunctionArgs } from '@remix-run/node';
import { json } from '@remix-run/node';
import { useLoaderData, Navigate } from '@remix-run/react';
import { useEffect } from 'react';
import { useStore } from '@nanostores/react';
import { Header } from '~/components/header/Header';
import BackgroundRays from '~/components/ui/BackgroundRays';
import { authStore, initializeAuth } from '~/lib/stores/auth';
import { ChatWithClone } from '~/components/chat/ChatWithClone';
import { RepoProvider } from '~/lib/contexts/RepoContext';
import { usePersistedRepoContext } from '~/lib/hooks/usePersistedRepoContext';

const isDevelopment = import.meta.env.DEV;

export const loader = async ({ params }: LoaderFunctionArgs) => {
  console.log('🚀 PARAMETERIZED chat.$chatId.tsx loader called with params:', params);

  const chatId = params.chatId;
  console.log('🚀 PARAMETERIZED Extracted chatId:', chatId);

  const data = { mixedId: chatId };
  console.log('🚀 PARAMETERIZED Returning from loader:', data);

  return json(data);
};

function ChatIdRoute() {
  const loaderData = useLoaderData<typeof loader>();
  const { user, loading, initialized } = useStore(authStore);
  const { selectedRepo, fromHub, clearRepoContext } = usePersistedRepoContext();

  console.log('🎯 PARAMETERIZED ChatIdRoute rendered', { loaderData });

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

export default ChatIdRoute;
