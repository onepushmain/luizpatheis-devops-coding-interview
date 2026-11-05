---
artifact_contract: ce-unified-plan/v1
product_contract_source: ce-brainstorm
status: implementation-ready
date: 2026-11-05
---

# CI/CD pipeline to GKE with Helm, plus rollback

## Goal Capsule

- **Objective:** Deliver PDF Item 1 for the SecureFlight API. A GitHub Actions pipeline runs on pushes to `main` and on PRs that target `main`. It builds the app and runs the existing tests. When the tests pass, it publishes an image and deploys it to GKE. Bonus: a rollback workflow.
- **Product authority:** "DevOps Coding Exercise" PDF (BEON.tech) and decisions the user made in this session.
- **Open blockers:** none.

## Product Contract

### Requirements

- **R1** The workflow triggers on `push` to `main` and on `pull_request` that targets `main`. (PDF 1a)
- **R2** The workflow builds the app as a container image. (PDF 1b)
- **R3** The workflow runs the existing pytest suite, unchanged. (PDF 1c)
- **R4** Only after R3 passes, and only on `main`, the workflow pushes the image and deploys it to GKE. A PR builds the image but does not push or deploy it. (PDF 1d)
- **R5** The docs list every secret, variable, and env var that the workflows use. (PDF constraint)
- **R6** A manually triggered workflow rolls the release back to the previous revision or to a revision that the operator chooses. (PDF bonus)
- **R7** The docs record the assumptions and design decisions. (PDF general)

### Key Decisions

- **KD1** Target is **GKE + Helm**. (decided during brainstorm)
- **KD2** Pipeline is **GitHub Actions**, because the repo is on GitHub. (design call)
- **KD3** Auth is **Workload Identity Federation**: GitHub OIDC to a GCP service account. No JSON keys are stored. (design call)
- **KD4** The registry is **Artifact Registry**. The image tag is the full git SHA, which is immutable and traceable. (design call)
- **KD5** Deploy runs `helm upgrade --install --atomic --wait`. A failed rollout reverts automatically. Each release creates a Helm revision, and R6 uses those revisions. (design call)
- **KD6** Strict scope split. The PDF says Item 2 (IaC: VPC, Mongo, API wiring) **must not be written in agent mode**. This change ships no Terraform. The Helm chart is the deployable unit that CI/CD needs. The hand-written IaC owns the VPC, the GKE cluster, Mongo, and the `secureflight-api-mongo` Secret. (decided during brainstorm: follow the PDF rules strictly)
- **KD7** Tests run with `PYTHONPATH=api` on Python 3.12, so the existing suite runs unmodified. `api/main.py` imports `flights.router` without the `api.` prefix, and the pinned wheels do not build on 3.14. (verified locally: 2 passed)
- **KD8** Third-party actions are pinned to full commit SHAs, with the version in a comment. (design call)

### Non-goals

- Application code fixes. Example: `service.get_flights` ignores `skip`. This is noted only.
- Terraform or IaC of any kind (see KD6).
- Multi-environment promotion and preview environments. These are listed as future work.

### Success criteria

- `actionlint` is clean, `helm lint` is clean, and `helm template` renders.
- `docker build` succeeds locally, and the container answers `GET /` with 204.
- Every secret and variable referenced in the workflows appears in `docs/ci-cd.md`.

## Implementation Units

- **U1 `Dockerfile` + `.dockerignore`.** `python:3.12-slim`, multi-stage, non-root UID 10001, `PYTHONPATH=/app:/app/api`, `uvicorn api.main:app` on port 8000, with a HEALTHCHECK.
- **U2 `deploy/helm/secureflight-api/`.** Contains a Deployment (probes on `/`, topology spread, restricted securityContext, read-only root filesystem, pull by digest), a Service (ClusterIP), a ServiceAccount, an optional NetworkPolicy (ingress 8000; egress DNS + Mongo peers supplied by the infra layer), and a PodDisruptionBudget. `MONGO_URI` comes from an existing Secret. `MONGO_DB_NAME` is a value.
- **U3 `.github/workflows/ci-cd.yml`** — jobs `test` → `build` (PR + main, no OIDC) → `publish` (main, push + SBOM/provenance, digest output) → `deploy` (main, `--atomic` by digest, in-cluster API→Mongo smoke test with auto-rollback). `production` environment for cloud jobs; per-job least-privilege permissions.
- **U4 `.github/workflows/rollback.yml`** — `workflow_dispatch` (`revision` optional, `reason` required); empty revision resolves to the last good revision running a different image; `helm rollback --wait`, rollout check, summary.
- **U5 `docs/ci-cd.md`.** Covers the flow, secrets and variables, the one-time GCP setup, how to roll back, assumptions, and decisions. The README links to it.

## Verification

Run `actionlint`, `helm lint`, `helm template | kubeconform`, `docker build`, and a container smoke test. Independent review subagents check the change before the push.
