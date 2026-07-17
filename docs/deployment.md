# Deployment & Scalability Plan

*Added 2026-07-17 (user-directed, pulled forward from the §7 Week-8 demo-build item).
Governs how CollusionGraph is packaged as a multi-service product and deployed on AWS
free-tier resources. The research prototype remains the priority; nothing here changes
the §4.5 evaluation protocol or the batch-offline inference decision (§3.2).*

## 1. What actually needs to run in production

The §3.2 architecture makes deployment unusually cheap, because **inference is
batch/offline by design** — the API serves precomputed artifacts and never touches a
GPU at request time:

| Workload | When it runs | Where it runs | Hardware |
|---|---|---|---|
| Ingest → features → train → score → explain | On demand (daily/weekly batch cadence) | Developer laptop / Colab / Kaggle GPU — **never on the serving box** | 1 consumer GPU or CPU |
| Artifact store (`alerts.parquet`, explanation bundles, `metrics.json`, DuckDB views) | Produced by batch, read by API | Object storage (S3) → pulled to the API container | none |
| **API** (FastAPI, read-only, §3.2) | Always on | Container | tiny CPU |
| **Frontend** (React static build, §5) | Always on | Static hosting/CDN | none |
| **Copilot** (Phase 2, §4.6 — SSE + external LLM API) | Always on (Phase 2 only) | Container beside the API | tiny CPU |

## 2. Service decomposition (the "separate containers" rule)

Three services, matching the §3.2 component contracts — each independently buildable,
replaceable, and scalable:

```
┌────────────┐   REST (read-only)   ┌─────────────┐   SSE + read-only   ┌─────────────┐
│  frontend   │ ───────────────────► │     api      │ ◄──────────────────│   copilot    │
│ nginx +     │                      │ FastAPI +    │                     │ (Phase 2)    │
│ React build │                      │ DuckDB over  │                     │ LangGraph +  │
└────────────┘                      │ /artifacts   │                     │ NIM/OpenAI   │
                                    └──────┬──────┘                     └──────┬──────┘
                                           │  pulls artifacts on start          │ env: LLM key
                                    ┌──────▼──────────────────────────────────────────┐
                                    │       artifact volume / S3 bucket (versioned)    │
                                    └──────────────────────────────────────────────────┘
```

Rules:
- The **ML pipeline is not a service** — it is a batch job whose only product is the
  artifact directory. Serving never imports torch (pinned by a test). Measured
  2026-07-17: the serving image builds at **815 MB** (polars/pyarrow/duckdb wheels)
  vs ~3.5 GB with torch — the single biggest cost/scalability lever. Container
  verified on Docker Desktop: build → run with read-only artifact mounts →
  endpoints serve with the caveat attached.
- Containers communicate only over the declared interfaces (REST/SSE); no shared code
  imports across service boundaries except the published artifact schema.
- One `docker-compose.yml` at the repo root runs the whole product locally
  (`docker compose up` = the §7 M5 demo path) and doubles as the deployment blueprint.

**Docker verdict: useful, adopted** — precisely because the images built for the local
demo are byte-identical to what EC2/ECS/Lambda run in production (dev/prod parity), and
because it enforces the serving-never-imports-torch boundary at build time. Dockerfiles
land **with the API implementation (§7 step 22)**, not before — there is nothing to
containerize until the API exists.

## 3. AWS mapping — free-tier first

The AWS Free Tier changed in July 2025: new accounts get **$100 signup credit + up to
$100 more** for completing onboarding activities, a **6-month free account plan** (no
charges until you upgrade), and **30+ always-free services**; the legacy
"12-months-free t2.micro" model is gone ([AWS announcement](https://aws.amazon.com/blogs/aws/aws-free-tier-update-new-customers-can-get-started-and-explore-aws-with-up-to-200-in-credits/),
[free-tier page](https://aws.amazon.com/free/), [FAQ](https://aws.amazon.com/free/free-tier-faqs/)).

### Track A — capstone demo (runs entirely on credits, ~$0 out of pocket)

| Piece | AWS service | Free-tier reality |
|---|---|---|
| Frontend | **S3 static site + CloudFront** | CloudFront always-free: 1 TB egress + 10M requests/month — effectively $0 forever |
| API (+Copilot later) | **one small EC2 instance** (t4g.small ~ $12–15/mo) running `docker compose up` | Paid, but covered by the $100–$200 credits for ≈ the whole capstone window |
| Artifact store | **S3 bucket** (artifacts are MBs, not GBs) | Pennies; within credits |
| Batch ML | **not on AWS** — local GPU / Colab / Kaggle | $0 |
| Demo data egress | first 100 GB/month outbound free account-wide | $0 at demo traffic |

### Track B — the scalability story (what the paper/product pitch cites)

1. **Scale to zero:** package the API as a **Lambda container image** (FastAPI via the
   Mangum adapter; artifacts baked into the image or on EFS) behind API Gateway —
   always-free tier: 1M requests + 400k GB-s/month. At screening-tool traffic
   (analyst teams, not consumers) this is $0/month indefinitely. SSE for the Copilot
   uses Lambda response streaming or moves that one service to the EC2/Fargate tier.
2. **Scale up:** the same three images move unchanged to **ECS Fargate** behind an ALB
   (multi-AZ, autoscaling on CPU) when concurrent-user counts justify it
   (~$30–70/month at small scale). Artifacts stay on S3 + CloudFront; DuckDB reads are
   per-container and embarrassingly parallel — the API is stateless, so horizontal
   scaling is trivial.
3. **Scale the ML:** batch scoring cadence (daily/weekly) means training scale is a
   *throughput* problem, not a latency one — AMLworld-Medium-sized runs rent one cloud
   GPU spot instance per run (§4.1 already budgets this) and write artifacts back to S3.
   No GPU is ever provisioned 24/7.

### Cost summary

| Phase | Monthly cost |
|---|---|
| Capstone/demo (Track A, within 6-month credit window) | **$0 out of pocket** (≈$15/mo drawn from credits for EC2; everything else always-free) |
| Post-credit, low traffic (Track B serverless) | **≈$0–5** (Lambda+API GW+S3+CloudFront all inside always-free tiers; egress <100 GB) |
| Post-credit, always-on small EC2 alternative | ≈$12–18 (t4g.small + EBS) |
| Growth (Fargate ×3 services + ALB) | ≈$40–80 |

**Guardrails:** create the account on the *free account plan* (hard $0 until upgraded);
set an AWS Budgets alert at $1 (also one of the credit-earning activities); never attach
a GPU instance to serving; artifacts versioned in S3 so a bad batch run is a one-line
rollback (`s3://…/runs/<run_id>/`).

## 4. Sequencing

1. **Week 7 (§7 step 22)** — build the FastAPI service → add `Dockerfile.api`,
   `frontend/Dockerfile` (Week 8), root `docker-compose.yml`; verify with Docker
   Desktop locally.
2. **Week 8 (M5)** — `docker compose up` is the demo exit criterion, unchanged.
3. **Post-M5 / MC** — S3+CloudFront frontend + one EC2 on credits (Track A);
   Lambda-container experiment as a stretch (Track B proof).
4. Copilot container joins at Week 11 with its LLM key via env (NVIDIA NIM preferred —
   see PROGRESS.md decision log).
