"use client";

import { createContext, useContext, ReactNode, Suspense } from 'react';
import { useSearchParams } from 'next/navigation';

interface ContributionContextType {
  owner: string | null;
  repo: string | null;
  branch: string | null;
}

const ContributionContext = createContext<ContributionContextType | null>(null);

// Internal component that uses search params
const ContributionProviderInternal = ({ children }: { children: ReactNode }) => {
  const searchParams = useSearchParams();
  const owner = searchParams.get('owner');
  const repo = searchParams.get('repo');
  const branch = searchParams.get('branch');

  return (
    <ContributionContext.Provider value={{ owner, repo, branch }}>
      {children}
    </ContributionContext.Provider>
  );
};

// Main provider with Suspense boundary
export const ContributionProvider = ({ children }: { children: ReactNode }) => {
  return (
    <Suspense fallback={<div>Loading contribution context...</div>}>
      <ContributionProviderInternal>
        {children}
      </ContributionProviderInternal>
    </Suspense>
  );
};

export const useContribution = () => {
  const context = useContext(ContributionContext);
  if (!context) {
    throw new Error('useContribution must be used within a ContributionProvider');
  }
  return context;
};
