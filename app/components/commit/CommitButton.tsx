import { useStore } from '@nanostores/react';
import { memo } from 'react';
import * as DropdownMenu from '@radix-ui/react-dropdown-menu';
import { classNames } from '~/utils/classNames';
import { streamingState } from '~/lib/stores/streaming';
import { useCommit, useModifiedFiles, usePR } from '~/lib/hooks';

interface CommitButtonProps {
  className?: string;
}

export const CommitButton = memo(({ className }: CommitButtonProps) => {
  const streaming = useStore(streamingState);
  const { handleCommitToGitHub, handleCommitToGitLab } = useCommit();
  const { handleCreateGitHubPR, handleCreateGitLabPR } = usePR();
  const { count: modifiedFilesCount, hasFiles: hasModifications } = useModifiedFiles();

  const isDisabled = streaming || !hasModifications;

  const handleGitHubCommit = () => {
    handleCommitToGitHub();
  };

  const handleGitLabCommit = () => {
    handleCommitToGitLab();
  };

  const handleGitHubPR = () => {
    handleCreateGitHubPR();
  };

  const handleGitLabPR = () => {
    handleCreateGitLabPR();
  };

  return (
    <div
      className={classNames(
        'flex border border-gitmesh-elements-borderColor rounded-md overflow-hidden ml-1',
        className,
      )}
    >
      <DropdownMenu.Root>
        <DropdownMenu.Trigger
          disabled={isDisabled}
          className="rounded-md items-center justify-center [&:is(:disabled,.disabled)]:cursor-not-allowed [&:is(:disabled,.disabled)]:opacity-60 px-3 py-1.5 text-xs bg-green-500 text-white hover:text-gitmesh-elements-item-contentAccent [&:not(:disabled,.disabled)]:hover:bg-gitmesh-elements-button-primary-backgroundHover outline-green-500 flex gap-1.7"
        >
          {`Commit (${modifiedFilesCount})`}
          <span className={classNames('i-ph:caret-down transition-transform')} />
        </DropdownMenu.Trigger>
        <DropdownMenu.Portal>
          <DropdownMenu.Content className="min-w-[220px] bg-gitmesh-elements-background-depth-1 border border-gitmesh-elements-borderColor rounded-md shadow-lg p-1 z-[100] text-white">
            {/* Direct Commit Options */}
            <DropdownMenu.Label className="px-3 py-1.5 text-xs font-semibold text-gitmesh-elements-textSecondary uppercase tracking-wider">
              Direct Commit
            </DropdownMenu.Label>
            <DropdownMenu.Item
              className="flex items-center gap-2 px-3 py-2 text-sm cursor-pointer hover:bg-gitmesh-elements-background-depth-2 rounded outline-none"
              onClick={handleGitHubCommit}
            >
              <div className="i-ph:github-logo" />
              Commit to GitHub
            </DropdownMenu.Item>
            <DropdownMenu.Item
              className="flex items-center gap-2 px-3 py-2 text-sm cursor-pointer hover:bg-gitmesh-elements-background-depth-2 rounded outline-none"
              onClick={handleGitLabCommit}
            >
              <div className="i-ph:gitlab-logo" />
              Commit to GitLab
            </DropdownMenu.Item>

            {/* Separator */}
            <DropdownMenu.Separator className="h-px bg-gitmesh-elements-borderColor my-1" />

            {/* Pull Request Options */}
            <DropdownMenu.Label className="px-3 py-1.5 text-xs font-semibold text-gitmesh-elements-textSecondary uppercase tracking-wider">
              Create Pull Request
            </DropdownMenu.Label>
            <DropdownMenu.Item
              className="flex items-center gap-2 px-3 py-2 text-sm cursor-pointer hover:bg-gitmesh-elements-background-depth-2 rounded outline-none"
              onClick={handleGitHubPR}
            >
              <div className="i-ph:git-pull-request" />
              GitHub Pull Request
            </DropdownMenu.Item>
            <DropdownMenu.Item
              className="flex items-center gap-2 px-3 py-2 text-sm cursor-pointer hover:bg-gitmesh-elements-background-depth-2 rounded outline-none"
              onClick={handleGitLabPR}
            >
              <div className="i-ph:git-merge" />
              GitLab Merge Request
            </DropdownMenu.Item>
          </DropdownMenu.Content>
        </DropdownMenu.Portal>
      </DropdownMenu.Root>
    </div>
  );
});
