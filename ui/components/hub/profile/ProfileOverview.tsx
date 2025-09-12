"use client";

import { useEffect, useState } from 'react';
import { useAuth } from '@/contexts/AuthContext';
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { GitHubUser } from '@/lib/types';
import { Repository } from '@/lib/github-api';
import GitHubAPI from '@/lib/github-api';
import { EnhancedRepositoryCard } from './EnhancedRepositoryCard';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import rehypeHighlight from 'rehype-highlight';
import rehypeRaw from 'rehype-raw';
import { Skeleton } from "@/components/ui/skeleton";
import 'highlight.js/styles/github.css';

// Define the props for our component
interface ReadmeCardProps {
  readmeContent: string;
  githubRepoUrl: string; // e.g., "https://github.com/shadcn-ui/ui"
}

interface ProfileOverviewProps {
  username: string;
  user: GitHubUser;
}

export function ReadmeCard({ readmeContent, githubRepoUrl }: ReadmeCardProps) {
  // Function to construct the absolute URL for images from the repo URL
  const getImageUrl = (src: string) => {
    // If the src is already an absolute URL, return it as is
    if (src.startsWith("http")) {
      return src;
    }

    try {
      // Parse the main repo URL to get the owner and repo name
      const url = new URL(githubRepoUrl);
      const [_, owner, repo] = url.pathname.split("/");
      
      // Assume the default branch is 'main'. For more complex cases, this could be a prop.
      // Handles both './path' and 'path' formats
      const cleanedSrc = src.startsWith("./") ? src.substring(2) : src;

      return `https://raw.githubusercontent.com/${owner}/${repo}/main/${cleanedSrc}`;
    } catch (error) {
      console.error("Invalid GitHub repo URL provided:", githubRepoUrl);
      return src; // Fallback to the original src if URL parsing fails
    }
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle>README</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="prose prose-sm max-w-none dark:prose-invert 
                     prose-headings:text-foreground prose-p:text-foreground 
                     prose-strong:text-foreground prose-code:text-foreground 
                     prose-pre:bg-muted prose-pre:border prose-pre:p-4 prose-pre:rounded-md
                     prose-blockquote:border-l-border prose-blockquote:text-muted-foreground
                     prose-a:text-blue-500 prose-a:no-underline hover:prose-a:underline
                     prose-hr:border-border">
          <ReactMarkdown
            remarkPlugins={[remarkGfm]}
            rehypePlugins={[rehypeHighlight, rehypeRaw]}
            components={{
              // Override 'a' tag to open links in a new tab
              a: ({ href, children }) => (
                <a href={href} target="_blank" rel="noopener noreferrer">
                  {children}
                </a>
              ),
              // Override 'img' to fix relative paths
              img: ({ src, alt }) => (
                <img
                  src={getImageUrl(src || "")}
                  alt={alt}
                  className="max-w-full rounded-md border border-border"
                />
              ),
              // Keep custom code styling for syntax highlighting from rehype-highlight
              code: ({ children, className }) => {
                // Inline code will not have a className from rehype-highlight
                const isInline = !className;
                return isInline ? (
                  <code className="bg-muted px-1.5 py-0.5 rounded-sm text-sm font-mono border">
                    {children}
                  </code>
                ) : (
                  // Code block (handled by <pre>)
                  <code className={className}>{children}</code>
                );
              },
            }}
          >
            {readmeContent}
          </ReactMarkdown>
        </div>
      </CardContent>
    </Card>
  );
}

export function ProfileOverview({ username, user }: ProfileOverviewProps) {
  const { token } = useAuth();
  const [readme, setReadme] = useState<string | null>(null);
  const [pinnedRepos, setPinnedRepos] = useState<Repository[]>([]);
  const [recentRepos, setRecentRepos] = useState<Repository[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (username && token) {
      const fetchOverviewData = async () => {
        setLoading(true);
        try {
          const api = new GitHubAPI(token);
          
          // Fetch README, pinned repos, and recent repos in parallel
          const [readmeContent, pinnedReposData, recentReposData] = await Promise.allSettled([
            api.getUserReadme(username),
            api.getUserPinnedRepos(username),
            api.getPublicUserRepositories(username, 1, 6, 'updated')
          ]);

          if (readmeContent.status === 'fulfilled') {
            setReadme(readmeContent.value);
          }

          if (pinnedReposData.status === 'fulfilled') {
            setPinnedRepos(pinnedReposData.value);
          }

          if (recentReposData.status === 'fulfilled') {
            setRecentRepos(recentReposData.value.repositories || []);
          }
        } catch (error) {
          console.error('Failed to fetch overview data:', error);
        } finally {
          setLoading(false);
        }
      };

      fetchOverviewData();
    }
  }, [username, token]);

  if (loading) {
    return (
      <div className="space-y-6">
        <Card>
          <CardHeader>
            <Skeleton className="h-6 w-32" />
          </CardHeader>
          <CardContent>
            <Skeleton className="h-32 w-full" />
          </CardContent>
        </Card>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {Array.from({ length: 6 }).map((_, i) => (
            <Skeleton key={i} className="h-40" />
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Contribution Stats */}
      <Card>
        <CardHeader>
          <CardTitle>Contribution Statistics</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className="text-center">
              <div className="text-2xl font-bold">{user.public_repos}</div>
              <div className="text-sm text-muted-foreground">Public Repos</div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-bold">{user.followers}</div>
              <div className="text-sm text-muted-foreground">Followers</div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-bold">{user.following}</div>
              <div className="text-sm text-muted-foreground">Following</div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-bold">
                {new Date().getFullYear() - new Date(user.created_at).getFullYear()}
              </div>
              <div className="text-sm text-muted-foreground">Years on GitHub</div>
            </div>
          </div>
        </CardContent>
      </Card>
      {/* README */}
      {readme && (
        <ReadmeCard 
          readmeContent={readme} 
          githubRepoUrl={`https://github.com/${username}`} 
        />
      )}

      {/* Pinned Repositories */}
      {pinnedRepos.length > 0 && (
        <div>
          <h3 className="text-xl font-semibold mb-4">Pinned Repositories</h3>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {pinnedRepos.map((repo) => (
              <EnhancedRepositoryCard key={repo.id} repo={repo} />
            ))}
          </div>
        </div>
      )}

      {/* Recent Repositories */}
      {recentRepos.length > 0 && (
        <div>
          <h3 className="text-xl font-semibold mb-4">Recently Updated Repositories</h3>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {recentRepos.map((repo) => (
              <EnhancedRepositoryCard key={repo.id} repo={repo} />
            ))}
          </div>
        </div>
      )}

    </div>
  );
}
