import { useState } from 'react';
import { UserActivity } from '@/lib/github-api';
import { Button } from '@/components/ui/button';

interface RecentActivityProps {
  activities: UserActivity[];
}

const ITEMS_PER_PAGE = 5;

const renderActivityDetails = (activity: UserActivity) => {
  const { type, payload } = activity;
  switch (type) {
    case 'PushEvent':
      return (
        <p className="text-sm text-gray-400">
          Pushed {payload.commits.length} commit(s) to{' '}
          <a href={`https://github.com/${activity.repo.name}/tree/${payload.ref.split('/').pop()}`} target="_blank" rel="noopener noreferrer" className="font-semibold text-orange-500 hover:underline">
            {payload.ref.split('/').pop()}
          </a>
          : {payload.commits[0].message}
        </p>
      );
    case 'PullRequestEvent':
      return (
        <p className="text-sm text-gray-400">
          {payload.action} a pull request:{' '}
          <a href={payload.pull_request.html_url} target="_blank" rel="noopener noreferrer" className="font-semibold text-orange-500 hover:underline">
            {payload.pull_request.title}
          </a>
        </p>
      );
    case 'IssuesEvent':
      return (
        <p className="text-sm text-gray-400">
          {payload.action} an issue:{' '}
          <a href={payload.issue.html_url} target="_blank" rel="noopener noreferrer" className="font-semibold text-orange-500 hover:underline">
            {payload.issue.title}
          </a>
        </p>
      );
    case 'IssueCommentEvent':
      return (
        <p className="text-sm text-gray-400">
          Commented on issue:{' '}
          <a href={payload.comment.html_url} target="_blank" rel="noopener noreferrer" className="font-semibold text-orange-500 hover:underline">
            {payload.issue.title}
          </a>
        </p>
      );
    default:
      return null;
  }
};

export const RecentActivity: React.FC<RecentActivityProps> = ({ activities }) => {
  const [currentPage, setCurrentPage] = useState(1);
  const totalPages = Math.ceil(activities.length / ITEMS_PER_PAGE);

  const paginatedActivities = activities.slice(
    (currentPage - 1) * ITEMS_PER_PAGE,
    currentPage * ITEMS_PER_PAGE
  );

  return (
    <div className="h-[400px] flex flex-col">
      <ul className="space-y-4 flex-grow overflow-y-auto">
        {paginatedActivities.map((activity) => (
          <li key={activity.id} className="flex items-start space-x-3 p-4 bg-black rounded-lg shadow-sm">
            <div className="flex-shrink-0">
              <img className="w-10 h-10 rounded-full" src={activity.actor.avatar_url} alt={activity.actor.login} />
            </div>
            <div className="flex-1">
              <p className="text-sm text-gray-300">
                <a href={`https://github.com/${activity.actor.login}`} target="_blank" rel="noopener noreferrer" className="font-semibold text-orange-400 hover:underline">
                  {activity.actor.login}
                </a>
                <span className="text-gray-400"> in </span>
                <a href={`https://github.com/${activity.repo.name}`} target="_blank" rel="noopener noreferrer" className="font-semibold text-orange-400 hover:underline">
                  {activity.repo.name}
                </a>
              </p>
              {renderActivityDetails(activity)}
              <p className="text-xs text-gray-500 mt-1">{new Date(activity.created_at).toLocaleString()}</p>
            </div>
          </li>
        ))}
      </ul>
      {totalPages > 1 && (
        <div className="flex justify-center mt-6">
          <Button
            onClick={() => setCurrentPage((prev) => Math.max(prev - 1, 1))}
            disabled={currentPage === 1}
            className="bg-orange-500 text-black hover:bg-orange-600 disabled:bg-gray-700"
          >
            Previous
          </Button>
          <span className="mx-4 text-gray-300">Page {currentPage} of {totalPages}</span>
          <Button
            onClick={() => setCurrentPage((prev) => Math.min(prev + 1, totalPages))}
            disabled={currentPage === totalPages}
            className="bg-orange-500 text-black hover:bg-orange-600 disabled:bg-gray-700"
          >
            Next
          </Button>
        </div>
      )}
    </div>
  );
};