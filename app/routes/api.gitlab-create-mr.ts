import { json, type ActionFunctionArgs } from '@remix-run/cloudflare';
import { logStore } from '~/lib/stores/logs';

interface CreateMRRequest {
  projectId: string;
  title: string;
  description?: string;
  sourceBranch: string;
  targetBranch: string;
  token: string;
  gitlabUrl?: string;
}

interface GitLabMRResponse {
  iid: number;
  web_url: string;
  title: string;
  source_branch: string;
  target_branch: string;
  state: string;
  created_at: string;
}

/**
 * API route to create a GitLab Merge Request
 * POST /api/gitlab-create-mr
 */
export async function action({ request }: ActionFunctionArgs) {
  try {
    const body = (await request.json()) as CreateMRRequest;
    const { projectId, title, description, sourceBranch, targetBranch, token, gitlabUrl } = body;

    // Validate required fields
    if (!projectId || !title || !sourceBranch || !targetBranch || !token) {
      return json(
        {
          error: 'Missing required fields: projectId, title, sourceBranch, targetBranch, token',
        },
        { status: 400 },
      );
    }

    const baseUrl = gitlabUrl || 'https://gitlab.com';

    logStore.logProvider('Creating GitLab MR', {
      component: 'MRCreation',
      action: 'create',
      projectId,
      sourceBranch,
      targetBranch,
    });

    // Encode project ID for URL
    const encodedProjectId = encodeURIComponent(projectId);

    // Create merge request using GitLab API
    const response = await fetch(`${baseUrl}/api/v4/projects/${encodedProjectId}/merge_requests`, {
      method: 'POST',
      headers: {
        Authorization: `Bearer ${token}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        title,
        description: description || '',
        sourceBranch,
        targetBranch,
        remove_source_branch: false,
      }),
    });

    if (!response.ok) {
      const errorData = (await response.json()) as { message?: string };
      logStore.logError('Failed to create GitLab MR', {
        status: response.status,
        error: errorData,
      });

      return json(
        {
          error: errorData.message || 'Failed to create merge request',
          details: errorData,
        },
        { status: response.status },
      );
    }

    const mrData = (await response.json()) as GitLabMRResponse;

    logStore.logProvider('GitLab MR created successfully', {
      component: 'MRCreation',
      action: 'created',
      mrId: mrData.iid,
      mrUrl: mrData.web_url,
    });

    return json({
      success: true,
      mr: {
        iid: mrData.iid,
        url: mrData.web_url,
        title: mrData.title,
        sourceBranch: mrData.source_branch,
        targetBranch: mrData.target_branch,
        state: mrData.state,
        created_at: mrData.created_at,
      },
    });
  } catch (error: any) {
    logStore.logError('Error creating GitLab MR', {
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
