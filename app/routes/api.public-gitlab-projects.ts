import { json } from '@remix-run/cloudflare';
import { withSecurity } from '~/lib/security';
import type { GitLabProjectInfo } from '~/types/GitLab';

const GITLAB_API_URL = 'https://gitlab.com/api/v4/projects';

async function fetchPublicGitlabProjects({ request }: { request: Request }) {
  try {
    const body: any = await request.json();
    const { token, query = '' } = body;

    // Ignore if query is less than 3 characters
    if (!query.trim() || query.trim().length < 3) {
      return json({ projects: [], total: 0 }, { status: 200 });
    }

    if (!token) {
      return json({ error: 'GitLab token is required' }, { status: 400 });
    }

    // Fetch top 50 results
    const url = `${GITLAB_API_URL}?search=${encodeURIComponent(query)}&per_page=50&order_by=updated_at&sort=desc`;

    const headers: Record<string, string> = {
      Accept: 'application/json',
      'User-Agent': 'gitmesh.diy-app',
    };

    if (token) {
      headers.Authorization = `Bearer ${token}`;
    }

    const response = await fetch(url, { headers });

    if (!response.ok) {
      if (response.status === 401) {
        return json({ error: 'Invalid GitLab token' }, { status: 401 });
      }

      const errorText = await response.text().catch(() => 'Unknown error');
      console.error('GitLab API error:', response.status, errorText);

      return json({ error: 'Failed to fetch projects' }, { status: 500 });
    }

    const jsonData: any = await response.json();
    const data: GitLabProjectInfo[] = jsonData.items;

    const transformedProjects: GitLabProjectInfo[] = data.map((project: GitLabProjectInfo) => ({
      id: project.id,
      name: project.name,
      path_with_namespace: project.path_with_namespace,
      description: project.description,
      http_url_to_repo: project.http_url_to_repo,
      star_count: project.star_count || 0,
      forks_count: project.forks_count || 0,
      updated_at: project.updated_at,
      default_branch: project.default_branch,
      visibility: project.visibility,
    }));

    return json({
      projects: transformedProjects.slice(0, 50),
      total: transformedProjects.length,
    });
  } catch (error) {
    console.error('Error fetching public GitLab projects:', error);
    return json(
      {
        error:
          error instanceof Error
            ? `Failed to fetch public GitLab projects: ${error.message}`
            : 'Failed to fetch public GitLab projects',
      },
      { status: 500 },
    );
  }
}

export const action = withSecurity(fetchPublicGitlabProjects);
