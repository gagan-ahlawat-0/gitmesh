import * as DropdownMenu from '@radix-ui/react-dropdown-menu';
import { motion } from 'framer-motion';
import { useStore } from '@nanostores/react';
import { toast } from 'react-toastify';
import { classNames } from '~/utils/classNames';
import { profileStore } from '~/lib/stores/profile';
import { authStore, signOut } from '~/lib/stores/auth';
import { isSupabaseConfigured } from '~/lib/supabase';
import type { TabType, Profile } from './types';

interface AvatarDropdownProps {
  onSelectTab: (tab: TabType) => void;
}

export const AvatarDropdown = ({ onSelectTab }: AvatarDropdownProps) => {
  const profile = useStore(profileStore) as Profile;
  const { user } = useStore(authStore);

  const handleSignOut = async () => {
    try {
      if (user && isSupabaseConfigured()) {
        await signOut();
        toast.success('Signed out successfully');
      } else {
        // In guest mode, just redirect to landing page
        window.location.href = '/';
      }
    } catch (error) {
      console.error('Failed to sign out:', error);
      toast.error('Failed to sign out');
    }
  };

  return (
    <DropdownMenu.Root>
      <DropdownMenu.Trigger asChild>
        <motion.button
          className="w-10 h-10 rounded-full bg-transparent flex items-center justify-center focus:outline-none"
          whileHover={{ scale: 1.02 }}
          whileTap={{ scale: 0.98 }}
        >
          {profile?.avatar ? (
            <img
              src={profile.avatar}
              alt={profile?.username || 'Profile'}
              className="w-full h-full rounded-full object-cover"
              loading="eager"
              decoding="sync"
            />
          ) : (
            <div className="w-full h-full rounded-full flex items-center justify-center bg-white dark:bg-gray-800 text-gray-400 dark:text-gray-500">
              <div className="i-ph:user w-6 h-6" />
            </div>
          )}
        </motion.button>
      </DropdownMenu.Trigger>

      <DropdownMenu.Portal>
        <DropdownMenu.Content
          className={classNames(
            'min-w-[240px] z-[250]',
            'bg-white dark:bg-[#141414]',
            'rounded-lg shadow-lg',
            'border border-gray-200/50 dark:border-gray-800/50',
            'animate-in fade-in-0 zoom-in-95',
            'py-1',
          )}
          sideOffset={5}
          align="end"
        >
          <div
            className={classNames(
              'px-4 py-3 flex items-center gap-3',
              'border-b border-gray-200/50 dark:border-gray-800/50',
            )}
          >
            <div className="w-10 h-10 rounded-full overflow-hidden flex-shrink-0 bg-white dark:bg-gray-800 shadow-sm">
              {profile?.avatar ? (
                <img
                  src={profile.avatar}
                  alt={profile?.username || 'Profile'}
                  className={classNames('w-full h-full', 'object-cover', 'transform-gpu', 'image-rendering-crisp')}
                  loading="eager"
                  decoding="sync"
                />
              ) : (
                <div className="w-full h-full flex items-center justify-center text-gray-400 dark:text-gray-500 font-medium text-lg">
                  <div className="i-ph:user w-6 h-6" />
                </div>
              )}
            </div>
            <div className="flex-1 min-w-0">
              <div className="font-medium text-sm text-gray-900 dark:text-white truncate">
                {profile?.username || 'Guest User'}
              </div>
              {profile?.bio && <div className="text-xs text-gray-500 dark:text-gray-400 truncate">{profile.bio}</div>}
            </div>
          </div>

          <DropdownMenu.Item
            className={classNames(
              'flex items-center gap-2 px-4 py-2.5',
              'text-sm text-gray-700 dark:text-gray-200',
              'hover:bg-blue-50 dark:hover:bg-blue-500/10',
              'hover:text-blue-500 dark:hover:text-blue-400',
              'cursor-pointer transition-all duration-200',
              'outline-none',
              'group',
            )}
            onClick={() => onSelectTab('profile')}
          >
            <div className="i-ph:user-circle w-4 h-4 text-gray-400 group-hover:text-blue-500 dark:group-hover:text-blue-400 transition-colors" />
            Edit Profile
          </DropdownMenu.Item>

          <DropdownMenu.Item
            className={classNames(
              'flex items-center gap-2 px-4 py-2.5',
              'text-sm text-gray-700 dark:text-gray-200',
              'hover:bg-blue-50 dark:hover:bg-blue-500/10',
              'hover:text-blue-500 dark:hover:text-blue-400',
              'cursor-pointer transition-all duration-200',
              'outline-none',
              'group',
            )}
            onClick={() => onSelectTab('settings')}
          >
            <div className="i-ph:gear-six w-4 h-4 text-gray-400 group-hover:text-blue-500 dark:group-hover:text-blue-400 transition-colors" />
            Settings
          </DropdownMenu.Item>

          <div className="my-1 border-t border-gray-200/50 dark:border-gray-800/50" />

          <DropdownMenu.Item
            className={classNames(
              'flex items-center gap-2 px-4 py-2.5',
              'text-sm text-gray-700 dark:text-gray-200',
              'hover:bg-blue-50 dark:hover:bg-blue-500/10',
              'hover:text-blue-500 dark:hover:text-blue-400',
              'cursor-pointer transition-all duration-200',
              'outline-none',
              'group',
            )}
            onClick={() =>
              window.open(
                'https://github.com/LF-Decentralized-Trust-labs/gitmesh/issues/new?template=bug_report.yml',
                '_blank',
              )
            }
          >
            <div className="i-ph:bug w-4 h-4 text-gray-400 group-hover:text-blue-500 dark:group-hover:text-blue-400 transition-colors" />
            Report Bug
          </DropdownMenu.Item>

          <DropdownMenu.Item
            className={classNames(
              'flex items-center gap-2 px-4 py-2.5',
              'text-sm text-gray-700 dark:text-gray-200',
              'hover:bg-blue-50 dark:hover:bg-blue-500/10',
              'hover:text-blue-500 dark:hover:text-blue-400',
              'cursor-pointer transition-all duration-200',
              'outline-none',
              'group',
            )}
            onClick={async () => {
              try {
                const { downloadDebugLog } = await import('~/utils/debugLogger');
                await downloadDebugLog();
              } catch (error) {
                console.error('Failed to download debug log:', error);
              }
            }}
          >
            <div className="i-ph:download w-4 h-4 text-gray-400 group-hover:text-blue-500 dark:group-hover:text-blue-400 transition-colors" />
            Download Debug Log
          </DropdownMenu.Item>

          <div className="my-1 border-t border-gray-200/50 dark:border-gray-800/50" />

          <DropdownMenu.Item
            className={classNames(
              'flex items-center gap-2 px-4 py-2.5',
              'text-sm text-red-600 dark:text-red-400',
              'hover:bg-red-50 dark:hover:bg-red-500/10',
              'cursor-pointer transition-all duration-200',
              'outline-none',
              'group',
            )}
            onClick={handleSignOut}
          >
            <div className="i-ph:sign-out w-4 h-4 text-red-500 group-hover:text-red-600 dark:group-hover:text-red-300 transition-colors" />
            {user ? 'Sign Out' : 'Exit to Landing'}
          </DropdownMenu.Item>
        </DropdownMenu.Content>
      </DropdownMenu.Portal>
    </DropdownMenu.Root>
  );
};
