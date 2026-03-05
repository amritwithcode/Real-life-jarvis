# JARVIS AI - Environment & DevOps

This document outlines the infrastructure, deployment strategy, and environment lifecycle for JARVIS AI.

## 1. Environments

The standard promotion path is: **Local -> Development -> Staging -> Production**.

1.  **Local (Developers):**
    - Docker Compose spins up Postgres, Redis, Qdrant, and mock LLM endpoints natively.
2.  **Development (DEV):**
    - Automatically deployed on every merge to `main`.
    - Hosted on AWS EKS (Elastic Kubernetes Service) with small node pools.
    - Used by internal QA and Product teams to test new automations.
3.  **Staging (STG):**
    - Identical mirror of Production.
    - Deploys trigger via explicit GitHub Release tag (e.g., `v1.0.0-rc1`).
    - Subject to automated load testing and API contract testing.
4.  **Production (PROD):**
    - Multi-Availability Zone (Multi-AZ) EKS deployment.
    - Auto-scaling groups triggered by CPU/Memory and concurrent WebSocket connections.
    - Deploys require manual approval from Engineering Lead.

## 2. CI/CD Pipeline (GitHub Actions)

**Trigger: Pull Request to `main`**

1.  **Linters & Type Check:** Run ESLint, Prettier, Ruff, MyPy.
2.  **Unit Tests:** Jest for Frontend/API, PyTest for Python Orchestrator and NLP layers.
3.  **Security Scan:** CodeQL and Snyk for dependency vulnerability checks.
4.  **Build:** TurboRepo checks cache and builds Docker images.

**Trigger: Merge to `main`**

1.  Push Docker semantic tags to AWS ECR.
2.  ArgoCD detects new ECR tags and rolls out Kubernetes pods to the DEV cluster via Blue/Green deployment to ensure zero downtime.

## 3. Infrastructure Layout (AWS Primary)

- **Compute:** Amazon EKS for running microservices.
- **Database:** Amazon RDS (PostgreSQL 16) with read replicas.
- **Vector DB:** Qdrant hosted on dedicated EC2 memory-optimized instances or managed Qdrant Cloud.
- **Cache:** Amazon ElastiCache (Redis 7).
- **Queues:** Amazon SQS or managed RabbitMQ for background tasks (e.g., Memory Summarization).
- **Storage:** Amazon S3 for user file uploads, chat backups.
- **DNS & Edge:** Cloudflare for CDN, DDoS protection, and SSL termination. WebSockets proxy through Cloudflare.

## 4. Observability & Monitoring

- **Logging:** Datadog agent installed on all EKS nodes to centralize standard output (stdout/stderr).
- **Metrics:** Prometheus & Grafana for system-level metrics (CPU, Memory, Network).
- **Tracing:** OpenTelemetry tracing injected into all requests to visually track a request from API Gateway -> Orchestrator -> Groq API -> Client (crucial for <4s latency debugging).
- **Alerting:** PagerDuty integration for P95 Latency spikes (>5s) or API 5xx error rate limits.
