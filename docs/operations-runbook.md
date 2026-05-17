# Operations Runbook

## Run Locally

1. Install dependencies:

```bash
make install
```

2. Create local environment file:

```bash
cp .env.example .env
```

3. Start PostgreSQL:

```bash
make db-up
```

4. Run migrations:

```bash
export DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:5432/polymarket_scalper
make db-migrate
```

5. Run the recorder once:

```bash
APP_MODE=record make record
```

## Run Tests

```bash
make test
```

## Run Linting

```bash
make lint
make format
```

## Docker Compose

Build images:

```bash
make docker-build
```

Run PostgreSQL:

```bash
make db-up
```

Run the recorder in Docker:

```bash
make docker-record
```

Inspect logs:

```bash
make docker-logs
```

Run tests in Docker:

```bash
make docker-test
```

Stop services:

```bash
make docker-down
```

## Health Check

```bash
APP_MODE=record make health
```

The health output reports:
- database reachability
- active underlying price provider
- last market refresh time
- active markets count
- last Polymarket message time
- last underlying price tick time
- snapshots written

## Logging Expectations

Logs should show:
- recorder start
- provider selection
- accepted and rejected markets
- snapshot batch counts
- database failures
- disconnect/reconnect conditions
- graceful shutdown

Secrets must never be logged.

## Config Validation Failure

If config validation fails:
- startup must stop immediately
- the invalid field or rule must be visible
- secrets must remain redacted

## Manual Backup

For local or simple server-side backup:

```bash
pg_dump postgresql://postgres:postgres@localhost:5432/polymarket_scalper > recorder_backup.sql
```

## Simple DigitalOcean Path

Keep deployment simple in Phase 2:
- single Ubuntu Droplet
- Docker and Docker Compose
- server-side `.env`
- PostgreSQL either in Compose or upgraded later to managed PostgreSQL only when justified
