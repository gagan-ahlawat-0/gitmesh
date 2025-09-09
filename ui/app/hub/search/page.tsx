"use client";

import { useSearchParams } from 'next/navigation';
import { Suspense } from 'react';
import { SearchResults } from '@/components/hub/search/SearchResults';
import { HubHeader } from '@/components/hub/HubHeader';

function SearchPageContent() {
  const searchParams = useSearchParams();
  const query = searchParams.get('q') || '';

  return (
    <div className="container mx-auto p-4 sm:p-6 lg:p-8">
      <HubHeader
        title="Search Results"
        subtitle={query ? `Showing results for "${query}"` : 'Please enter a search term'}
      />
      {query ? (
        <SearchResults query={query} />
      ) : (
        <div className="text-center text-gray-500 dark:text-gray-400 mt-8">
          <p>Search for repositories, users, and organizations on GitHub.</p>
        </div>
      )}
    </div>
  );
}

export default function SearchPage() {
  return (
    <Suspense fallback={<div>Loading...</div>}>
      <SearchPageContent />
    </Suspense>
  );
}
