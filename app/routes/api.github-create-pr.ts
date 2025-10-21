import { json, type ActionFunctionArgs } from '@remix-run/cloudflare';
import { logStore } from '~/lib/stores/logs';

interface CreatePRRequest {
  owner: string;
  repo: string;
  title: string;
  body?: string;
  head: string;
  base: string;
  token: string;
}

interface GitHubPRResponse {
  number: number;
  html_url: string;
  title: string;
  head: { ref: string };
  base: { ref: string };
  state: string;
  created_at: string;
}

/**
 * API route to create a GitHub Pull Request
 * POST /api/github-create-pr
 */
export async function action({ request }: ActionFunctionArgs) {
  try {
    const body = (await request.json()) as CreatePRRequest;
    const { owner, repo, title, body: prBody, head, base, token } = body;

    // Validate required fields
    if (!owner || !repo || !title || !head || !base || !token) {
      return json(
        {
          error: 'Missing required fields: owner, repo, title, head, base, token',
        },
        { status: 400 },
      );
    }

    logStore.logProvider('Creating GitHub PR', {
      component: 'PRCreation',
      action: 'create',
      owner,
      repo,
      head,
      base,
    });

    // Create pull request using GitHub API
    const response = await fetch(`https://api.github.com/repos/${owner}/${repo}/pulls`, {
      method: 'POST',
      headers: {
        Authorization: `Bearer ${token}`,
        Accept: 'application/vnd.github.v3+json',
        'Content-Type': 'application/json',
        'User-Agent': 'GitMesh',
      },
      body: JSON.stringify({
        title,
        body: prBody || '',
        head,
        base,
        maintainer_can_modify: true,
      }),
    });

    if (!response.ok) {
      const errorData = (await response.json()) as {
        message?: string;
        errors?: Array<{ message: string; field?: string }>;
        documentation_url?: string;
      };

      logStore.logError('Failed to create GitHub PR', {
        status: response.status,
        error: errorData,
        requestData: { owner, repo, head, base },
      });

      // Provide more specific error messages
      let errorMessage = errorData.message || 'Failed to create pull request';

      if (errorData.errors && errorData.errors.length > 0) {
        const errorDetails = errorData.errors.map((e) => e.message).join(', ');
        errorMessage = `${errorMessage}: ${errorDetails}`;
      }

      // Common error scenarios
      if (response.status === 422) {
        errorMessage = `Validation failed. Please check:\n- The source branch (${head}) exists on GitHub\n- The target branch (${base}) exists\n- There are no existing PRs with the same branches\n- You have push access to the repository`;
      }

      return json(
        {
          error: errorMessage,
          details: errorData,
        },
        { status: response.status },
      );
    }

    const prData = (await response.json()) as GitHubPRResponse;

    logStore.logProvider('GitHub PR created successfully', {
      component: 'PRCreation',
      action: 'created',
      prNumber: prData.number,
      prUrl: prData.html_url,
    });

    return json({
      success: true,
      pr: {
        number: prData.number,
        url: prData.html_url,
        title: prData.title,
        head: prData.head.ref,
        base: prData.base.ref,
        state: prData.state,
        created_at: prData.created_at,
      },
    });
  } catch (error: any) {
    logStore.logError('Error creating GitHub PR', {
      error: error.message,
    });

    return json(
      {
        error: 'Internal server error',
        details: error.message,
      },
      { status: 500 },
    );
  }
}
