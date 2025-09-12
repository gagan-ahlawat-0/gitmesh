"use client";

import { useAuth } from '@/contexts/AuthContext';
import { useEffect, useState } from 'react';
import { HubHeader } from '@/components/hub/HubHeader';
import { StatsCard } from '@/components/hub/overview/StatsCards';
import { RecentActivity } from '@/components/hub/overview/RecentActivity';
import { MonthlyGoals } from '@/components/hub/overview/MonthlyGoals';
import { QuickActions } from '@/components/hub/overview/QuickActions';
import { AIInsights } from '@/components/hub/overview/AIInsights';
import { AssignedIssues } from '@/components/hub/overview/AssignedIssues';
import { GitCommit, GitPullRequest, Star, Users, CheckCircle, GitMerge, BookOpen, Eye, AlertCircle } from 'lucide-react';
import { HubOverviewSkeleton } from '@/components/hub/overview/HubOverviewSkeleton';

const getTimeBasedGreeting = () => {
  const now = new Date();
  const hour = now.getHours();

  if (hour >= 5 && hour < 12) return "Morning";
  if (hour >= 12 && hour < 17) return "Afternoon";
  if (hour >= 17 && hour < 21) return "Evening";
  return "Yo"; // For late night vibes
};

const getPersonalSubtitle = () => {
  const day = new Date().getDay();

  switch (day) {
    case 1:
      return "ugh monday again, let’s get this over with";
    case 2:
      return "hey, tuesday’s good for some actual work";
    case 3:
      return "midweek already? ship something small";
    case 4:
      return "thursday chill vibes but don’t slack";
    case 5:
      return "friday finally, but maybe don’t push to prod";
    case 6:
      return "saturday man, hack or relax, up to you";
    case 0:
    default:
      return "sunday… maybe take it easy or prep for monday";
  }
};


export default function HubOverviewPage() {
  const { user, loading: authLoading, githubApi, isAuthenticated } = useAuth();
  const [loading, setLoading] = useState(true);
  const [summary, setSummary] = useState<any>(null);
  const [activities, setActivities] = useState<any[]>([]);
  const [issues, setIssues] = useState<any[]>([]);
  const [pullRequests, setPullRequests] = useState<any[]>([]);

  useEffect(() => {
    if (githubApi && isAuthenticated) {
      const api = githubApi;
      Promise.all([
        api.getAggregatedSummary(),
        api.getUserActivity(user?.login),
        api.getAggregatedIssues('open'),
        api.getAggregatedPullRequests('open'),
      ]).then(([summary, activities, issues, pullRequests]) => {
        setSummary(summary);
        setActivities(activities);
        setIssues(issues);
        setPullRequests(pullRequests);
        setLoading(false);
      }).catch(error => {
        console.error("Failed to fetch overview data:", error);
        setLoading(false);
      });
    }
  }, [githubApi, isAuthenticated, user?.login]);

  if (authLoading || loading) {
    return <HubOverviewSkeleton />;
  }

  return (
    <div className="min-h-screen bg-black text-white">
      <div className="container mx-auto p-4 sm:p-6 lg:p-8">
      <HubHeader
        title={`${getTimeBasedGreeting()},`}
        subtitle={`${user?.name || user?.login || 'builder'}, ${getPersonalSubtitle()}`}
      />
        
        {/* Main Stats */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mt-8">
          <StatsCard title="Commits Today" value={summary?.commitsToday || 0} icon={<GitCommit className="h-6 w-6 text-orange-500" />} />
          <StatsCard title="Active PRs" value={summary?.activePRs || 0} icon={<GitPullRequest className="h-6 w-6 text-orange-500" />} />
          <StatsCard title="Stars Earned" value={summary?.starsEarned || 0} icon={<Star className="h-6 w-6 text-orange-500" />} />
          <StatsCard title="Collaborators" value={summary?.collaborators || 0} icon={<Users className="h-6 w-6 text-orange-500" />} />
        </div>

        {/* Key Metrics */}
        {/* <div className="mt-8">
          <h2 className="text-2xl font-semibold text-gray-200 mb-4">Key Metrics</h2>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <StatsCard title="Code Reviews" value={summary?.reviews || 0} icon={<Eye className="h-6 w-6 text-orange-500" />} />
            <StatsCard title="Merged PRs" value={summary?.mergedPRs || 0} icon={<GitMerge className="h-6 w-6 text-green-400" />} />
            <StatsCard title="New Issues" value={summary?.newIssues || 0} icon={<AlertCircle className="h-6 w-6 text-red-400" />} />
          </div>
        </div> */} {/* TO-DO */}

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8 mt-8">
          <div className="lg:col-span-2 bg-black p-6 rounded-lg shadow-lg">
            <h2 className="text-xl font-bold mb-4 text-gray-200">Recent Activity</h2>
            <RecentActivity activities={activities} />
          </div>
          {/* <div className="bg-black p-6 rounded-lg shadow-lg">
            <h2 className="text-xl font-bold mb-4 text-gray-200">Monthly Goals</h2>
            <MonthlyGoals goals={mockGoals} />
          </div> */} {/* TO-DO */}
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8 mt-8">
          <div className="lg:col-span-2">
            <AssignedIssues issues={issues} pullRequests={pullRequests} />
          </div>
          {/* <div className="space-y-8">
            <div className="bg-black p-6 rounded-lg shadow-lg">
              <h2 className="text-xl font-bold mb-4 text-gray-200">Quick Actions</h2>
              <QuickActions />
            </div>
            <div className="bg-black p-6 rounded-lg shadow-lg">
              <h2 className="text-xl font-bold mb-4 text-gray-200">AI Insights</h2>
              <AIInsights insights={mockInsights} />
            </div>
          </div> */} {/* TO-DO */}
        </div>
      </div>
    </div>
  );
}
