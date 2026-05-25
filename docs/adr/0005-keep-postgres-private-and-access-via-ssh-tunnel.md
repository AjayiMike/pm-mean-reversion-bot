# ADR 0005: Keep Postgres private and access via SSH tunnel

## Status

Accepted

## Context

A prior production issue exposed PostgreSQL publicly while weak/default credentials were still in use. Logs showed malicious SQL attempts. The database was treated as compromised.

## Decision

Keep PostgreSQL private in production. Do not publish it publicly. Access should remain through Docker's internal network or via SSH tunnel to a loopback-bound host port when manual inspection is necessary.

## Consequences

- Local inspection requires SSH tunneling or server-side access.
- Deployment changes must preserve private DB exposure.
- Security posture is materially stronger than public port publishing.

## Alternatives Considered

- Publish PostgreSQL on a public host port with firewall restrictions.
- Allow direct laptop-to-DB access without SSH tunneling.

## Notes

The incident response already included:
- DB volume wipe
- credential rotation
- removal of public publishing
- hardened Compose configuration
- loopback binding for safe DBeaver/psql access
