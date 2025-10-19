import { json } from '@remix-run/cloudflare';
import { withSecurity } from '~/lib/security';
import type { GitHubRepoInfo } from '~/types/GitHub';

const GITHUB_API_URL = 'https://api.github.com/search/repositories';

async function publicReposLoader({ request }: { request: Request }) {
  try {
    const body: any = await request.json();
    const { token, query = '' } = body;

    // Ignore if query is less than 3 characters
    if (!query.trim() || query.trim().length < 3) {
      return json({ repositories: [], total: 0 }, { status: 200 });
    }

    if (!token) {
      return json({ error: 'GitHub token is required' }, { status: 400 });
    }

    // Fetch top 50 results
    const url = `${GITHUB_API_URL}?q=${encodeURIComponent(query)}&per_page=50&sort=stars&order=desc`;

    const headers: Record<string, string> = {
      Accept: 'application/vnd.github.v3+json',
      'User-Agent': 'gitmesh.diy-app',
    };

    if (token) {
      headers.Authorization = `Bearer ${token}`;
    }

    const response = await fetch(url, { headers });

    if (!response.ok) {
      if (response.status === 401) {
        return json({ error: 'Invalid GitHub token' }, { status: 401 });
      }

      const errorText = await response.text().catch(() => 'Unknown error');
      console.error('GitHub API error:', response.status, errorText);

      return json(
        { error: `Failed to fetch public repositories: ${response.statusText}` },
        { status: response.status },
      );
    }

    const jsonData: any = await response.json();
    const data: GitHubRepoInfo[] = jsonData.items;

    const transformedRepositories: GitHubRepoInfo[] = data.map((repo) => ({
      id: repo.id.toString(),
      name: repo.name,
      full_name: repo.full_name,
      html_url: repo.html_url,
      description: repo.description,
      stargazers_count: repo.stargazers_count,
      forks_count: repo.forks_count,
      default_branch: repo.default_branch,
      updated_at: repo.updated_at,
      language: repo.language,
      languages_url: repo.languages_url,
      private: repo.private,
      topics: repo.topics,
      archived: repo.archived,
      fork: repo.fork,
      size: repo.size,
      contributors_count: repo.contributors_count,
      branches_count: repo.branches_count,
      issues_count: repo.issues_count,
      pull_requests_count: repo.pull_requests_count,
      license: repo.license ? { name: repo.license.name, spdx_id: repo.license.spdx_id } : undefined,
    }));

    return json({
      repositories: transformedRepositories.slice(0, 50),
      total: transformedRepositories.length,
    });
  } catch (error) {
    console.error('Failed to fetch Public Repositories:', error);
    return json(
      {
        error:
          error instanceof Error
            ? `Failed to fetch Public Repositories: ${error.message}`
            : 'An unexpected error occurred while fetching repositories.',
      },
      { status: 500 },
    );
  }
}

export const action = withSecurity(publicReposLoader);
