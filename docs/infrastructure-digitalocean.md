# Infrastructure On DigitalOcean

## Initial Recommendation

Use a single DigitalOcean Ubuntu Droplet with:
- Docker
- Docker Compose
- `.env` file stored on the server
- SSH key access
- host firewall
- simple Git-based deploy flow or small deploy script

This is the right trade-off for the current phase because the project is still defining behavior and does not need distributed infrastructure.

## Local-First Testing

The application should run locally and in Docker Compose before any server deployment.

For Phase 1, the app should run locally and in Docker. No live trading credentials are required. No real orders are placed.

## Deployment Approach

Recommended initial deployment flow:
- create Ubuntu Droplet
- install Docker and Docker Compose plugin
- clone repository on the server
- create `.env` on the server from `.env.example`
- build and start services with `docker compose`
- update via `git pull` plus rebuild/restart, or a small deploy script wrapping those commands

## Firewall Requirements

At minimum:
- allow inbound `22/tcp` for SSH
- allow outbound HTTPS and secure WebSocket traffic for future data collection
- avoid opening unnecessary inbound ports in Phase 1

If a future dashboard or metrics endpoint is added, expose it only if there is a clear operational reason.

## SSH Key Access

Use SSH keys only. Do not rely on password logins.

Recommended hardening:
- disable root password authentication
- use a non-root sudo user
- limit SSH access to approved keys

## Environment Variables

Use a server-side `.env` file.

Phase 1 rules:
- no live trading secrets are needed
- builder credentials remain empty
- private key remains empty
- database and Redis settings may stay unset

## Monitoring

Keep monitoring simple at first:
- container logs
- restart policy in Compose when appropriate in later phases
- optional lightweight uptime checks once long-running services exist

Do not add heavy observability stacks in Phase 1.

## Backups

Phase 1 has no persistent runtime data requirements.

Later, when market recording begins:
- back up recorded market data
- back up environment configuration securely
- keep deploy instructions reproducible from version control

## Later Database Option

DigitalOcean Managed PostgreSQL is a reasonable later option only when market recording and historical storage become operational requirements.

It should not be introduced before Phase 2 or later evidence that a managed database is worth the cost and complexity.

## Why No Live Trading Secrets Are Needed In Phase 1

Phase 1 is documentation and scaffolding only.
- no order placement exists
- no authenticated Polymarket requests are required
- no wallet signing is required
- no builder credentials are required

That keeps setup simple, reduces risk, and avoids solving future-phase security problems too early.
