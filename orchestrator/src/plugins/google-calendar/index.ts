import { google, type calendar_v3 } from 'googleapis';
import type { OAuth2Client } from 'google-auth-library';
import type { ConnectorPlugin, ToolDefinition } from '../types.js';

export class GoogleCalendarPlugin implements ConnectorPlugin {
  name = 'google-calendar';
  displayName = 'Google Calendar';
  description = 'Read and query Google Calendar events for scheduling and meeting awareness';

  private oauth2Client: OAuth2Client | null = null;
  private calendar: calendar_v3.Calendar | null = null;

  tools: ToolDefinition[] = [
    {
      name: 'list_events',
      description: 'List calendar events within a date range',
      input_schema: {
        type: 'object',
        properties: {
          start_date: { type: 'string', description: 'ISO 8601 date/datetime string' },
          end_date: { type: 'string', description: 'ISO 8601 date/datetime string' },
          max_results: { type: 'number', description: 'Maximum events to return (default 20)' },
        },
        required: ['start_date', 'end_date'],
      },
    },
    {
      name: 'get_upcoming_meetings',
      description: 'Get meetings happening within the next N minutes',
      input_schema: {
        type: 'object',
        properties: {
          within_minutes: { type: 'number', description: 'Look ahead window in minutes' },
        },
        required: ['within_minutes'],
      },
    },
  ];

  async executeTool(name: string, input: Record<string, unknown>): Promise<unknown> {
    if (!this.calendar) {
      return { error: 'Google Calendar not configured. Set GOOGLE_* environment variables.' };
    }

    switch (name) {
      case 'list_events':
        return this.listEvents(input);
      case 'get_upcoming_meetings':
        return this.getUpcomingMeetings(input);
      default:
        return { error: `Unknown tool: ${name}` };
    }
  }

  async healthCheck(): Promise<{ ok: boolean; message?: string }> {
    if (!this.calendar) {
      return { ok: false, message: 'Not configured — set Google OAuth credentials in .env' };
    }
    try {
      const res = await this.calendar.calendarList.list({ maxResults: 1 });
      const count = res.data.items?.length ?? 0;
      return { ok: true, message: `Connected — ${count} calendar(s) accessible` };
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
    this.calendar = google.calendar({ version: 'v3', auth: this.oauth2Client });
  }

  async shutdown(): Promise<void> {
    this.oauth2Client = null;
    this.calendar = null;
  }

  private async listEvents(input: Record<string, unknown>): Promise<unknown> {
    const res = await this.calendar!.events.list({
      calendarId: 'primary',
      timeMin: new Date(input.start_date as string).toISOString(),
      timeMax: new Date(input.end_date as string).toISOString(),
      maxResults: (input.max_results as number) || 20,
      singleEvents: true,
      orderBy: 'startTime',
    });

    return {
      events: (res.data.items ?? []).map(formatEvent),
    };
  }

  private async getUpcomingMeetings(input: Record<string, unknown>): Promise<unknown> {
    const now = new Date();
    const end = new Date(now.getTime() + ((input.within_minutes as number) || 60) * 60_000);

    const res = await this.calendar!.events.list({
      calendarId: 'primary',
      timeMin: now.toISOString(),
      timeMax: end.toISOString(),
      singleEvents: true,
      orderBy: 'startTime',
    });

    return {
      meetings: (res.data.items ?? []).map(formatEvent),
    };
  }
}

function formatEvent(event: calendar_v3.Schema$Event) {
  return {
    id: event.id,
    summary: event.summary,
    start: event.start?.dateTime ?? event.start?.date,
    end: event.end?.dateTime ?? event.end?.date,
    location: event.location,
    attendees: event.attendees?.map((a) => ({ email: a.email, status: a.responseStatus })),
    htmlLink: event.htmlLink,
  };
}
