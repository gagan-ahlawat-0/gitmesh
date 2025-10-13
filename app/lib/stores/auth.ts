import { atom } from 'nanostores';
import { auth, type User } from '~/lib/supabase';

interface AuthState {
  user: User | null;
  loading: boolean;
  initialized: boolean;
}

const initialState: AuthState = {
  user: null,
  loading: true,
  initialized: false,
};

export const authStore = atom<AuthState>(initialState);

export const initializeAuth = async () => {
  // Only initialize on client-side
  if (typeof window === 'undefined') {
    return;
  }

  try {
    const { session } = await auth.getSession();
    authStore.set({
      user: session?.user as User | null,
      loading: false,
      initialized: true,
    });

    // Set up auth state listener
    auth.onAuthStateChange((user) => {
      const current = authStore.get();
      authStore.set({
        ...current,
        user,
        loading: false,
      });
    });
  } catch (error) {
    console.error('Failed to initialize auth:', error);
    authStore.set({
      user: null,
      loading: false,
      initialized: true,
    });
  }
};

export const signOut = async () => {
  const current = authStore.get();
  authStore.set({ ...current, loading: true });

  try {
    await auth.signOut();

    // The auth state change listener will handle updating the store
  } catch (error) {
    console.error('Failed to sign out:', error);

    const current = authStore.get();
    authStore.set({ ...current, loading: false });
  }
};
