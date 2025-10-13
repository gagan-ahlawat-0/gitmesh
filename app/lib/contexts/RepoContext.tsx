import { createContext, useContext, type ReactNode } from 'react';

interface RepoContextType {
  selectedRepo?: {
    clone_url: string;
    name: string;
    full_name: string;
    provider: 'github' | 'gitlab';
  };
  fromHub?: boolean;
  clearRepoContext?: () => void;
}

const RepoContext = createContext<RepoContextType>({});

export function RepoProvider({ children, value }: { children: ReactNode; value: RepoContextType }) {
  return <RepoContext.Provider value={value}>{children}</RepoContext.Provider>;
}

export function useRepoContext() {
  return useContext(RepoContext);
}
