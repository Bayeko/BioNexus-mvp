import type { ConnectorPlugin, ToolDefinition } from '../types.js';

export class GmailPlugin implements ConnectorPlugin {
  name = 'gmail';
  displayName = 'Gmail';
  description = 'Search and read Gmail messages for email-aware workflows';

  private initialized = false;

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
    if (!this.initialized) {
      return { error: 'Gmail not configured. Set GOOGLE_* environment variables.' };
    }

    switch (name) {
      case 'search_messages':
        return { messages: [], message: `Would search for: ${input.query}` };
      case 'get_message':
        return { message: null, info: `Would fetch message ${input.message_id}` };
      case 'list_unread':
        return { messages: [], message: 'Would list unread messages' };
      default:
        return { error: `Unknown tool: ${name}` };
    }
  }

  async healthCheck(): Promise<{ ok: boolean; message?: string }> {
    if (!this.initialized) {
      return { ok: false, message: 'Not configured — set Google OAuth credentials in .env' };
    }
    return { ok: true };
  }

  async initialize(_config: Record<string, string>): Promise<void> {
    const clientId = process.env.GOOGLE_CLIENT_ID;
    const clientSecret = process.env.GOOGLE_CLIENT_SECRET;
    const refreshToken = process.env.GOOGLE_REFRESH_TOKEN;

    if (clientId && clientSecret && refreshToken) {
      // TODO: Initialize googleapis OAuth2 client for Gmail
      this.initialized = true;
    }
  }

  async shutdown(): Promise<void> {
    this.initialized = false;
  }
}
