import { atom } from 'nanostores';

// PR dialog state
export const prDialogOpen = atom<boolean>(false);
export const prProvider = atom<'github' | 'gitlab' | null>(null);

// Reset PR state
export function resetPRState() {
  prDialogOpen.set(false);
  prProvider.set(null);
}
