"use client";

import { useEffect, useState, useCallback } from 'react';
import { useAuth } from '@/contexts/AuthContext';
import { Card, CardContent } from "@/components/ui/card";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { Badge } from "@/components/ui/badge";
import { GitHubUserActivity } from '@/lib/types';
import GitHubAPI from '@/lib/github-api';
import { Skeleton } from "@/components/ui/skeleton";
import { GitBranch, GitCommit, GitPullRequest, Star, GitFork, Eye, Calendar } from "lucide-react";

interface ProfileActivityProps {
  username: string;
}

export function ProfileActivity({ username }: ProfileActivityProps) {
  const { token } = useAuth();
  const [activities, setActivities] = useState<GitHubUserActivity[]>([]);
  const [loading, setLoading] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);
  const [page, setPage] = useState(1);
  const [hasMore, setHasMore] = useState(true);

  const fetchActivities = async (pageNum: number, isLoadMore = false) => {
    if (!token) return;

    if (isLoadMore) {
      setLoadingMore(true);
    } else {
      setLoading(true);
    }

    try {
      const api = new GitHubAPI(token);
      const newActivities = await api.getUserActivities(username, pageNum, 30);
      
      if (isLoadMore) {
        setActivities(prev => [...prev, ...newActivities]);
      } else {
        setActivities(newActivities);
      }
      
      // If we get less than 30 activities, we've reached the end
      setHasMore(newActivities.length === 30);
    } catch (error) {
      console.error('Failed to fetch activities:', error);
      if (!isLoadMore) {
        setActivities([]);
      }
    } finally {
      setLoading(false);
      setLoadingMore(false);
    }
  };

  useEffect(() => {
    if (username && token) {
      fetchActivities(1, false);
    }
  }, [username, token]);

  const loadMore = useCallback(() => {
    if (!loadingMore && hasMore) {
      const nextPage = page + 1;
      setPage(nextPage);
      fetchActivities(nextPage, true);
    }
  }, [page, loadingMore, hasMore]);

  useEffect(() => {
    const handleScroll = () => {
      if (
        window.innerHeight + document.documentElement.scrollTop
        >= document.documentElement.offsetHeight - 1000
      ) {
        loadMore();
      }
    };

    window.addEventListener('scroll', handleScroll);
    return () => window.removeEventListener('scroll', handleScroll);
  }, [loadMore]);

  const getActivityIcon = (type: string) => {
    switch (type) {
      case 'PushEvent':
        return <GitCommit className="w-4 h-4" />;
      case 'PullRequestEvent':
        return <GitPullRequest className="w-4 h-4" />;
      case 'CreateEvent':
        return <GitBranch className="w-4 h-4" />;
      case 'WatchEvent':
        return <Star className="w-4 h-4" />;
      case 'ForkEvent':
        return <GitFork className="w-4 h-4" />;
      case 'IssuesEvent':
        return <Eye className="w-4 h-4" />;
      default:
        return <Calendar className="w-4 h-4" />;
    }
  };

  const getActivityDescription = (activity: GitHubUserActivity) => {
    switch (activity.type) {
      case 'PushEvent':
        const commitCount = activity.payload?.commits?.length || 1;
        return `Pushed ${commitCount} commit${commitCount > 1 ? 's' : ''} to ${activity.repo.name}`;
      case 'PullRequestEvent':
        const action = activity.payload?.action || 'opened';
        return `${action.charAt(0).toUpperCase() + action.slice(1)} pull request in ${activity.repo.name}`;
      case 'CreateEvent':
        const refType = activity.payload?.ref_type || 'repository';
        return `Created ${refType} ${activity.payload?.ref || ''} in ${activity.repo.name}`;
      case 'WatchEvent':
        return `Starred ${activity.repo.name}`;
      case 'ForkEvent':
        return `Forked ${activity.repo.name}`;
      case 'IssuesEvent':
        const issueAction = activity.payload?.action || 'opened';
        return `${issueAction.charAt(0).toUpperCase() + issueAction.slice(1)} issue in ${activity.repo.name}`;
      default:
        return `${activity.type.replace('Event', '')} in ${activity.repo.name}`;
    }
  };

  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    const now = new Date();
    const diffInHours = Math.floor((now.getTime() - date.getTime()) / (1000 * 60 * 60));
    
    if (diffInHours < 1) {
      return 'Just now';
    } else if (diffInHours < 24) {
      return `${diffInHours} hour${diffInHours > 1 ? 's' : ''} ago`;
    } else if (diffInHours < 24 * 7) {
      const days = Math.floor(diffInHours / 24);
      return `${days} day${days > 1 ? 's' : ''} ago`;
    } else {
      return date.toLocaleDateString();
    }
  };

  if (loading) {
    return (
      <div className="space-y-4">
        {Array.from({ length: 10 }).map((_, i) => (
          <Card key={i}>
            <CardContent className="p-4">
              <div className="flex items-start space-x-3">
                <Skeleton className="w-8 h-8 rounded-full" />
                <div className="flex-1 space-y-2">
                  <Skeleton className="h-4 w-3/4" />
                  <Skeleton className="h-3 w-1/2" />
                </div>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <h3 className="text-xl font-semibold">Recent Activity</h3>
      
      {activities.length > 0 ? (
        <>
          {activities.map((activity) => (
            <Card key={activity.id}>
              <CardContent className="p-4">
                <div className="flex items-start space-x-3">
                  <Avatar className="w-8 h-8">
                    <AvatarImage src={activity.actor.avatar_url} alt={activity.actor.login} />
                    <AvatarFallback>{activity.actor.login.charAt(0)}</AvatarFallback>
                  </Avatar>
                  
                  <div className="flex-1">
                    <div className="flex items-center space-x-2 mb-1">
                      {getActivityIcon(activity.type)}
                      <span className="text-sm font-medium">
                        {getActivityDescription(activity)}
                      </span>
                      <Badge variant="outline" className="text-xs">
                        {activity.type.replace('Event', '')}
                      </Badge>
                    </div>
                    
                    <p className="text-xs text-muted-foreground">
                      {formatDate(activity.created_at)}
                    </p>
                    
                    {/* Additional details based on activity type */}
                    {activity.type === 'PushEvent' && activity.payload?.commits && (
                      <div className="mt-2 text-xs text-muted-foreground">
                        <div className="border-l-2 border-gray-200 pl-2">
                          {activity.payload.commits.slice(0, 3).map((commit: any, idx: number) => (
                            <div key={idx} className="truncate">
                              {commit.message}
                            </div>
                          ))}
                          {activity.payload.commits.length > 3 && (
                            <div>...and {activity.payload.commits.length - 3} more</div>
                          )}
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              </CardContent>
            </Card>
          ))}
          
          {loadingMore && (
            <div className="flex justify-center py-4">
              <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-gray-900"></div>
            </div>
          )}
          
          {!hasMore && activities.length > 0 && (
            <div className="text-center py-4 text-muted-foreground">
              <p>That's all the recent activity!</p>
            </div>
          )}
        </>
      ) : (
        <div className="text-center py-12">
          <p className="text-muted-foreground">No recent activity found.</p>
        </div>
      )}
    </div>
  );
}
