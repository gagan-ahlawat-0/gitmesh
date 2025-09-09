"use client";

import { useEffect, useState } from 'react';
import { useAuth } from '@/contexts/AuthContext';
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { RepositoryCard } from './RepositoryCard';
import { UserCard } from './UserCard';
import { OrganizationCard } from './OrganizationCard';

interface SearchResultsProps {
  query: string;
}

export function SearchResults({ query }: SearchResultsProps) {
  const { token } = useAuth();
  const [results, setResults] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (query && token) {
      const fetchResults = async () => {
        setLoading(true);
        setError(null);
        try {
          const response = await fetch(`/api/v1/search?q=${encodeURIComponent(query)}`, {
            headers: {
              Authorization: `Bearer ${token}`,
            },
          });
          if (!response.ok) {
            throw new Error('Failed to fetch search results');
          }
          const data = await response.json();
          setResults(data);
        } catch (err) {
          setError(err.message);
        } finally {
          setLoading(false);
        }
      };
      fetchResults();
    }
  }, [query, token]);

  if (loading) {
    return <div>Loading...</div>;
  }

  if (error) {
    return <div>Error: {error}</div>;
  }

  if (!results) {
    return <div>No results found.</div>;
  }

  return (
    <Tabs defaultValue="repositories" className="w-full mt-6">
      <TabsList className="grid w-full grid-cols-3">
        <TabsTrigger value="repositories">Repositories ({results.repositories?.length || 0})</TabsTrigger>
        <TabsTrigger value="users">Users ({results.users?.length || 0})</TabsTrigger>
        <TabsTrigger value="organizations">Organizations ({results.organizations?.length || 0})</TabsTrigger>
      </TabsList>
      <TabsContent value="repositories">
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 mt-4">
          {results.repositories?.map((repo: any) => (
            <RepositoryCard key={repo.id} repo={repo} />
          ))}
        </div>
      </TabsContent>
      <TabsContent value="users">
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 mt-4">
          {results.users?.map((user: any) => (
            <UserCard key={user.id} user={user} />
          ))}
        </div>
      </TabsContent>
      <TabsContent value="organizations">
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 mt-4">
          {results.organizations?.map((org: any) => (
            <OrganizationCard key={org.id} org={org} />
          ))}
        </div>
      </TabsContent>
    </Tabs>
  );
}
