"use client";

import { useState, useEffect, useCallback } from 'react';
import { useAuth } from '@/contexts/AuthContext';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Activity, RefreshCw } from 'lucide-react';
import { UserActivity, Repository } from "@/lib/github-api";
import { Timeline } from '@/components/hub/activity/Timeline';
import { HubActivitySkeleton } from '@/components/hub/activity/HubActivitySkeleton';
import { ActivityFilters } from '@/components/hub/activity/ActivityFilters';

const ITEMS_PER_PAGE = 5;

export default function HubActivityPage() {
  const { user, githubApi } = useAuth();
  const [loading, setLoading] = useState(true);
  const [activities, setActivities] = useState<UserActivity[]>([]);
  const [filteredActivities, setFilteredActivities] = useState<UserActivity[]>([]);
  const [refreshing, setRefreshing] = useState(false);
  const [filters, setFilters] = useState<any>({ repository: "all", dateRange: null });
  const [repositories, setRepositories] = useState<Repository[]>([]);
  const [currentPage, setCurrentPage] = useState(1);

  const fetchActivities = useCallback(async () => {
    if (!githubApi) return;

    setLoading(true);
    const api = githubApi;
    try {
      const [userActivities, repos] = await Promise.all([
        api.getUserActivity(user?.login),
        api.getUserRepositories(),
      ]);
      setActivities(userActivities);
      setFilteredActivities(userActivities);
      setRepositories(repos);
    } catch (error) {
      console.error('Error fetching activities:', error);
    } finally {
      setLoading(false);
    }
  }, [githubApi, user?.login]);

  const refreshActivities = useCallback(async () => {
    setRefreshing(true);
    await fetchActivities();
    setRefreshing(false);
  }, [fetchActivities]);

  useEffect(() => {
    fetchActivities();
  }, [fetchActivities]);

  useEffect(() => {
    let filtered = activities;

    if (filters.repository !== "all") {
      filtered = filtered.filter((activity) => activity.repo.name === filters.repository);
    }

    if (filters.dateRange) {
      filtered = filtered.filter((activity) => {
        const activityDate = new Date(activity.created_at);
        return activityDate >= filters.dateRange.from && activityDate <= filters.dateRange.to;
      });
    }

    setFilteredActivities(filtered);
    setCurrentPage(1);
  }, [filters, activities]);

  const groupedActivities = filteredActivities.reduce((acc, activity) => {
    const date = new Date(activity.created_at).toLocaleDateString();
    if (!acc[date]) {
      acc[date] = [];
    }
    acc[date].push(activity);
    return acc;
  }, {} as { [key: string]: UserActivity[] });

  const dates = Object.keys(groupedActivities);
  const totalPages = Math.ceil(dates.length / ITEMS_PER_PAGE);
  const paginatedDates = dates.slice(
    (currentPage - 1) * ITEMS_PER_PAGE,
    currentPage * ITEMS_PER_PAGE
  );

  if (loading) {
    return <HubActivitySkeleton />;
  }

  return (
    <div className="min-h-screen bg-black text-white">
      <div className="container mx-auto p-4 sm:p-6 lg:p-8">
        <div className="flex flex-col md:flex-row items-start md:items-center justify-between mb-8">
          <div className="mb-4 md:mb-0">
            <h2 className="text-3xl font-bold flex items-center gap-3">
              <Activity className="w-8 h-8 text-orange-500" />
              Activity Feed
            </h2>
            <p className="text-gray-400 mt-2">
              Recent activity across all your repositories.
            </p>
          </div>
          <div className="flex items-center gap-4 w-full md:w-auto">
            <ActivityFilters repositories={repositories} onFilterChange={setFilters} />
            <Button
              variant="outline"
              size="sm"
              onClick={refreshActivities}
              disabled={refreshing}
              className="flex items-center gap-2 bg-gray-800 text-white hover:bg-gray-700 border-gray-700"
            >
              <RefreshCw className={`w-4 h-4 ${refreshing ? 'animate-spin' : ''}`} />
              Refresh
            </Button>
          </div>
        </div>
        <Card className="bg-gray-900 shadow-lg rounded-lg">
          <CardHeader>
            <CardTitle className="text-xl font-bold text-white">Recent Activity</CardTitle>
            <CardDescription className="text-gray-400">
              Latest updates and changes from your repositories.
            </CardDescription>
          </CardHeader>
          <CardContent>
            {paginatedDates.length > 0 ? (
              paginatedDates.map((date) => (
                <div key={date}>
                  <h3 className="text-lg font-semibold my-4 text-gray-300">{date}</h3>
                  <Timeline activities={groupedActivities[date]} />
                </div>
              ))
            ) : (
              <div className="text-center py-12">
                <Activity className="w-12 h-12 text-gray-500 mx-auto mb-4" />
                <h3 className="text-lg font-semibold mb-2">No Activity Yet</h3>
                <p className="text-gray-400">
                  No activities found for the selected filter.
                </p>
              </div>
            )}
            {totalPages > 1 && (
              <div className="flex justify-center mt-8">
                <Button
                  onClick={() => setCurrentPage((prev) => Math.max(prev - 1, 1))}
                  disabled={currentPage === 1}
                  className="bg-orange-500 text-black hover:bg-orange-600 disabled:bg-gray-700"
                >
                  Previous
                </Button>
                <span className="mx-4 text-white">Page {currentPage} of {totalPages}</span>
                <Button
                  onClick={() => setCurrentPage((prev) => Math.min(prev + 1, totalPages))}
                  disabled={currentPage === totalPages}
                  className="bg-orange-500 text-black hover:bg-orange-600 disabled:bg-gray-700"
                >
                  Next
                </Button>
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
