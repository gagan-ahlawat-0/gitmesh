import { createContext, useContext, type ReactNode } from 'react';
import type { Message } from 'ai';

interface CloneContextType {
  addClonedMessages?: (messages: Message[]) => void;
}

const CloneContext = createContext<CloneContextType>({});

export function CloneProvider({ children, value }: { children: ReactNode; value: CloneContextType }) {
  return <CloneContext.Provider value={value}>{children}</CloneContext.Provider>;
}

export function useCloneContext() {
  return useContext(CloneContext);
}
