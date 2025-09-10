"use client";

import { useEffect, useState } from 'react';
import { useAuth } from '@/contexts/AuthContext';
import { Button } from "@/components/ui/button";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Repository } from '@/lib/github-api';
import GitHubAPI from '@/lib/github-api';
import { EnhancedRepositoryCard } from './EnhancedRepositoryCard';
import { Skeleton } from "@/components/ui/skeleton";
import { ChevronLeft, ChevronRight } from "lucide-react";

interface ProfileRepositoriesProps {
  username: string;
}

export function ProfileRepositories({ username }: ProfileRepositoriesProps) {
  const { token } = useAuth();
  const [repositories, setRepositories] = useState<Repository[]>([]);
  const [loading, setLoading] = useState(true);
  const [currentPage, setCurrentPage] = useState(1);
  const [perPage, setPerPage] = useState(30);
  const [sortBy, setSortBy] = useState('updated');
  const [totalPages, setTotalPages] = useState(1);
  const [hasNextPage, setHasNextPage] = useState(false);

  const fetchRepositories = async (page: number, per_page: number, sort: string) => {
    if (!token) return;

    setLoading(true);
    try {
      const api = new GitHubAPI(token);
      const response = await api.getPublicUserRepositories(username, page, per_page, sort);
      setRepositories(response.repositories || []);
      setHasNextPage(response.has_next_page || false);
      
      // Calculate total pages based on response headers or estimate
      if (response.total_count) {
        setTotalPages(Math.ceil(response.total_count / per_page));
      }
    } catch (error) {
      console.error('Failed to fetch repositories:', error);
      setRepositories([]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (username && token) {
      fetchRepositories(currentPage, perPage, sortBy);
    }
  }, [username, token, currentPage, perPage, sortBy]);

  const handlePageChange = (newPage: number) => {
    setCurrentPage(newPage);
  };

  const handlePerPageChange = (newPerPage: string) => {
    setPerPage(parseInt(newPerPage));
    setCurrentPage(1);
  };

  const handleSortChange = (newSort: string) => {
    setSortBy(newSort);
    setCurrentPage(1);
  };

  if (loading) {
    return (
      <div className="space-y-6">
        <div className="flex justify-between items-center">
          <Skeleton className="h-8 w-32" />
          <div className="flex space-x-4">
            <Skeleton className="h-10 w-32" />
            <Skeleton className="h-10 w-32" />
            <Skeleton className="h-10 w-24" />
          </div>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {Array.from({ length: perPage }).map((_, i) => (
            <Skeleton key={i} className="h-40" />
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Controls */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
        <h3 className="text-xl font-semibold">
          Repositories ({repositories.length > 0 ? 'Showing' : 'No'} results)
        </h3>
        
        <div className="flex flex-col sm:flex-row gap-4">
          {/* Sort By */}
          <Select value={sortBy} onValueChange={handleSortChange}>
            <SelectTrigger className="w-40">
              <SelectValue placeholder="Sort by" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="updated">Last updated</SelectItem>
              <SelectItem value="created">Recently created</SelectItem>
              <SelectItem value="pushed">Recently pushed</SelectItem>
              <SelectItem value="full_name">Name</SelectItem>
            </SelectContent>
          </Select>

          {/* Per Page */}
          <Select value={perPage.toString()} onValueChange={handlePerPageChange}>
            <SelectTrigger className="w-24">
              <SelectValue placeholder="Per page" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="10">10</SelectItem>
              <SelectItem value="30">30</SelectItem>
              <SelectItem value="50">50</SelectItem>
              <SelectItem value="100">100</SelectItem>
            </SelectContent>
          </Select>
        </div>
      </div>

      {/* Repositories Grid */}
      {repositories.length > 0 ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {repositories.map((repo) => (
            <EnhancedRepositoryCard key={repo.id} repo={repo} />
          ))}
        </div>
      ) : (
        <div className="text-center py-12">
          <p className="text-muted-foreground">No repositories found.</p>
        </div>
      )}

      {/* Pagination */}
      {repositories.length > 0 && (totalPages > 1 || hasNextPage) && (
        <div className="flex justify-center items-center space-x-4">
          <Button
            variant="outline"
            size="sm"
            onClick={() => handlePageChange(currentPage - 1)}
            disabled={currentPage === 1}
          >
            <ChevronLeft className="w-4 h-4 mr-1" />
            Previous
          </Button>
          
          <span className="text-sm text-muted-foreground">
            Page {currentPage} {totalPages > 1 && `of ${totalPages}`}
          </span>
          
          <Button
            variant="outline"
            size="sm"
            onClick={() => handlePageChange(currentPage + 1)}
            disabled={!hasNextPage && currentPage >= totalPages}
          >
            Next
            <ChevronRight className="w-4 h-4 ml-1" />
          </Button>
        </div>
      )}
    </div>
  );
}
