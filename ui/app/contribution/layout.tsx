"use client";

import { useEffect, useRef } from 'react';
import { useRouter, useSearchParams, usePathname } from 'next/navigation';
import VSCodeInterface from '@/components/VSCodeInterface';
import ClientProviders from '@/components/ClientProviders';
import "./globals.css";
import { KnowledgeBaseProvider } from '@/contexts/KnowledgeBaseContext';
import { useAuth } from '@/contexts/AuthContext';
import { useRepository } from '@/contexts/RepositoryContext';
import { BranchProvider } from '@/contexts/BranchContext';
import { toast } from 'sonner';

export default function ContributionLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const searchParams = useSearchParams();
  const pathname = usePathname();
  const { setRepository, repository, isRepositoryLoaded } = useRepository();
  const repoProcessedRef = useRef(false);
  const router = useRouter();
  const { isAuthenticated, token } = useAuth();

  // Handle repository data from URL parameters
  useEffect(() => {
    const repoParam = searchParams.get('repo');
    if (repoParam && !repoProcessedRef.current) {
      try {
        const repoData = JSON.parse(decodeURIComponent(repoParam));
        
        // Validate required fields
        if (!repoData.name || !repoData.full_name || !repoData.owner?.login) {
          throw new Error('Invalid repository data structure');
        }
        
        // Ensure all required fields are present
        const validatedRepoData = {
          name: repoData.name,
          full_name: repoData.full_name,
          description: repoData.description || 'No description available',
          owner: {
            login: repoData.owner.login,
            avatar_url: repoData.owner.avatar_url || 'https://github.com/github.png',
            type: repoData.owner.type || 'User'
          },
          language: repoData.language || 'Unknown',
          stargazers_count: repoData.stargazers_count || 0,
          forks_count: repoData.forks_count || 0,
          html_url: repoData.html_url,
          clone_url: repoData.clone_url || (repoData.html_url ? `${repoData.html_url}.git` : ''),
          default_branch: repoData.default_branch || '',
          created_at: repoData.created_at || new Date().toISOString(),
          updated_at: repoData.updated_at || new Date().toISOString(),
          private: repoData.private || false,
          type: repoData.type || 'owned'
        };
        
        setRepository(validatedRepoData);
        repoProcessedRef.current = true;
        
        // Clean up URL parameters
        const newUrl = window.location.pathname;
        window.history.replaceState({}, document.title, newUrl);
        
        toast.success(`Opened ${validatedRepoData.full_name} in GitMesh`);
      } catch (error) {
        console.error('Error parsing repository data:', error);
        toast.error('Invalid repository data. Please try again.');
        // Redirect to landing page on error
        router.push('/');
      }
    }
  }, [searchParams, setRepository, router]);

  // Set up demo repository if in demo mode and no repository is set
  useEffect(() => {
    // Only set demo repository if:
    // 1. User is authenticated with demo token
    // 2. No repository is currently set
    // 3. Repository hasn't been processed from URL params
    // 4. Repository context has finished loading (to avoid overriding restored repository)
    if (isAuthenticated && token === 'demo-token' && !repository && !repoProcessedRef.current && isRepositoryLoaded) {
      const demoRepository = {
        name: 'GitMesh-app',
        full_name: 'demo-user/GitMesh-app',
        description: 'A demo repository for testing GitMesh features',
        owner: {
          login: 'demo-user',
          avatar_url: 'https://github.com/github.png',
          type: 'User'
        },
        language: 'TypeScript',
        stargazers_count: 42,
        forks_count: 8,
        html_url: 'https://github.com/demo-user/GitMesh-app',
        clone_url: 'https://github.com/demo-user/GitMesh-app.git',
        default_branch: '',
        created_at: '2023-01-01T00:00:00Z',
        updated_at: new Date().toISOString(),
        private: false,
        type: 'owned' as const
      };
      setRepository(demoRepository);
      repoProcessedRef.current = true;
    }
  }, [isAuthenticated, token, repository, isRepositoryLoaded, setRepository]);

  return (
    <ClientProviders>
      <KnowledgeBaseProvider>
        <BranchProvider>
          <div className="h-screen overflow-hidden">
            <VSCodeInterface>
              {children}
            </VSCodeInterface>
          </div>
        </BranchProvider>
      </KnowledgeBaseProvider>
    </ClientProviders>
  );
}