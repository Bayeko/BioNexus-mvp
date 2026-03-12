import 'dotenv/config';
import { google } from 'googleapis';
import http from 'node:http';
import fs from 'node:fs';
import path from 'node:path';
import { execSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const ENV_PATH = path.resolve(__dirname, '..', '.env');
const CALLBACK_PORT = 3838;
const REDIRECT_URI = `http://localhost:${CALLBACK_PORT}/oauth2callback`;

const SCOPES = [
  'https://www.googleapis.com/auth/calendar',
  'https://www.googleapis.com/auth/gmail.modify',
  'https://www.googleapis.com/auth/drive',
];

function getCredentials(): { clientId: string; clientSecret: string } {
  const clientId = process.env.GOOGLE_CLIENT_ID;
  const clientSecret = process.env.GOOGLE_CLIENT_SECRET;

  if (!clientId || !clientSecret) {
    console.error('Missing GOOGLE_CLIENT_ID or GOOGLE_CLIENT_SECRET in .env');
    process.exit(1);
  }

  return { clientId, clientSecret };
}

function saveRefreshToken(token: string): void {
  let envContent = fs.readFileSync(ENV_PATH, 'utf-8');

  if (envContent.match(/^GOOGLE_REFRESH_TOKEN=.*$/m)) {
    envContent = envContent.replace(
      /^GOOGLE_REFRESH_TOKEN=.*$/m,
      `GOOGLE_REFRESH_TOKEN=${token}`
    );
  } else {
    envContent = envContent.trimEnd() + `\nGOOGLE_REFRESH_TOKEN=${token}\n`;
  }

  fs.writeFileSync(ENV_PATH, envContent);
}

function openBrowser(url: string): void {
  const platform = process.platform;
  try {
    if (platform === 'darwin') {
      execSync(`open "${url}"`);
    } else if (platform === 'win32') {
      execSync(`start "" "${url}"`);
    } else {
      // Linux / WSL — try wslview first (WSL), then xdg-open
      try {
        execSync(`wslview "${url}" 2>/dev/null`);
      } catch {
        execSync(`xdg-open "${url}" 2>/dev/null`);
      }
    }
  } catch {
    // Browser open failed — user will use the printed URL
  }
}

async function main(): Promise<void> {
  console.log('Google OAuth2 Authentication Flow');
  console.log('=================================\n');

  const { clientId, clientSecret } = getCredentials();

  const oauth2Client = new google.auth.OAuth2(clientId, clientSecret, REDIRECT_URI);

  const authUrl = oauth2Client.generateAuthUrl({
    access_type: 'offline',
    prompt: 'consent',
    scope: SCOPES,
  });

  // Start local server to receive the callback
  const server = http.createServer(async (req, res) => {
    if (!req.url?.startsWith('/oauth2callback')) {
      res.writeHead(404);
      res.end('Not found');
      return;
    }

    const url = new URL(req.url, `http://localhost:${CALLBACK_PORT}`);
    const code = url.searchParams.get('code');
    const error = url.searchParams.get('error');

    if (error) {
      res.writeHead(200, { 'Content-Type': 'text/html' });
      res.end('<h1>Authorization denied</h1><p>You can close this tab.</p>');
      console.error(`\nAuthorization denied: ${error}`);
      server.close();
      process.exit(1);
    }

    if (!code) {
      res.writeHead(400, { 'Content-Type': 'text/html' });
      res.end('<h1>Missing authorization code</h1>');
      return;
    }

    try {
      const { tokens } = await oauth2Client.getToken(code);

      if (!tokens.refresh_token) {
        res.writeHead(200, { 'Content-Type': 'text/html' });
        res.end(
          '<h1>No refresh token received</h1>' +
          '<p>Revoke access at <a href="https://myaccount.google.com/permissions">Google Account Permissions</a> and try again.</p>'
        );
        console.error('\nNo refresh token received. Revoke app access and retry.');
        server.close();
        process.exit(1);
      }

      saveRefreshToken(tokens.refresh_token);

      res.writeHead(200, { 'Content-Type': 'text/html' });
      res.end(
        '<h1>Authorization successful!</h1>' +
        '<p>Refresh token saved to .env. You can close this tab.</p>'
      );

      console.log('\nRefresh token saved to .env');
      console.log('Scopes authorized: Calendar, Gmail, Drive');
      console.log('\nYou can now start the orchestrator with: npm run dev');
    } catch (err) {
      res.writeHead(500, { 'Content-Type': 'text/html' });
      res.end('<h1>Token exchange failed</h1><p>Check the console for details.</p>');
      console.error('\nToken exchange failed:', err);
    }

    server.close();
  });

  server.listen(CALLBACK_PORT, () => {
    console.log(`Callback server listening on port ${CALLBACK_PORT}`);
    console.log(`\nOpening browser for authorization...\n`);
    console.log(`If the browser doesn't open, visit this URL:\n`);
    console.log(authUrl);
    console.log('');

    openBrowser(authUrl);
  });
}

main();
