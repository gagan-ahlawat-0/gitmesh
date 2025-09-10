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

interface ProfileOverviewProps {
  username: string;
  user: GitHubUser;
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
      {/* README */}
      {readme && (
        <Card>
          <CardHeader>
            <CardTitle>README</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="prose prose-sm max-w-none dark:prose-invert 
                         prose-headings:text-foreground prose-p:text-foreground 
                         prose-strong:text-foreground prose-code:text-foreground 
                         prose-pre:bg-muted prose-pre:border prose-pre:text-foreground
                         prose-blockquote:border-l-border prose-blockquote:text-muted-foreground
                         prose-ul:text-foreground prose-ol:text-foreground prose-li:text-foreground
                         prose-table:text-foreground prose-th:text-foreground prose-td:text-foreground
                         prose-hr:border-border">
              <ReactMarkdown 
                remarkPlugins={[remarkGfm]}
                rehypePlugins={[rehypeHighlight, rehypeRaw]}
                components={{
                  // Custom heading components
                  h1: ({ children }) => (
                    <h1 className="text-2xl font-bold text-foreground border-b border-border pb-2 mb-4">
                      {children}
                    </h1>
                  ),
                  h2: ({ children }) => (
                    <h2 className="text-xl font-semibold text-foreground border-b border-border pb-2 mb-3 mt-6">
                      {children}
                    </h2>
                  ),
                  h3: ({ children }) => (
                    <h3 className="text-lg font-semibold text-foreground mb-2 mt-4">
                      {children}
                    </h3>
                  ),
                  h4: ({ children }) => (
                    <h4 className="text-base font-semibold text-foreground mb-2 mt-3">
                      {children}
                    </h4>
                  ),
                  h5: ({ children }) => (
                    <h5 className="text-sm font-semibold text-foreground mb-2 mt-3">
                      {children}
                    </h5>
                  ),
                  h6: ({ children }) => (
                    <h6 className="text-xs font-semibold text-foreground mb-2 mt-3">
                      {children}
                    </h6>
                  ),
                  // Custom paragraph component
                  p: ({ children }) => (
                    <p className="text-foreground mb-4 leading-7">
                      {children}
                    </p>
                  ),
                  // Custom list components
                  ul: ({ children }) => (
                    <ul className="list-disc list-inside text-foreground mb-4 space-y-1">
                      {children}
                    </ul>
                  ),
                  ol: ({ children }) => (
                    <ol className="list-decimal list-inside text-foreground mb-4 space-y-1">
                      {children}
                    </ol>
                  ),
                  li: ({ children }) => (
                    <li className="text-foreground">
                      {children}
                    </li>
                  ),
                  // Custom blockquote component
                  blockquote: ({ children }) => (
                    <blockquote className="border-l-4 border-border pl-4 py-2 bg-muted/50 text-muted-foreground italic mb-4">
                      {children}
                    </blockquote>
                  ),
                  // Custom table components
                  table: ({ children }) => (
                    <div className="overflow-x-auto mb-4">
                      <table className="min-w-full border border-border rounded-md">
                        {children}
                      </table>
                    </div>
                  ),
                  thead: ({ children }) => (
                    <thead className="bg-muted">
                      {children}
                    </thead>
                  ),
                  tbody: ({ children }) => (
                    <tbody className="bg-background">
                      {children}
                    </tbody>
                  ),
                  tr: ({ children }) => (
                    <tr className="border-b border-border">
                      {children}
                    </tr>
                  ),
                  th: ({ children }) => (
                    <th className="px-4 py-2 text-left font-semibold text-foreground border-r border-border">
                      {children}
                    </th>
                  ),
                  td: ({ children }) => (
                    <td className="px-4 py-2 text-foreground border-r border-border">
                      {children}
                    </td>
                  ),
                  // Custom horizontal rule
                  hr: () => (
                    <hr className="border-t border-border my-6" />
                  ),
                  // Custom link component to handle GitHub links
                  a: ({ href, children }) => (
                    <a
                      href={href}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-blue-500 hover:text-blue-600 underline transition-colors"
                    >
                      {children}
                    </a>
                  ),
                  // Custom code block styling
                  pre: ({ children }) => (
                    <pre className="bg-muted p-4 rounded-md overflow-x-auto border border-border mb-4">
                      {children}
                    </pre>
                  ),
                  // Custom inline code styling
                  code: ({ children, className }) => {
                    const isInline = !className;
                    return isInline ? (
                      <code className="bg-muted px-2 py-1 rounded text-sm font-mono text-foreground border">
                        {children}
                      </code>
                    ) : (
                      <code className={`${className} text-foreground`}>{children}</code>
                    );
                  },
                  // Custom image styling
                  img: ({ src, alt }) => (
                    <img 
                      src={src} 
                      alt={alt} 
                      className="max-w-full h-auto rounded-md border border-border mb-4"
                    />
                  ),
                }}
              >
                {readme}
              </ReactMarkdown>
            </div>
          </CardContent>
        </Card>
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
    </div>
  );
}
