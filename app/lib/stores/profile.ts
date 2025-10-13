import { atom } from 'nanostores';
import { authStore } from './auth';
import type { User } from '~/lib/supabase';

interface Profile {
  username: string;
  bio: string;
  avatar: string;
}

// Initialize with stored profile or defaults
const storedProfile = typeof window !== 'undefined' ? localStorage.getItem('gitmesh_profile') : null;
const initialProfile: Profile = storedProfile
  ? JSON.parse(storedProfile)
  : {
      username: '',
      bio: '',
      avatar: '',
    };

export const profileStore = atom<Profile>(initialProfile);

// Sync profile with authentication state
if (typeof window !== 'undefined') {
  authStore.subscribe((authState) => {
    if (authState.user) {
      const user = authState.user as User;
      const currentProfile = profileStore.get();

      // Update profile from user metadata if not already set
      const updates: Partial<Profile> = {};

      if (!currentProfile.username && (user.user_metadata?.full_name || user.user_metadata?.name)) {
        updates.username = user.user_metadata.full_name || user.user_metadata.name || '';
      }

      if (!currentProfile.avatar && user.user_metadata?.avatar_url) {
        updates.avatar = user.user_metadata.avatar_url;
      }

      if (Object.keys(updates).length > 0) {
        updateProfile(updates);
      }
    } else {
      // Clear profile when signed out unless it's a manual profile
      const currentProfile = profileStore.get();

      if (currentProfile.username && !localStorage.getItem('gitmesh_profile_manual')) {
        profileStore.set({
          username: '',
          bio: '',
          avatar: '',
        });
        localStorage.removeItem('gitmesh_profile');
      }
    }
  });
}

export const updateProfile = (updates: Partial<Profile>) => {
  profileStore.set({ ...profileStore.get(), ...updates });

  // Persist to localStorage
  if (typeof window !== 'undefined') {
    localStorage.setItem('gitmesh_profile', JSON.stringify(profileStore.get()));

    // Mark as manually updated if username was changed
    if (updates.username) {
      localStorage.setItem('gitmesh_profile_manual', 'true');
    }
  }
};
