import { UserActivity } from '@/lib/github-api';
import { GitCommit, GitPullRequest, GitBranch, Star, Book, AlertCircle } from 'lucide-react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';

interface TimelineItemProps {
  activity: UserActivity;
  isLast: boolean;
}

const eventIcons: { [key: string]: React.ReactNode } = {
  PushEvent: <GitCommit className="w-5 h-5 text-gray-400" />,
  PullRequestEvent: <GitPullRequest className="w-5 h-5 text-gray-400" />,
  CreateEvent: <GitBranch className="w-5 h-5 text-gray-400" />,
  WatchEvent: <Star className="w-5 h-5 text-gray-400" />,
  IssuesEvent: <AlertCircle className="w-5 h-5 text-gray-400" />,
  ForkEvent: <Book className="w-5 h-5 text-gray-400" />,
};

const renderContent = (activity: UserActivity) => {
  switch (activity.type) {
    case 'PushEvent':
      return (
        <div>
          <p className="text-sm text-gray-300">
            Pushed {activity.payload.commits.length} commit(s) to{" "}
            <span className="font-semibold text-white">{activity.payload.ref.replace('refs/heads/', '')}</span>
          </p>
          <ul className="mt-2 space-y-1">
            {activity.payload.commits.map((commit: any) => (
              <li key={commit.sha} className="flex items-center gap-2">
                <GitCommit className="w-4 h-4 text-gray-500" />
                <a
                  href={`https://github.com/${activity.repo.name}/commit/${commit.sha}`}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-sm text-orange-500 hover:underline"
                >
                  {commit.message}
                </a>
              </li>
            ))}
          </ul>
        </div>
      );
    case 'PullRequestEvent':
      return (
        <div>
          <p className="text-sm text-gray-300">
            {activity.payload.action} pull request{" "}
            <a
              href={activity.payload.pull_request.html_url}
              target="_blank"
              rel="noopener noreferrer"
              className="font-semibold text-orange-500 hover:underline"
            >
              #{activity.payload.pull_request.number}
            </a>
          </p>
          <p className="mt-1 text-sm text-gray-400">{activity.payload.pull_request.title}</p>
        </div>
      );
    case 'CreateEvent':
      return (
        <p className="text-sm text-gray-300">
          Created a {activity.payload.ref_type} named <span className="font-semibold text-white">{activity.payload.ref}</span>
        </p>
      );
    case 'WatchEvent':
      return (
        <p className="text-sm text-gray-300">
          Starred the repository
        </p>
      );
    case 'IssuesEvent':
      return (
        <div>
          <p className="text-sm text-gray-300">
            {activity.payload.action} issue{" "}
            <a
              href={activity.payload.issue.html_url}
              target="_blank"
              rel="noopener noreferrer"
              className="font-semibold text-orange-500 hover:underline"
            >
              #{activity.payload.issue.number}
            </a>
          </p>
          <p className="mt-1 text-sm text-gray-400">{activity.payload.issue.title}</p>
        </div>
      );
    case 'ForkEvent':
      return (
        <p className="text-sm text-gray-300">
          Forked the repository to{" "}
          <a
            href={activity.payload.forkee.html_url}
            target="_blank"
            rel="noopener noreferrer"
            className="font-semibold text-orange-500 hover:underline"
          >
            {activity.payload.forkee.full_name}
          </a>
        </p>
      );
    default:
      return <p className="text-sm text-gray-300">Unhandled event type: {activity.type}</p>;
  }
};

export const TimelineItem: React.FC<TimelineItemProps> = ({ activity, isLast }) => {
  const icon = eventIcons[activity.type] || <AlertCircle className="w-5 h-5 text-gray-500" />;

  return (
    <div className={`relative mb-8 pl-12 ${isLast ? '' : 'after:absolute after:left-6 after:top-12 after:h-[calc(100%-3rem)] after:w-px after:bg-gray-700'}`}>
      <div className="absolute left-0 top-2 flex h-12 w-12 items-center justify-center rounded-full bg-gray-800">
        <div className="flex h-10 w-10 items-center justify-center rounded-full bg-gray-900">
          {icon}
        </div>
      </div>
      <Card className="bg-gray-800 border-gray-700 shadow-md">
        <CardHeader>
          <CardTitle className="text-base font-semibold text-white">
            <a href={`https://github.com/${activity.repo.name}`} target="_blank" rel="noopener noreferrer" className="hover:underline">
              {activity.repo.name}
            </a>
          </CardTitle>
          <CardDescription className="text-gray-400">{new Date(activity.created_at).toLocaleString()}</CardDescription>
        </CardHeader>
        <CardContent>{renderContent(activity)}</CardContent>
      </Card>
    </div>
  );
};