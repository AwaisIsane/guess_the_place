# WorldGuessr

A guest-only, five-round world exploration game built with Mapillary, MapLibre, FastAPI,
PostgreSQL/PostGIS, Redis, and Caddy.

## Local start

1. Copy `.env.example` to `.env`. Set `POSTGRES_PASSWORD` and `SIGNING_SECRET`.
2. For real imagery, add a domain-restricted public Mapillary client token and a server Graph
   API token. Configure a production OSM-derived map style URL.
3. Start the stack: `podman compose up --build -d`. The worker automatically discovers and
   stores real imagery when `MAPILLARY_GRAPH_TOKEN` is configured.
4. For a UI smoke test only, set `ALLOW_DEMO_CATALOG=true`, then seed:
   `podman compose run --rm backend python -m app.seed --demo`.
5. Visit `http://localhost:3000`.

Demo records use placeholder image IDs, so they exercise gameplay but intentionally show an
imagery placeholder. Production catalog ingestion must store validated Mapillary image and
sequence IDs. Public OpenStreetMap tiles must not be bulk-prefetched or proxied; use an
appropriate provider and follow its terms.

## Deployment

Point the domain at the VPS, set `PUBLIC_DOMAIN`, `PUBLIC_ORIGIN`, and `SITE_ADDRESS` for its
HTTPS URL, set `HTTP_PORT=80` and `HTTPS_PORT=443`, and run
`podman compose up --build -d`. Binding privileged ports in rootless Podman requires the host
to permit them; alternatively, run the production stack rootfully. Only Caddy publishes ports;
PostgreSQL and Redis remain on an internal Podman network. All persistent state is beneath
`.volumes/`.

Before opening traffic:

- use strong, unique database and signing secrets;
- restrict the public Mapillary token to the production domain;
- supply a licensed OSM-derived style/tile provider;
- populate at least `ELIGIBLE_COUNTRY_MINIMUM` countries with `COUNTRY_POOL_MINIMUM` validated
  locations each;
- verify `/health/live` and `/health/ready`.

The worker prunes expired games and stale provider records. PostgreSQL remains authoritative;
Redis is limited to queues and reconstructible hot state.

## Catalog

`python -m app.seed --demo` is idempotent. Real discovery starts automatically with the worker,
runs periodically, and uses bounded retries and jitter against the Mapillary Graph API.
It imports small, bundled city regions, upserts metadata, rebuilds catalog counts, and stops
demo placeholders from being selected once the real catalog is playable.

The API selects countries uniformly from eligible countries and then chooses a quality-weighted
location. Recent locations for the guest are excluded where the pool permits.

## Backups and restore

The `backup` service creates one compressed custom-format dump daily in `.volumes/backups` and
keeps seven days. Test restore regularly:

```sh
podman compose stop backend worker
podman compose exec -T postgres dropdb -U worldguessr worldguessr
podman compose exec -T postgres createdb -U worldguessr worldguessr
podman compose exec -T postgres pg_restore -U worldguessr -d worldguessr --clean --if-exists \
  < .volumes/backups/worldguessr-TIMESTAMP.dump
podman compose up -d backend worker
```

Restore is destructive to the current database; take a fresh backup first.

## Development and tests

Backend:

```sh
cd backend
python -m venv .venv && . .venv/bin/activate
pip install -e '.[dev]'
DATABASE_URL=sqlite:///test.db pytest
ruff check .
```

Frontend:

```sh
cd frontend
npm install
npm run build
```

Validate the container configuration with `podman compose config`.
