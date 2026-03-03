import 'dotenv/config';

export interface SchedulerConfig {
  morningKickoffCron: string;
  weeklyReviewCron: string;
  meetingPrepLeadMinutes: number;
  githubPollIntervalMinutes: number;
}

export interface OrchestratorConfig {
  port: number;
  host: string;
  anthropic: { apiKey: string; model: string };
  google: {
    clientId: string;
    clientSecret: string;
    refreshToken: string;
  };
  github: { token: string; owner: string; repo: string };
  scheduler: SchedulerConfig;
}

function requireEnv(key: string): string {
  const value = process.env[key];
  if (!value) {
    throw new Error(`Missing required environment variable: ${key}`);
  }
  return value;
}

function optionalEnv(key: string, fallback: string): string {
  return process.env[key] || fallback;
}

export function loadConfig(): OrchestratorConfig {
  return {
    port: parseInt(optionalEnv('PORT', '3737'), 10),
    host: optionalEnv('HOST', 'localhost'),
    anthropic: {
      apiKey: requireEnv('ANTHROPIC_API_KEY'),
      model: optionalEnv('ANTHROPIC_MODEL', 'claude-sonnet-4-20250514'),
    },
    google: {
      clientId: optionalEnv('GOOGLE_CLIENT_ID', ''),
      clientSecret: optionalEnv('GOOGLE_CLIENT_SECRET', ''),
      refreshToken: optionalEnv('GOOGLE_REFRESH_TOKEN', ''),
    },
    github: {
      token: optionalEnv('GITHUB_TOKEN', ''),
      owner: optionalEnv('GITHUB_OWNER', 'Bayeko'),
      repo: optionalEnv('GITHUB_REPO', 'BioNexus-mvp'),
    },
    scheduler: {
      morningKickoffCron: optionalEnv('MORNING_KICKOFF_CRON', '0 8 * * 1-5'),
      weeklyReviewCron: optionalEnv('WEEKLY_REVIEW_CRON', '0 17 * * 5'),
      meetingPrepLeadMinutes: parseInt(optionalEnv('MEETING_PREP_LEAD_MINUTES', '30'), 10),
      githubPollIntervalMinutes: parseInt(optionalEnv('GITHUB_POLL_INTERVAL_MINUTES', '15'), 10),
    },
  };
}
