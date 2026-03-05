# JARVIS AI - Monorepo Structure

To maintain velocity across the frontend, mobile, desktop, and microservice backends, JARVIS uses a Turborepo/Nx style monorepo structure.

## Directory Tree

```bash
jarvis-ai-monorepo/
??? apps/
?   ??? web/                  # Next.js 15 Web Application
?   ??? mobile/               # React Native / Expo Application
?   ??? desktop/              # Electron wrapper + React UI
?   ??? api-gateway/          # Node.js Express/Fastify gateway
?   ??? orchestrator/         # Python FastAPI (LangGraph logic)
?   ??? memory-service/       # Python FastAPI (Vector DB interactions)
?   ??? automation-engine/    # Python (Celery Workers for OS/Web tasks)
?
??? packages/                 # Shared internal libraries
?   ??? ui-components/        # Shared Shadcn/React components (Web & Desktop)
?   ??? database-schema/      # Prisma or SQLAlchemy schemas & migrations
?   ??? types/                # Shared TypeScript definitions (API contracts)
?   ??? ai-core/              # Shared Python libraries for Prompts and LLM wrappers
?   ??? desktop-native/       # Rust/C++ bindings for deep OS-level system control
?
??? docs/                     # Engineering documentation (PRDs, ACs)
?   ??? architecture/
?   ??? api/
?
??? infrastructure/           # DevOps and Deployment
?   ??? terraform/            # AWS / GCP Infrastructure as Code
?   ??? k8s/                  # Kubernetes manifests / Helm charts
?   ??? docker/               # Dockerfiles for local compose setup
?
??? package.json
??? turbo.json
??? .github/
    ??? workflows/            # GitHub Actions CI/CD pipelines
```

## Monorepo Tooling

- **Build System:** `Turborepo` (for managing TS/JS cross-dependencies and caching build artifacts).
- **Python Package Management:** `Poetry` or `uv` within the Python specific folders (`apps/orchestrator`, `apps/memory-service`).
- **Containerization:** `Docker Compose` at the root level to spin up Postgres, Redis, Qdrant, and all local microservices simultaneously via `docker-compose up`.
- **Formatting/Linting:**
  - JS/TS: `ESLint` + `Prettier`
  - Python: `Ruff` + `MyPy`

## Shared Dependencies Flow

1. API Contracts defined in `packages/types/` are imported by `apps/web` and `apps/api-gateway`.
2. UI components are built once in `packages/ui-components/` and consumed by both Web and Electron (Desktop).
3. The core AI execution logic (Prompts, Agent tools) lives in `packages/ai-core/` and is consumed by `orchestrator` and `memory-service`.
