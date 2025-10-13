import { useStore } from '@nanostores/react';
import { useNavigate } from '@remix-run/react';
import { profileStore } from '~/lib/stores/profile';
import { signOut, authStore } from '~/lib/stores/auth';
import { Dropdown, DropdownItem, DropdownSeparator } from '~/components/ui/Dropdown';

export function ProfileButton() {
  const profile = useStore(profileStore);
  const authState = useStore(authStore);
  const navigate = useNavigate();

  const handleGoToProfile = () => {
    navigate('/hub/settings/profile');
  };

  const handleSignOut = async () => {
    try {
      // Check if we're in development mode (guest mode) or production
      const isDev = import.meta.env.DEV;
      const isAuthenticated = !!authState.user;

      if (isDev && !isAuthenticated) {
        // In development mode with no authentication (guest mode), just navigate to home
        navigate('/');
        return;
      }

      // In production or when authenticated, perform actual sign out
      await signOut();
      navigate('/');
    } catch (error) {
      console.error('Sign out failed:', error);

      // Even if sign out fails, navigate to home page
      navigate('/');
    }
  };

  const trigger = (
    <button
      className="flex items-center gap-2 px-3 py-2 rounded-lg text-sm font-medium transition-colors duration-200 text-gitmesh-elements-textSecondary bg-gitmesh-elements-background-depth-1 hover:text-gitmesh-elements-textPrimary hover:bg-gitmesh-elements-background-depth-2"
      title={profile?.username || 'Profile'}
    >
      {profile?.avatar ? (
        <img
          src={profile.avatar}
          alt={profile?.username || 'User'}
          className="w-6 h-6 object-cover rounded-full"
          loading="eager"
          decoding="sync"
        />
      ) : (
        <div className="i-ph:user-circle-duotone w-6 h-6" />
      )}
      {profile?.username && <span className="hidden sm:inline">{profile.username}</span>}
      <div className="i-ph:caret-down w-4 h-4" />
    </button>
  );

  return (
    <Dropdown trigger={trigger} align="end">
      <DropdownItem onSelect={handleGoToProfile}>
        <div className="i-ph:user-duotone w-4 h-4" />
        Profile
      </DropdownItem>
      <DropdownSeparator />
      <DropdownItem onSelect={handleSignOut}>
        <div className="i-ph:sign-out-duotone w-4 h-4" />
        {import.meta.env.DEV && !authState.user ? 'Exit' : 'Sign Out'}
      </DropdownItem>
    </Dropdown>
  );
}
