# Bionexus Platform

This directory contains a minimal development environment for the
BioNexus MVP platform.  The stack is composed of a Django backend,
PostgreSQL database, and a React frontend orchestrated through
Docker Compose.

## Environment Variables

The following variables can be customised in a `.env` file or by
overriding them when running `docker compose`.

| Variable | Description | Default |
|----------|-------------|---------|
| `POSTGRES_USER` | database user | `bionexus` |
| `POSTGRES_PASSWORD` | database password | `bionexus` |
| `POSTGRES_DB` | database name | `bionexus` |
| `DATABASE_URL` | connection string used by Django | `postgres://bionexus:bionexus@db:5432/bionexus` |
| `DJANGO_SECRET_KEY` | secret key used by Django | `dev-secret-key` |
| `DJANGO_DEBUG` | enable debug mode (`true`/`false`) | `true` |
| `DJANGO_ALLOWED_HOSTS` | comma separated hostnames Django can serve | `localhost,127.0.0.1,testserver` |
| `CHOKIDAR_USEPOLLING` | enables reliable hot reloading for the frontend inside Docker | `true` |

These variables override the defaults defined in `core/settings.py` and
can be placed in a `.env` file or exported in your shell before
starting the services.

## Usage

From this directory run:

```bash
docker compose up --build
```

Services will be available at:

- Backend: <http://localhost:8000>
- Frontend: <http://localhost:3000>
- PostgreSQL: `localhost:5432`

Source code for the backend and frontend is mounted into the containers
so that changes on the host trigger automatic reloads.  PostgreSQL data
is stored in a named volume `postgres_data` to persist across runs.

