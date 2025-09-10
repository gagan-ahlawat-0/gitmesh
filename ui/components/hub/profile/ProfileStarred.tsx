"use client";

import { useEffect, useState, useCallback } from 'react';
import { useAuth } from '@/contexts/AuthContext';
import { Repository } from '@/lib/github-api';
import GitHubAPI from '@/lib/github-api';
import { EnhancedRepositoryCard } from './EnhancedRepositoryCard';
import { Skeleton } from "@/components/ui/skeleton";

interface ProfileStarredProps {
  username: string;
}

export function ProfileStarred({ username }: ProfileStarredProps) {
  const { token } = useAuth();
  const [starredRepos, setStarredRepos] = useState<Repository[]>([]);
  const [loading, setLoading] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);
  const [page, setPage] = useState(1);
  const [hasMore, setHasMore] = useState(true);

  const fetchStarredRepos = async (pageNum: number, isLoadMore = false) => {
    if (!token) return;

    if (isLoadMore) {
      setLoadingMore(true);
    } else {
      setLoading(true);
    }

    try {
      const api = new GitHubAPI(token);
      const response = await api.getUserStarredRepos(username, pageNum, 30);
      const newRepos = response.repositories || [];
      
      if (isLoadMore) {
        setStarredRepos(prev => [...prev, ...newRepos]);
      } else {
        setStarredRepos(newRepos);
      }
      
      // Check if there are more pages
      setHasMore(response.has_next_page || newRepos.length === 30);
    } catch (error) {
      console.error('Failed to fetch starred repositories:', error);
      if (!isLoadMore) {
        setStarredRepos([]);
      }
    } finally {
      setLoading(false);
      setLoadingMore(false);
    }
  };

  useEffect(() => {
    if (username && token) {
      fetchStarredRepos(1, false);
    }
  }, [username, token]);

  const loadMore = useCallback(() => {
    if (!loadingMore && hasMore) {
      const nextPage = page + 1;
      setPage(nextPage);
      fetchStarredRepos(nextPage, true);
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

  if (loading) {
    return (
      <div className="space-y-6">
        <div className="flex justify-between items-center">
          <Skeleton className="h-8 w-32" />
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {Array.from({ length: 12 }).map((_, i) => (
            <Skeleton key={i} className="h-40" />
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <h3 className="text-xl font-semibold">
        Starred Repositories ({starredRepos.length > 0 ? starredRepos.length : 'No'} repositories)
      </h3>
      
      {starredRepos.length > 0 ? (
        <>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {starredRepos.map((repo) => (
              <EnhancedRepositoryCard key={repo.id} repo={repo} />
            ))}
          </div>
          
          {loadingMore && (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {Array.from({ length: 6 }).map((_, i) => (
                <Skeleton key={i} className="h-40" />
              ))}
            </div>
          )}
          
          {!hasMore && starredRepos.length > 0 && (
            <div className="text-center py-8">
              <p className="text-muted-foreground">You've reached the end of starred repositories!</p>
            </div>
          )}
        </>
      ) : (
        <div className="text-center py-12">
          <p className="text-muted-foreground">No starred repositories found.</p>
        </div>
      )}
    </div>
  );
}
