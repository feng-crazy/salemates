# Database Migrations

## Running Migrations

```bash
# Connect to Postgres
psql $DATABASE_URL

# Run migrations
\i migrations/001_initial_schema.sql
```

## Migration Files

- `001_initial_schema.sql` - Initial tables (customers, conversations, stage_transitions)