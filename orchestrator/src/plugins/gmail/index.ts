import { google, type gmail_v1 } from 'googleapis';
import type { OAuth2Client } from 'google-auth-library';
import type { ConnectorPlugin, ToolDefinition } from '../types.js';

export class GmailPlugin implements ConnectorPlugin {
  name = 'gmail';
  displayName = 'Gmail';
  description = 'Search and read Gmail messages for email-aware workflows';

  private oauth2Client: OAuth2Client | null = null;
  private gmail: gmail_v1.Gmail | null = null;

  tools: ToolDefinition[] = [
    {
      name: 'search_messages',
      description: 'Search Gmail messages using Gmail search syntax',
      input_schema: {
        type: 'object',
        properties: {
          query: { type: 'string', description: 'Gmail search query (e.g. "from:johannes subject:meeting")' },
          max_results: { type: 'number', description: 'Maximum messages to return (default 10)' },
        },
        required: ['query'],
      },
    },
    {
      name: 'get_message',
      description: 'Get the full content of a specific email message',
      input_schema: {
        type: 'object',
        properties: {
          message_id: { type: 'string', description: 'Gmail message ID' },
        },
        required: ['message_id'],
      },
    },
    {
      name: 'list_unread',
      description: 'List unread messages in the inbox',
      input_schema: {
        type: 'object',
        properties: {
          max_results: { type: 'number', description: 'Maximum messages to return (default 20)' },
        },
      },
    },
  ];

  async executeTool(name: string, input: Record<string, unknown>): Promise<unknown> {
    if (!this.gmail) {
      return { error: 'Gmail not configured. Set GOOGLE_* environment variables.' };
    }

    switch (name) {
      case 'search_messages':
        return this.searchMessages(input);
      case 'get_message':
        return this.getMessage(input);
      case 'list_unread':
        return this.listUnread(input);
      default:
        return { error: `Unknown tool: ${name}` };
    }
  }

  async healthCheck(): Promise<{ ok: boolean; message?: string }> {
    if (!this.gmail) {
      return { ok: false, message: 'Not configured — set Google OAuth credentials in .env' };
    }
    try {
      const res = await this.gmail.users.getProfile({ userId: 'me' });
      return { ok: true, message: `Connected as ${res.data.emailAddress}` };
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
    this.gmail = google.gmail({ version: 'v1', auth: this.oauth2Client });
  }

  async shutdown(): Promise<void> {
    this.oauth2Client = null;
    this.gmail = null;
  }

  private async searchMessages(input: Record<string, unknown>): Promise<unknown> {
    const res = await this.gmail!.users.messages.list({
      userId: 'me',
      q: input.query as string,
      maxResults: (input.max_results as number) || 10,
    });

    if (!res.data.messages?.length) {
      return { messages: [], total: 0 };
    }

    const messages = await Promise.all(
      res.data.messages.map((m) => this.fetchMessageSummary(m.id!))
    );

    return { messages, total: res.data.resultSizeEstimate };
  }

  private async getMessage(input: Record<string, unknown>): Promise<unknown> {
    const res = await this.gmail!.users.messages.get({
      userId: 'me',
      id: input.message_id as string,
      format: 'full',
    });

    return formatFullMessage(res.data);
  }

  private async listUnread(input: Record<string, unknown>): Promise<unknown> {
    const res = await this.gmail!.users.messages.list({
      userId: 'me',
      q: 'is:unread',
      maxResults: (input.max_results as number) || 20,
    });

    if (!res.data.messages?.length) {
      return { messages: [], total: 0 };
    }

    const messages = await Promise.all(
      res.data.messages.map((m) => this.fetchMessageSummary(m.id!))
    );

    return { messages, total: res.data.resultSizeEstimate };
  }

  private async fetchMessageSummary(id: string) {
    const res = await this.gmail!.users.messages.get({
      userId: 'me',
      id,
      format: 'metadata',
      metadataHeaders: ['From', 'To', 'Subject', 'Date'],
    });
    const headers = res.data.payload?.headers ?? [];
    const header = (name: string) => headers.find((h) => h.name === name)?.value ?? '';

    return {
      id: res.data.id,
      threadId: res.data.threadId,
      from: header('From'),
      to: header('To'),
      subject: header('Subject'),
      date: header('Date'),
      snippet: res.data.snippet,
    };
  }
}

function formatFullMessage(msg: gmail_v1.Schema$Message) {
  const headers = msg.payload?.headers ?? [];
  const header = (name: string) => headers.find((h) => h.name === name)?.value ?? '';

  let body = '';
  if (msg.payload?.body?.data) {
    body = Buffer.from(msg.payload.body.data, 'base64').toString('utf-8');
  } else if (msg.payload?.parts) {
    const textPart = msg.payload.parts.find((p) => p.mimeType === 'text/plain');
    if (textPart?.body?.data) {
      body = Buffer.from(textPart.body.data, 'base64').toString('utf-8');
    }
  }

  return {
    id: msg.id,
    threadId: msg.threadId,
    from: header('From'),
    to: header('To'),
    subject: header('Subject'),
    date: header('Date'),
    body,
    labels: msg.labelIds,
  };
}
