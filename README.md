# WorldGuessr

> **Prepare for the interview:** [Full-stack and cloud handbook](docs/README.md) — four
> code-grounded chapters covering FastAPI, React, architecture/system design, and AWS/EKS,
> with original visuals, answer frameworks, practice prompts, and authoritative external reading.

Read it as a searchable documentation site:

```sh
npm ci
npm run docs:dev
```

A guest-only, five-round world exploration game built with Mapillary, MapLibre, FastAPI,
PostgreSQL/PostGIS, Valkey, and Caddy.

## Supported toolchain

- Node.js 24 LTS with npm 11;
- Python 3.14 with uv 0.12;
- Podman 6 with Compose support;
- Terraform 1.15 and Helm 4 for infrastructure work.

## Local start

1. Copy `.env.example` to `.env`. Set `POSTGRES_PASSWORD` and `SIGNING_SECRET`.
2. For real imagery, add a domain-restricted public Mapillary client token and a server Graph
   API token. Configure a production OSM-derived map style URL.
3. Start the stack: `podman compose up --build -d`. The worker automatically discovers and
   stores real imagery when `MAPILLARY_GRAPH_TOKEN` is configured.
4. For a UI smoke test only, set `ALLOW_DEMO_CATALOG=true`, then seed:
   `podman compose run --rm backend python -m app.seed --demo`.
5. Visit `http://localhost:3000`.

For container-based development, run `npm run dev`. It starts the complete stack with bind-mounted
source: Vite hot-updates frontend edits, while Uvicorn and the ARQ worker reload on backend edits.
The development-only Caddy configuration permits the inline React-refresh preamble and WebSocket
connections required by Vite; the stricter production CSP remains unchanged. The development stack
stays attached so its logs are visible; Ctrl+C stops it.

Use `npm run dev:clean` when you need a completely fresh build. It removes only this Podman
Compose project's containers, locally built images, and `.volumes/frontend-node-modules`
dependency cache; clears generated
frontend/Python caches; pulls fresh base images; rebuilds without the layer cache; and launches
the same hot-reloading development stack. Persistent data in `.volumes/` is not removed.

Demo records use placeholder image IDs, so they exercise gameplay but intentionally show an
imagery placeholder. Production catalog ingestion must store validated Mapillary image and
sequence IDs. Public OpenStreetMap tiles must not be bulk-prefetched or proxied; use an
appropriate provider and follow its terms.

## Deployment

Point the domain at the VPS, set `PUBLIC_DOMAIN`, `PUBLIC_ORIGIN`, and `SITE_ADDRESS` for its
HTTPS URL, set `HTTP_PORT=80` and `HTTPS_PORT=443`, and run
`podman compose up --build -d`. Binding privileged ports in rootless Podman requires the host
to permit them; alternatively, run the production stack rootfully. Only Caddy publishes ports;
PostgreSQL and Valkey remain on an internal Podman network. All persistent state is beneath
`.volumes/`.

Before opening traffic:

- use strong, unique database and signing secrets;
- restrict the public Mapillary token to the production domain;
- supply a licensed OSM-derived style/tile provider;
- populate at least `ELIGIBLE_COUNTRY_MINIMUM` countries with `COUNTRY_POOL_MINIMUM` validated
  locations each;
- verify `/health/live` and `/health/ready`.

The worker prunes expired games and stale provider records. PostgreSQL remains authoritative;
Valkey is limited to queues and reconstructible hot state.

## Catalog

`python -m app.seed --demo` is idempotent. Real discovery starts automatically with the worker,
runs periodically, and uses bounded retries and jitter against the Mapillary Graph API.
It imports small, bundled city regions, upserts metadata, rebuilds catalog counts, and stops
demo placeholders from being selected once the real catalog is playable.

The API selects countries uniformly from eligible countries and then chooses a quality-weighted
location. Recent locations for the guest are excluded where the pool permits.

## Upgrading local PostgreSQL 17 to 18

PostgreSQL 18 uses a different container volume layout. The current Compose configuration mounts
the new cluster at `.volumes/postgres18` and deliberately leaves the former
`.volumes/postgres` directory untouched. Do not point PostgreSQL 18 at the old directory.

If the PostgreSQL 17 directory contains data you need, create a logical dump before starting the
new stack. Stop the old Compose stack, then run the former image against the preserved directory:

```sh
mkdir -p .volumes/backups
podman run --rm -d --name worldguessr-pg17-migration --env-file .env \
  -e POSTGRES_USER="${POSTGRES_USER:-worldguessr}" \
  -e POSTGRES_DB="${POSTGRES_DB:-worldguessr}" \
  -v "$PWD/.volumes/postgres:/var/lib/postgresql/data:Z" \
  docker.io/postgis/postgis:17-3.5-alpine
podman exec worldguessr-pg17-migration pg_dump \
  -U "${POSTGRES_USER:-worldguessr}" -d "${POSTGRES_DB:-worldguessr}" -Fc \
  > .volumes/backups/worldguessr-pg17.dump
podman stop worldguessr-pg17-migration
```

Only continue if the dump command succeeds and the dump is non-empty. Start PostgreSQL 18,
restore into its empty database, and then start the complete stack:

```sh
podman compose up -d postgres
podman compose exec -T postgres pg_restore \
  -U "${POSTGRES_USER:-worldguessr}" -d "${POSTGRES_DB:-worldguessr}" --no-owner \
  < .volumes/backups/worldguessr-pg17.dump
podman compose up --build -d
podman compose exec backend python -c \
  "import urllib.request; print(urllib.request.urlopen('http://localhost:8000/health/ready').status)"
```

Keep `.volumes/postgres` and the logical dump until row counts, gameplay, and a fresh PostgreSQL
18 backup have been verified. Valkey queue and rate-limit data is reconstructible and therefore
starts in the new `.volumes/valkey` directory.

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
uv sync --extra dev --locked
DATABASE_URL=sqlite:///test.db uv run pytest
uv run ruff check .
```

Frontend:

```sh
cd frontend
npm ci
npm run build
```

Validate the container configuration with `podman compose config`.
