import { useEffect, useState } from 'react';
import { toast } from 'react-toastify';

interface DevError {
  message: string;
  stack?: string;
  timestamp: string;
}

const isDevelopment = import.meta.env.DEV;
const GITHUB_REPO = 'LF-Decentralized-Trust-labs/gitmesh';

export function DevErrorHandler() {
  const [errors, setErrors] = useState<DevError[]>([]);

  useEffect(() => {
    if (!isDevelopment) {
      return undefined;
    }

    const handleError = (event: ErrorEvent) => {
      const error: DevError = {
        message: event.message,
        stack: event.error?.stack,
        timestamp: new Date().toISOString(),
      };

      setErrors((prev) => [...prev, error]);
      showErrorNotification(error);
    };

    const handleUnhandledRejection = (event: PromiseRejectionEvent) => {
      const error: DevError = {
        message: `Unhandled Promise Rejection: ${event.reason}`,
        stack: event.reason?.stack,
        timestamp: new Date().toISOString(),
      };

      setErrors((prev) => [...prev, error]);
      showErrorNotification(error);
    };

    window.addEventListener('error', handleError);
    window.addEventListener('unhandledrejection', handleUnhandledRejection);

    const cleanup = () => {
      window.removeEventListener('error', handleError);
      window.removeEventListener('unhandledrejection', handleUnhandledRejection);
    };

    return cleanup;
  }, []);

  const showErrorNotification = (error: DevError) => {
    toast.error(
      <div className="flex flex-col gap-2">
        <div className="font-semibold text-red-500">Development Error Detected</div>
        <div className="text-sm text-gray-600 max-w-md truncate">{error.message}</div>
        <div className="flex gap-2">
          <button
            onClick={() => createGitHubIssue(error)}
            className="px-3 py-1 bg-blue-500 text-white text-xs rounded hover:bg-blue-600 transition-colors"
          >
            Report Issue
          </button>
          <button
            onClick={() => copyErrorToClipboard(error)}
            className="px-3 py-1 bg-gray-500 text-white text-xs rounded hover:bg-gray-600 transition-colors"
          >
            Copy Error
          </button>
        </div>
      </div>,
      {
        autoClose: false,
        closeOnClick: false,
        draggable: false,
      },
    );
  };

  const createGitHubIssue = (error: DevError) => {
    const title = `Bug: ${error.message.substring(0, 100)}${error.message.length > 100 ? '...' : ''}`;

    const body = `## Bug Report

**Environment:** Development Mode
**Timestamp:** ${error.timestamp}
**User Agent:** ${navigator.userAgent}
**URL:** ${window.location.href}

### Error Details

\`\`\`
${error.message}
\`\`\`

### Stack Trace

\`\`\`
${error.stack || 'No stack trace available'}
\`\`\`

### Steps to Reproduce
<!-- Please describe the steps that led to this error -->

### Expected Behavior
<!-- What should have happened instead? -->

### Additional Context
<!-- Any other information that might be helpful -->

---
*This issue was automatically generated from the development error handler.*
`;

    const url = new URL(`https://github.com/${GITHUB_REPO}/issues/new`);
    url.searchParams.set('title', title);
    url.searchParams.set('body', body);
    url.searchParams.set('labels', 'bug,development');

    window.open(url.toString(), '_blank');
  };

  const copyErrorToClipboard = async (error: DevError) => {
    const errorText = `Error: ${error.message}\n\nStack: ${error.stack || 'No stack trace'}\n\nTimestamp: ${error.timestamp}`;

    try {
      await navigator.clipboard.writeText(errorText);
      toast.success('Error details copied to clipboard', { autoClose: 2000 });
    } catch (err) {
      console.error('Failed to copy to clipboard:', err);
      toast.error('Failed to copy to clipboard', { autoClose: 2000 });
    }
  };

  /*
   * This component doesn't render anything visible.
   * The errors state is kept for potential future use (e.g., error history)
   */
  console.debug(`DevErrorHandler: tracking ${errors.length} errors`);

  return null;
}
