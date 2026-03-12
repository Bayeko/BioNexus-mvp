import { google, type drive_v3 } from 'googleapis';
import type { OAuth2Client } from 'google-auth-library';
import type { ConnectorPlugin, ToolDefinition } from '../types.js';

export class GoogleDrivePlugin implements ConnectorPlugin {
  name = 'google-drive';
  displayName = 'Google Drive';
  description = 'Search, read, and create documents in Google Drive';

  private oauth2Client: OAuth2Client | null = null;
  private drive: drive_v3.Drive | null = null;

  tools: ToolDefinition[] = [
    {
      name: 'search_files',
      description: 'Search for files in Google Drive by name or content',
      input_schema: {
        type: 'object',
        properties: {
          query: { type: 'string', description: 'Search query string' },
          max_results: { type: 'number', description: 'Maximum files to return (default 10)' },
        },
        required: ['query'],
      },
    },
    {
      name: 'get_file_content',
      description: 'Get the text content of a Google Drive document',
      input_schema: {
        type: 'object',
        properties: {
          file_id: { type: 'string', description: 'Google Drive file ID' },
        },
        required: ['file_id'],
      },
    },
    {
      name: 'create_document',
      description: 'Create a new Google Doc with the given title and content',
      input_schema: {
        type: 'object',
        properties: {
          title: { type: 'string', description: 'Document title' },
          content: { type: 'string', description: 'Document body text' },
          folder_id: { type: 'string', description: 'Optional parent folder ID' },
        },
        required: ['title', 'content'],
      },
    },
    {
      name: 'list_files',
      description: 'List files in a specific Google Drive folder',
      input_schema: {
        type: 'object',
        properties: {
          folder_id: { type: 'string', description: 'Folder ID (omit for root)' },
          max_results: { type: 'number', description: 'Maximum files to return (default 20)' },
        },
      },
    },
  ];

  async executeTool(name: string, input: Record<string, unknown>): Promise<unknown> {
    if (!this.drive) {
      return { error: 'Google Drive not configured. Set GOOGLE_* environment variables.' };
    }

    switch (name) {
      case 'search_files':
        return this.searchFiles(input);
      case 'get_file_content':
        return this.getFileContent(input);
      case 'create_document':
        return this.createDocument(input);
      case 'list_files':
        return this.listFiles(input);
      default:
        return { error: `Unknown tool: ${name}` };
    }
  }

  async healthCheck(): Promise<{ ok: boolean; message?: string }> {
    if (!this.drive) {
      return { ok: false, message: 'Not configured — set Google OAuth credentials in .env' };
    }
    try {
      const res = await this.drive.about.get({ fields: 'user(displayName,emailAddress)' });
      const user = res.data.user;
      return { ok: true, message: `Connected as ${user?.displayName} (${user?.emailAddress})` };
    } catch (err) {
      return { ok: false, message: `API error: ${err instanceof Error ? err.message : String(err)}` };
    }
  }

  async initialize(_config: Record<string, string>): Promise<void> {
    const clientId = process.env.GOOGLE_CLIENT_ID;
    const clientSecret = process.env.GOOGLE_CLIENT_SECRET;
    const refreshToken = process.env.GOOGLE_REFRESH_TOKEN;

    if (!clientId || !clientSecret || !refreshToken) return;

    this.oauth2Client = new google.auth.OAuth2(clientId, clientSecret);
    this.oauth2Client.setCredentials({ refresh_token: refreshToken });
    this.drive = google.drive({ version: 'v3', auth: this.oauth2Client });
  }

  async shutdown(): Promise<void> {
    this.oauth2Client = null;
    this.drive = null;
  }

  private async searchFiles(input: Record<string, unknown>): Promise<unknown> {
    const query = input.query as string;
    const res = await this.drive!.files.list({
      q: `fullText contains '${query.replace(/'/g, "\\'")}'`,
      pageSize: (input.max_results as number) || 10,
      fields: 'files(id,name,mimeType,modifiedTime,webViewLink,size)',
    });

    return { files: (res.data.files ?? []).map(formatFile) };
  }

  private async getFileContent(input: Record<string, unknown>): Promise<unknown> {
    const fileId = input.file_id as string;

    // Get file metadata first to check type
    const meta = await this.drive!.files.get({ fileId, fields: 'mimeType,name' });
    const mimeType = meta.data.mimeType ?? '';

    // Google Docs/Sheets/Slides: export as plain text
    if (mimeType.startsWith('application/vnd.google-apps.')) {
      const exportMime = mimeType.includes('spreadsheet')
        ? 'text/csv'
        : 'text/plain';
      const res = await this.drive!.files.export(
        { fileId, mimeType: exportMime },
        { responseType: 'text' }
      );
      return { name: meta.data.name, mimeType, content: res.data as string };
    }

    // Binary/other files: download content
    const res = await this.drive!.files.get(
      { fileId, alt: 'media' },
      { responseType: 'text' }
    );
    return { name: meta.data.name, mimeType, content: res.data as string };
  }

  private async createDocument(input: Record<string, unknown>): Promise<unknown> {
    const title = input.title as string;
    const content = input.content as string;
    const folderId = input.folder_id as string | undefined;

    const parents = folderId ? [folderId] : undefined;

    // Create the file as a Google Doc
    const res = await this.drive!.files.create({
      requestBody: {
        name: title,
        mimeType: 'application/vnd.google-apps.document',
        parents,
      },
      media: {
        mimeType: 'text/plain',
        body: content,
      },
      fields: 'id,name,webViewLink',
    });

    return {
      file_id: res.data.id,
      name: res.data.name,
      webViewLink: res.data.webViewLink,
    };
  }

  private async listFiles(input: Record<string, unknown>): Promise<unknown> {
    const folderId = input.folder_id as string | undefined;
    const q = folderId
      ? `'${folderId}' in parents and trashed = false`
      : 'trashed = false';

    const res = await this.drive!.files.list({
      q,
      pageSize: (input.max_results as number) || 20,
      fields: 'files(id,name,mimeType,modifiedTime,webViewLink,size)',
      orderBy: 'modifiedTime desc',
    });

    return { files: (res.data.files ?? []).map(formatFile) };
  }
}

function formatFile(file: drive_v3.Schema$File) {
  return {
    id: file.id,
    name: file.name,
    mimeType: file.mimeType,
    modifiedTime: file.modifiedTime,
    webViewLink: file.webViewLink,
    size: file.size,
  };
}
