import { useRepoContext } from '~/lib/contexts/RepoContext';
import { classNames } from '~/utils/classNames';
import { Github, GitBranch } from 'lucide-react';
import { useNavigate } from '@remix-run/react';

interface RepoStatusProps {
  className?: string;
  embedded?: boolean; // New prop to control embedded vs standalone mode
}

export function RepoStatus({ className, embedded = false }: RepoStatusProps) {
  const { selectedRepo, fromHub, clearRepoContext } = useRepoContext();
  const navigate = useNavigate();

  // Only show if we have a repo and came from hub
  if (!selectedRepo || !fromHub) {
    return null;
  }

  const getRepoUrl = () => {
    if (selectedRepo.provider === 'github') {
      return `https://github.com/${selectedRepo.full_name}`;
    } else if (selectedRepo.provider === 'gitlab') {
      return `https://gitlab.com/${selectedRepo.full_name}`;
    }

    return selectedRepo.clone_url;
  };

  const handleRepoClick = () => {
    window.open(getRepoUrl(), '_blank');
  };

  const handleHomeClick = (e: React.MouseEvent) => {
    e.stopPropagation();

    // Check if user wants to clear repo context (ctrl/cmd + click) or just go to hub
    if (e.ctrlKey || e.metaKey) {
      // Clear repo context and go to clean chat
      if (clearRepoContext) {
        clearRepoContext();
      }
    } else {
      // Normal click - go to hub projects
      navigate('/hub/projects');
    }
  };

  if (embedded) {
    // Embedded mode for header integration
    return (
      <div
        className={classNames(
          'flex items-center gap-2',
          'text-gitmesh-elements-textPrimary',
          'text-sm font-medium',
          className,
        )}
      >
        {/* Repository info */}
        <div className="flex items-center gap-1.5 min-w-0">
          <div className="flex items-center text-gitmesh-elements-textSecondary">
            {selectedRepo.provider === 'github' ? (
              <Github className="w-3.5 h-3.5" />
            ) : (
              <GitBranch className="w-3.5 h-3.5" />
            )}
          </div>
          <button
            onClick={handleRepoClick}
            className="truncate max-w-[120px] text-gitmesh-elements-textPrimary hover:text-gitmesh-elements-item-contentAccent transition-colors duration-200 font-medium bg-gitmesh-elements-background-depth-1"
            title={`Open ${selectedRepo.full_name} in new tab`}
          >
            {selectedRepo.name}
          </button>
        </div>

        {/* Home button */}
        <button
          onClick={handleHomeClick}
          className="flex items-center justify-center w-7 h-7 rounded-md bg-transparent hover:bg-gitmesh-elements-background-depth-1 text-gitmesh-elements-textSecondary hover:text-gitmesh-elements-textPrimary transition-all duration-200"
          title="Back to Projects (Ctrl+Click to exit repo mode)"
        >
          <div className="i-ph:house w-3.5 h-3.5" />
        </button>
      </div>
    );
  }

  // Standalone mode - directly on screen like sidebar button
  return (
    <div
      className={classNames(
        'fixed top-4 right-4 z-40',
        'flex items-center gap-2',
        'text-gitmesh-elements-textPrimary',
        'text-sm font-medium',
        className,
      )}
    >
      {/* Repository info */}
      <div className="flex items-center gap-1.5 min-w-0">
        <div className="flex items-center text-gitmesh-elements-textSecondary">
          {selectedRepo.provider === 'github' ? <Github className="w-4 h-4" /> : <GitBranch className="w-4 h-4" />}
        </div>
        <button
          onClick={handleRepoClick}
          className="truncate max-w-[120px] text-gitmesh-elements-textPrimary hover:text-gitmesh-elements-item-contentAccent transition-colors duration-200 font-medium bg-gitmesh-elements-background-depth-1"
          title={`Open ${selectedRepo.full_name} in new tab`}
        >
          {selectedRepo.name}
        </button>
      </div>

      {/* Home button */}
      <button
        onClick={handleHomeClick}
        className="flex items-center justify-center w-7 h-7 rounded-md bg-transparent hover:bg-gitmesh-elements-background-depth-1 text-gitmesh-elements-textSecondary hover:text-gitmesh-elements-textPrimary transition-all duration-200"
        title="Back to Projects (Ctrl+Click to exit repo mode)"
      >
        <div className="i-ph:house w-4 h-4" />
      </button>
    </div>
  );
}
