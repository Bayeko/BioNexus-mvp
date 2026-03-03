import type { Express, Request, Response, NextFunction } from 'express';
import express from 'express';

export function setupMiddleware(app: Express): void {
  app.use(express.json());

  // CORS for dashboard dev server
  app.use((_req: Request, res: Response, next: NextFunction) => {
    res.header('Access-Control-Allow-Origin', '*');
    res.header('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS');
    res.header('Access-Control-Allow-Headers', 'Content-Type');
    if (_req.method === 'OPTIONS') {
      res.sendStatus(204);
      return;
    }
    next();
  });

  // Request logging
  app.use((req: Request, _res: Response, next: NextFunction) => {
    if (req.path !== '/api/sse' && req.path !== '/api/health') {
      console.log(JSON.stringify({
        timestamp: new Date().toISOString(),
        method: req.method,
        path: req.path,
      }));
    }
    next();
  });
}

// Error handler — must be registered after routes
export function errorHandler(err: Error, _req: Request, res: Response, _next: NextFunction): void {
  console.error(JSON.stringify({
    timestamp: new Date().toISOString(),
    level: 'error',
    message: err.message,
    stack: err.stack,
  }));
  res.status(500).json({ error: 'Internal server error' });
}
