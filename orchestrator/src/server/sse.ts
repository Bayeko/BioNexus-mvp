import type { Response } from 'express';

export interface SSEClient {
  id: string;
  res: Response;
}

export class SSEManager {
  private clients: Map<string, SSEClient> = new Map();
  private nextId = 1;

  addClient(res: Response): string {
    const id = String(this.nextId++);

    res.writeHead(200, {
      'Content-Type': 'text/event-stream',
      'Cache-Control': 'no-cache',
      Connection: 'keep-alive',
      'Access-Control-Allow-Origin': '*',
    });

    // Send initial connection event
    res.write(`event: connected\ndata: ${JSON.stringify({ clientId: id })}\n\n`);

    this.clients.set(id, { id, res });

    res.on('close', () => {
      this.clients.delete(id);
    });

    return id;
  }

  broadcast(event: string, data: unknown): void {
    const payload = `event: ${event}\ndata: ${JSON.stringify(data)}\n\n`;
    for (const client of this.clients.values()) {
      client.res.write(payload);
    }
  }

  get clientCount(): number {
    return this.clients.size;
  }
}

export function createSSEManager(): SSEManager {
  return new SSEManager();
}
