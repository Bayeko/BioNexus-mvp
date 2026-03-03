import type { ConnectorPlugin, ToolDefinition } from '../types.js';

export class GitHubPlugin implements ConnectorPlugin {
  name = 'github';
  displayName = 'GitHub';
  description = 'Access GitHub repositories — commits, PRs, and file tracking';

  private initialized = false;
  private owner = '';
  private repo = '';

  tools: ToolDefinition[] = [
    {
      name: 'list_recent_commits',
      description: 'List recent commits on the default branch',
      input_schema: {
        type: 'object',
        properties: {
          since: { type: 'string', description: 'ISO 8601 date — only commits after this date' },
          per_page: { type: 'number', description: 'Number of commits to return (default 20)' },
        },
      },
    },
    {
      name: 'list_pull_requests',
      description: 'List pull requests with optional state filter',
      input_schema: {
        type: 'object',
        properties: {
          state: { type: 'string', description: 'Filter by state: open, closed, or all (default open)' },
          per_page: { type: 'number', description: 'Number of PRs to return (default 10)' },
        },
      },
    },
    {
      name: 'list_recently_changed_files',
      description: 'List files that were created or modified in recent commits',
      input_schema: {
        type: 'object',
        properties: {
          since: { type: 'string', description: 'ISO 8601 date — only changes after this date' },
          path_filter: { type: 'string', description: 'Optional path prefix filter (e.g. "docs/")' },
        },
      },
    },
  ];

  async executeTool(name: string, input: Record<string, unknown>): Promise<unknown> {
    if (!this.initialized) {
      return { error: 'GitHub not configured. Set GITHUB_TOKEN in .env' };
    }

    switch (name) {
      case 'list_recent_commits':
        return { commits: [], message: `Would list commits since ${input.since ?? 'last week'} for ${this.owner}/${this.repo}` };
      case 'list_pull_requests':
        return { pull_requests: [], message: `Would list ${input.state ?? 'open'} PRs for ${this.owner}/${this.repo}` };
      case 'list_recently_changed_files':
        return { files: [], message: `Would list changed files since ${input.since ?? 'last week'}` };
      default:
        return { error: `Unknown tool: ${name}` };
    }
  }

  async healthCheck(): Promise<{ ok: boolean; message?: string }> {
    if (!this.initialized) {
      return { ok: false, message: 'Not configured — set GITHUB_TOKEN in .env' };
    }
    // TODO: Make a test API call (octokit.rest.repos.get)
    return { ok: true, message: `Connected to ${this.owner}/${this.repo}` };
  }

  async initialize(_config: Record<string, string>): Promise<void> {
    const token = process.env.GITHUB_TOKEN;
    this.owner = process.env.GITHUB_OWNER || 'Bayeko';
    this.repo = process.env.GITHUB_REPO || 'BioNexus-mvp';

    if (token) {
      // TODO: Initialize Octokit with auth token
      this.initialized = true;
    }
  }

  async shutdown(): Promise<void> {
    this.initialized = false;
  }
}
