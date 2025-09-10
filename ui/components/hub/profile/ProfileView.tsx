"use client";

import { useEffect, useState } from 'react';
import { useAuth } from '@/contexts/AuthContext';
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { ProfileHeader } from './ProfileHeader';
import { ProfileOverview } from './ProfileOverview';
import { ProfileRepositories } from './ProfileRepositories';
import { ProfileActivity } from './ProfileActivity';
import { ProfileStarred } from './ProfileStarred';
import { ProfileSkeleton } from './ProfileSkeleton';
import { GitHubUser } from '@/lib/types';
import GitHubAPI from '@/lib/github-api';

interface ProfileViewProps {
  username: string;
  isOwnProfile?: boolean;
}

export function ProfileView({ username, isOwnProfile = false }: ProfileViewProps) {
  const { token } = useAuth();
  const [user, setUser] = useState<GitHubUser | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isFollowing, setIsFollowing] = useState(false);

  useEffect(() => {
    if (username && token) {
      const fetchUserProfile = async () => {
        setLoading(true);
        setError(null);
        try {
          const api = new GitHubAPI(token);
          const userData = await api.getGitHubUserProfile(username);
          
          // Fetch organizations
          try {
            const orgsData = await api.getUserOrganizations(username);
            userData.organizations = orgsData;
          } catch (orgError) {
            console.warn('Failed to fetch organizations:', orgError);
            userData.organizations = [];
          }
          
          setUser(userData);
          
          // Check if following (only if not own profile)
          if (!isOwnProfile) {
            const followingStatus = await api.isFollowingUser(username);
            setIsFollowing(followingStatus);
          }
        } catch (err: any) {
          setError(err.message || 'Failed to fetch user profile');
        } finally {
          setLoading(false);
        }
      };
      fetchUserProfile();
    }
  }, [username, token, isOwnProfile]);

  const handleFollowToggle = async () => {
    if (!token || !user || isOwnProfile) return;

    try {
      const api = new GitHubAPI(token);
      if (isFollowing) {
        await api.unfollowUser(username);
        setIsFollowing(false);
        setUser(prev => prev ? { ...prev, followers: prev.followers - 1 } : null);
      } else {
        await api.followUser(username);
        setIsFollowing(true);
        setUser(prev => prev ? { ...prev, followers: prev.followers + 1 } : null);
      }
    } catch (err) {
      console.error('Failed to toggle follow status:', err);
    }
  };

  if (loading) {
    return <ProfileSkeleton />;
  }

  if (error) {
    return (
      <div className="container mx-auto p-4 sm:p-6 lg:p-8">
        <div className="text-center">
          <p className="text-red-500">Error: {error}</p>
        </div>
      </div>
    );
  }

  if (!user) {
    return (
      <div className="container mx-auto p-4 sm:p-6 lg:p-8">
        <div className="text-center">
          <p>User not found.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <ProfileHeader 
        user={user} 
        isOwnProfile={isOwnProfile}
        isFollowing={isFollowing}
        onFollowToggle={handleFollowToggle}
      />
      
      <Tabs defaultValue="overview" className="w-full">
        <TabsList className="grid w-full grid-cols-4">
          <TabsTrigger value="overview">Overview</TabsTrigger>
          <TabsTrigger value="repositories">Repositories</TabsTrigger>
          <TabsTrigger value="activity">Activity</TabsTrigger>
          <TabsTrigger value="starred">Starred</TabsTrigger>
        </TabsList>
        
        <TabsContent value="overview" className="mt-6">
          <ProfileOverview username={username} user={user} />
        </TabsContent>
        
        <TabsContent value="repositories" className="mt-6">
          <ProfileRepositories username={username} />
        </TabsContent>
        
        <TabsContent value="activity" className="mt-6">
          <ProfileActivity username={username} />
        </TabsContent>
        
        <TabsContent value="starred" className="mt-6">
          <ProfileStarred username={username} />
        </TabsContent>
      </Tabs>
    </div>
  );
}
