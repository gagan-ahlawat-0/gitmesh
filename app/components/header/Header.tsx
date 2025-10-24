import { useStore } from '@nanostores/react';
import { ClientOnly } from 'remix-utils/client-only';
import { chatStore } from '~/lib/stores/chat';
import { sidebarOpen } from '~/lib/stores/sidebar';
import { classNames } from '~/utils/classNames';
import { HeaderActionButtons } from './HeaderActionButtons.client';
import { ChatDescription } from '~/lib/persistence/ChatDescription.client';
import { RepoStatus } from '~/components/chat/RepoStatus';

export function Header() {
  const chat = useStore(chatStore);
  const isSidebarOpen = useStore(sidebarOpen);

  return (
    <header
      // Make header fixed so it stays visible at the top of the screen
      className={classNames(
        'flex items-center px-4 border-b h-[var(--header-height)] fixed top-0 left-0 right-0 bg-gitmesh-elements-background-depth-1 z-40',
        {
          'border-transparent': !chat.started,
          'border-gitmesh-elements-borderColor': chat.started,
        },
      )}
    >
      <div
        className="flex items-center gap-2 z-logo text-gitmesh-elements-textPrimary cursor-pointer transition-colors hover:text-blue-700 dark:hover:text-blue-300"
        onClick={() => sidebarOpen.set(!isSidebarOpen)}
        title={isSidebarOpen ? 'Close sidebar' : 'Open sidebar'}
      >
        <div className="i-ph:sidebar-simple-duotone text-xl" />
        {/* <a href="/" className="text-2xl font-semibold text-accent flex items-center">
          <img src="/gitmesh.png" alt="logo" className="w-[90px] inline-block dark:hidden" />
          <img src="/gitmesh.png" alt="logo" className="w-[90px] inline-block hidden dark:block" />
        </a> */}
      </div>
      {chat.started && ( // Display ChatDescription and HeaderActionButtons only when the chat has started.
        <>
          <span className="flex-1 px-4 truncate text-center text-gitmesh-elements-textPrimary">
            <ClientOnly>{() => <ChatDescription />}</ClientOnly>
          </span>
          <div className="flex items-center gap-3">
            <RepoStatus embedded />
            <ClientOnly>
              {() => (
                <div className="">
                  <HeaderActionButtons chatStarted={chat.started} />
                </div>
              )}
            </ClientOnly>
          </div>
        </>
      )}
    </header>
  );
}
