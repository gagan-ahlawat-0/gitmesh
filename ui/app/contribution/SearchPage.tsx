"use client";

import React, { useState } from 'react';
import { SearchResults } from '@/components/hub/search/SearchResults';
import { SearchBar } from '@/components/hub/projects/SearchBar';
import { AnimatedTransition } from '@/components/AnimatedTransition';
import { useAnimateIn } from '@/lib/animations';

const SearchPage = () => {
  const showContent = useAnimateIn(false, 300);
  const [query, setQuery] = useState<string>('');
  
  return (
    <div className="max-w-full mx-auto px-4 pt-20 overflow-hidden fixed bottom-0 left-0 right-0 h-screen">
      <AnimatedTransition show={showContent} animation="slide-up">
        <div className="h-[calc(100vh-80px)]">
          <div className="container mx-auto p-4 sm:p-6 lg:p-8">
            <div className="mb-6">
              <SearchBar onSearch={setQuery} />
            </div>
            {query ? (
              <SearchResults query={query} />
            ) : (
              <div className="text-center text-gray-500 dark:text-gray-400 mt-8">
                <p>Search for repositories, users, and organizations on GitHub.</p>
              </div>
            )}
          </div>
        </div>
      </AnimatedTransition>
    </div>
  );
};

export default SearchPage;
