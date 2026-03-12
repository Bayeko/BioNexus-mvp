import { Octokit } from '@octokit/rest';
import type { ConnectorPlugin, ToolDefinition } from '../types.js';

export class GitHubPlugin implements ConnectorPlugin {
  name = 'github';
  displayName = 'GitHub';
  description = 'Access GitHub repositories — commits, PRs, and file tracking';

  private octokit: Octokit | null = null;
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
    {
      name: 'get_file_content',
      description: 'Get the text content of a file from the repository',
      input_schema: {
        type: 'object',
        properties: {
          path: { type: 'string', description: 'File path relative to repo root (e.g. "docs/API_REFERENCE.md")' },
          ref: { type: 'string', description: 'Branch or commit SHA (default: default branch)' },
        },
        required: ['path'],
      },
    },
  ];

  async executeTool(name: string, input: Record<string, unknown>): Promise<unknown> {
    if (!this.octokit) {
      return { error: 'GitHub not configured. Set GITHUB_TOKEN in .env' };
    }

    switch (name) {
      case 'list_recent_commits':
        return this.listRecentCommits(input);
      case 'list_pull_requests':
        return this.listPullRequests(input);
      case 'list_recently_changed_files':
        return this.listRecentlyChangedFiles(input);
      case 'get_file_content':
        return this.getFileContent(input);
      default:
        return { error: `Unknown tool: ${name}` };
    }
  }

  async healthCheck(): Promise<{ ok: boolean; message?: string }> {
    if (!this.octokit) {
      return { ok: false, message: 'Not configured — set GITHUB_TOKEN in .env' };
    }
    try {
      const res = await this.octokit.repos.get({ owner: this.owner, repo: this.repo });
      return { ok: true, message: `Connected to ${res.data.full_name}` };
    } catch (err) {
      return { ok: false, message: `API error: ${err instanceof Error ? err.message : String(err)}` };
    }
  }

  async initialize(_config: Record<string, string>): Promise<void> {
    const token = process.env.GITHUB_TOKEN;
    this.owner = process.env.GITHUB_OWNER || 'Bayeko';
    this.repo = process.env.GITHUB_REPO || 'BioNexus-mvp';

    if (!token) {
      console.log(JSON.stringify({
        timestamp: new Date().toISOString(),
        level: 'warn',
        message: 'GitHub: GITHUB_TOKEN not found in environment',
      }));
      this.octokit = null;
      return;
    }

    console.log(JSON.stringify({
      timestamp: new Date().toISOString(),
      level: 'info',
      message: `GitHub: token loaded (${token.length} chars), owner=${this.owner}, repo=${this.repo}`,
    }));

    this.octokit = new Octokit({ auth: token });
  }

  async shutdown(): Promise<void> {
    this.octokit = null;
  }

  private async listRecentCommits(input: Record<string, unknown>): Promise<unknown> {
    const since = input.since as string | undefined;
    const perPage = (input.per_page as number) || 20;

    const res = await this.octokit!.repos.listCommits({
      owner: this.owner,
      repo: this.repo,
      since,
      per_page: perPage,
    });

    return {
      commits: res.data.map((c) => ({
        sha: c.sha.slice(0, 7),
        message: c.commit.message,
        author: c.commit.author?.name,
        date: c.commit.author?.date,
        url: c.html_url,
      })),
    };
  }

  private async listPullRequests(input: Record<string, unknown>): Promise<unknown> {
    const state = (input.state as 'open' | 'closed' | 'all') || 'open';
    const perPage = (input.per_page as number) || 10;

    const res = await this.octokit!.pulls.list({
      owner: this.owner,
      repo: this.repo,
      state,
      per_page: perPage,
      sort: 'updated',
      direction: 'desc',
    });

    return {
      pull_requests: res.data.map((pr) => ({
        number: pr.number,
        title: pr.title,
        state: pr.state,
        author: pr.user?.login,
        created_at: pr.created_at,
        updated_at: pr.updated_at,
        url: pr.html_url,
        draft: pr.draft,
      })),
    };
  }

  private async listRecentlyChangedFiles(input: Record<string, unknown>): Promise<unknown> {
    const since = input.since as string | undefined;
    const pathFilter = input.path_filter as string | undefined;

    // Get recent commits
    const commits = await this.octokit!.repos.listCommits({
      owner: this.owner,
      repo: this.repo,
      since,
      per_page: 20,
    });

    // Collect changed files from each commit
    const fileMap = new Map<string, { status: string; sha: string; date: string }>();

    for (const commit of commits.data.slice(0, 10)) {
      const detail = await this.octokit!.repos.getCommit({
        owner: this.owner,
        repo: this.repo,
        ref: commit.sha,
      });
      for (const file of detail.data.files ?? []) {
        if (pathFilter && !file.filename?.startsWith(pathFilter)) continue;
        if (file.filename && !fileMap.has(file.filename)) {
          fileMap.set(file.filename, {
            status: file.status ?? 'modified',
            sha: commit.sha.slice(0, 7),
            date: commit.commit.author?.date ?? '',
          });
        }
      }
    }

    return {
      files: Array.from(fileMap.entries()).map(([filename, info]) => ({
        filename,
        ...info,
      })),
    };
  }

  private async getFileContent(input: Record<string, unknown>): Promise<unknown> {
    const path = input.path as string;
    const ref = input.ref as string | undefined;

    const res = await this.octokit!.repos.getContent({
      owner: this.owner,
      repo: this.repo,
      path,
      ...(ref && { ref }),
    });

    const data = res.data;

    // getContent returns a file object with base64-encoded content
    if (!Array.isArray(data) && data.type === 'file' && data.content) {
      const content = Buffer.from(data.content, 'base64').toString('utf-8');
      return {
        path: data.path,
        name: data.name,
        size: data.size,
        content,
      };
    }

    // If it's a directory, return the listing
    if (Array.isArray(data)) {
      return {
        path,
        type: 'directory',
        entries: data.map((entry) => ({ name: entry.name, type: entry.type, path: entry.path })),
      };
    }

    return { error: `Unsupported content type at path: ${path}` };
  }
}
