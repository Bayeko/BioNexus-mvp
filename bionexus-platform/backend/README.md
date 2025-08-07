# Backend

## Applying Database Migrations

To apply the latest migrations for the `samples` and `protocols` apps:

```bash
cd bionexus-platform/backend
python manage.py migrate
```

This will create or update the database schema based on the defined models and migration files.
