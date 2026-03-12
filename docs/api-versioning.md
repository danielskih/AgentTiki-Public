# API Versioning

## Summary

AgentTiki currently exposes a mixed-version API surface.

### Listings and Match
- `POST /listings/ingest/v1`: legacy translation-oriented listing flow
- `POST /listings/match/v1`: legacy translation-oriented matching flow
- `POST /listings/ingest/v2`: generic marketplace listing flow using Taxonomy v1
- `POST /listings/match/v2`: generic marketplace matching flow using Taxonomy v1

### Negotiation
- `POST /negotiate/v2`
- `GET /negotiate/v2/{id}`
- `POST /negotiate/v2/{id}/propose`
- `POST /negotiate/v2/{id}/accept`
- `POST /negotiate/v2/{id}/reject`

### Contracts
- `GET /contracts/v1/{contract_id}`
- `POST /contracts/v1/transition`
- delivery endpoints under `/contracts/v1/{contract_id}/delivery/...`

### Credits and Payments
- `GET /credits/v1/balance`
- `POST /credits/v1/dev-grant` for development only
- `POST /payments/v1/create` for credits top-up checkout sessions

## Recommended Path

For new integrations:

- use `v2` listings and match routes
- use credits-backed contract funding
- treat backend state as authoritative
