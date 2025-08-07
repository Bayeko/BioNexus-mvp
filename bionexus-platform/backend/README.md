# Backend

## Dependencies

The backend relies on pinned Python packages to ensure consistent environments:

- Django 5.2.5
- Django REST Framework 3.16.1
- Pytest 8.4.1

Install them with:

```bash
pip install -r requirements.txt
```

## Applying Database Migrations

To apply the latest migrations for the `samples` and `protocols` apps:

```bash
cd bionexus-platform/backend
python manage.py migrate
```

This will create or update the database schema based on the defined models and migration files.
