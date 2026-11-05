# CI/CD: SecureFlight API

Two GitHub Actions workflows build, test, and deploy the SecureFlight API to **Google Kubernetes Engine (GKE)** with **Helm**.

| Workflow | File | Trigger |
|---|---|---|
| CI/CD | [`.github/workflows/ci-cd.yml`](../.github/workflows/ci-cd.yml) | `push` to `main`, `pull_request` targeting `main` |
| Rollback (bonus) | [`.github/workflows/rollback.yml`](../.github/workflows/rollback.yml) | Manual (`workflow_dispatch`) |

## Pipeline flow

```
 PR -> main     ┌──────┐   ┌─────────────────────────────┐
 ──────────────▶│ test │──▶│ build: helm lint/template   │   stops here: no cloud credentials
                └──────┘   │ docker build · smoke GET /  │
                           └─────────────────────────────┘
 push -> main   ┌──────┐   ┌───────┐   ┌──────────────────────────┐   ┌──────────────────────────────┐
 ──────────────▶│ test │──▶│ build │──▶│ publish: push to Artifact │──▶│ deploy: helm upgrade --atomic │
                └──────┘   └───────┘   │ Registry + SBOM/provenance│   │ smoke API→Mongo · auto-revert │
                                       └──────────────────────────┘   └──────────────────────────────┘
```

| Job | Runs on | What it does |
|---|---|---|
| `test` | PR + main | Sets up Python 3.12 with a pip cache. Runs the existing `pytest` suite and uploads the JUnit report as the `test-results` artifact. |
| `build` | PR + main | Lints and renders the Helm chart, builds the Docker image with the GitHub Actions layer cache, and runs the container with a read-only filesystem. The container must answer `GET /` with `204`. **No `id-token` permission**, so this job can never get cloud credentials. |
| `publish` | main only | Uses Workload Identity Federation to push `…/secureflight-api:<git-sha>` with an SBOM and SLSA provenance (`mode=max`). Outputs the **image digest**. |
| `deploy` | main only | See the steps below. |

The `deploy` job runs these steps:

1. Fails early if the release is stuck in `pending-*`.
2. Runs `helm upgrade --install --atomic`, pinned to the **image digest**. The revision description records the commit.
3. Runs a smoke test from inside the cluster: `GET /flights?limit=1` through the Service. The pod probes only call `GET /`, which never touches Mongo, so this step is what proves the database path. If it fails, the job runs `helm rollback` automatically.
4. Writes the release history to the job summary.

`publish` and `deploy` run in the `production` GitHub environment.

## Rollback

Go to **Actions → rollback → Run workflow** and fill in two inputs:

- `revision`: a Helm revision number from the deploy summary, or from `helm history secureflight-api -n <ns>`. Each entry's description holds `sha=<commit>`. Leave it empty to pick the **last good revision that ran a different image**. This is not always "current − 1". After a revert the history reads N (good), N+1 (bad), N+2 (rollback to N), and going back one step would choose the broken release. So the automatic choice skips failed revisions and any revision that was itself rolled away from. When the release is stuck in `pending-*`, it picks the last `deployed` revision.
- `reason`: required. It is written to the run summary as an audit trail.

The workflow then runs `helm rollback --wait`, verifies with `kubectl rollout status`, and writes the summary.

Things to know:

- A rollback creates a **new** Helm revision that runs the old image. The next push to `main` deploys again, so fix the bad commit with `git revert`.
- Deploy and rollback share the `deploy-production` concurrency group, so they never run at the same time. GitHub keeps only **one pending** run per group: if a deploy is queued while a rollback is already waiting, the older waiting run is cancelled. Check that your rollback run actually completed.
- History is capped at 10 revisions (`--history-max 10`). Older revision numbers disappear.
- If a cancelled run leaves the release in `pending-upgrade`, running `rollback` clears it.

## Secrets and variables

The `publish`, `deploy` and `rollback` jobs run in the **`production` environment**. Define these values on that environment, or at repository level. The `test` and `build` jobs read none of them.

### Secrets

| Name | Description |
|---|---|
| `GCP_WORKLOAD_IDENTITY_PROVIDER` | Provider resource name, e.g. `projects/123456789/locations/global/workloadIdentityPools/github/providers/github-oidc` |
| `GCP_SERVICE_ACCOUNT` | Deployer service account email |

No service-account JSON key is used. GitHub's OIDC token is exchanged for a short-lived GCP token.

### Variables

| Name | Example | Description |
|---|---|---|
| `GCP_PROJECT_ID` | `secureflight-prod` | GCP project |
| `GCP_REGION` | `us-central1` | Artifact Registry region |
| `GAR_REPOSITORY` | `secureflight` | Artifact Registry Docker repository |
| `GKE_CLUSTER` | `secureflight-prod-gke` | GKE cluster name |
| `GKE_LOCATION` | `us-central1` | Cluster region or zone |
| `K8S_NAMESPACE` | `secureflight` | Release namespace (must exist) |
| `MONGO_EGRESS_CIDR` | `10.10.1.0/24` | *Optional.* CIDR of the Mongo host. When set, the deploy enables the chart's NetworkPolicy and limits egress to DNS and this CIDR on port 27017. |

### Workflow-level env (hard-coded, non-secret)

| Name | Value | Why |
|---|---|---|
| `PYTHON_VERSION` | `3.12` | The pinned wheels (`pydantic-core`, `uvloop`, …) fail to build on Python 3.14 (verified) |
| `PYTHONPATH` (test job) | `api` | `api/main.py` imports `flights.router` without the `api.` prefix |
| `MONGO_URI` / `MONGO_DB_NAME` (test job) | dummy values | `Settings()` requires them. The tests use `mongomock`, so no database is contacted. |
| `HELM_RELEASE`, `CHART_PATH`, `IMAGE_NAME`, `HELM_VERSION` | see the workflow | Single place to rename or upgrade |

### Runtime configuration of the app

| Env var | Source |
|---|---|
| `MONGO_URI` | Kubernetes Secret `secureflight-api-mongo`, key `MONGO_URI`. It is **not** created by the chart or the pipeline. |
| `MONGO_DB_NAME` | Helm value `mongo.dbName` (default `flights`) |

## Prerequisites (pipeline contract)

The pipeline expects these to exist. It does not create any of them. They belong to the infrastructure layer (exercise item 2), which is written separately.

- **Artifact Registry**: a Docker repository named `GAR_REPOSITORY`.
- **GKE cluster**:
  - It is named `GKE_CLUSTER`.
  - The namespace `K8S_NAMESPACE` exists.
  - The control plane is reachable from GitHub-hosted runners. The workflows use the GKE DNS-based endpoint (`use_dns_based_endpoint: true`).
- **Secret**: `secureflight-api-mongo`, key `MONGO_URI`, in that namespace.
- **Workload Identity Federation**: a provider trusted for this repository's GitHub OIDC tokens. The trust must be limited to `main` or the `production` environment, not to the whole repository. Otherwise any branch could get deploy credentials.
- **Deployer identity** with exactly these rights:
  - push to the Artifact Registry repository
  - get cluster credentials
  - manage the release's objects in `K8S_NAMESPACE`
- **GitHub `production` environment**:
  - deployment branches restricted to `main`
  - required reviewers (optional). Both `publish` and `deploy` use this environment, so a push to `main` asks for approval twice.
- **Pod Security**: the post-deploy smoke test runs a `curlimages/curl` pod with no `securityContext`. If the namespace enforces the Pod Security `restricted` level, that pod is rejected; allow the `baseline` level instead.

## Helm chart

The chart lives at `deploy/helm/secureflight-api/`.

| Resource | Notes |
|---|---|
| Deployment | 2 replicas spread across nodes. Rolling update with `maxUnavailable: 0`. Liveness and readiness probes on `GET /`. Runs as non-root (uid 10001) with a read-only root filesystem and all capabilities dropped. Uses the seccomp `RuntimeDefault` profile. Does not mount the ServiceAccount token. |
| Service | `ClusterIP` on port 80, forwarding to 8000 |
| ServiceAccount | Annotate it for GKE Workload Identity if the app ever calls GCP APIs |
| NetworkPolicy | Optional. Default deny. Ingress is allowed only on 8000. Egress is allowed only to DNS (kube-dns, NodeLocal DNSCache, Cloud DNS) and to the Mongo peers. Rendering fails if it is enabled without a Mongo destination. |
| PodDisruptionBudget | `minAvailable: 1` |

Image rules:

- `image.tag` must be set, and `latest` is rejected.
- When `image.digest` is set, the pod pulls by digest. The pipeline always sets it.

Exposing the API outside the cluster (Ingress or Gateway) is left to the platform. Google Cloud Load Balancer health checks expect `200`, but `GET /` returns `204`. Point the health check at `/openapi.json`, and allow `35.191.0.0/16` and `130.211.0.0/22` in `networkPolicy.ingressFrom`.

## Assumptions and design decisions

- **GKE + Helm.** Helm's revision history (`helm history` / `helm rollback`) is the backbone of the rollback bonus. `--atomic` reverts failed rollouts with no operator involved.
- **Immutable artifacts.** Images are tagged with the git SHA and deployed **by digest**. There is no mutable `latest` tag. Each image ships with an SBOM and build provenance.
- **Credentials only where needed.**
  - `test` and `build` cannot request an OIDC token, so PRs (including PRs from forks) never reach the cloud. They still prove that the image builds and starts.
  - `publish`, `deploy` and `rollback` run in the `production` environment, which only `main` can use.
- **Rollback safety in layers.**
  1. `--atomic` reverts a rollout that never becomes ready.
  2. The post-deploy smoke test reverts a rollout that is healthy but can't reach Mongo.
  3. `rollback.yml` handles a bad release that passed both checks.
  4. A `git revert` makes the fix permanent.
- **Supply chain.**
  - Every action is pinned to a full commit SHA, with its version in a comment.
  - The base image is pinned by digest. Dependabot keeps actions, the base image and pip deps current.
  - `GITHUB_TOKEN` defaults to `contents: read`, and checkout uses `persist-credentials: false`.
  - Workflow inputs pass through env vars and are never interpolated into shell.
- **Application code is unchanged.** Known issues are recorded here instead of fixed:
  - Imports are inconsistent (`flights.router` vs `api.flights.*`). `PYTHONPATH` works around it.
  - `service.get_flights` ignores `skip`.
  - Test dependencies (`pytest`, `mongomock`) ship in the runtime image because there is a single `requirements.txt`.
- **Scope split.** The exercise requires item 2 (IaC: VPC, MongoDB, API wiring) to be written without agent mode. This change contains no Terraform and does not design that layer. The section above lists only what the pipeline expects to exist.

### Future work

- Image vulnerability scanning (Trivy or Artifact Analysis) as a blocking gate.
- Keyless `cosign` signing enforced by Binary Authorization.
- Per-PR preview environments.
- Canary releases (Argo Rollouts or Gateway traffic splitting).
- GitOps (Argo CD) to remove the need for runners to reach the control plane.

## Local equivalents

```bash
# tests (same as CI)
PYTHONPATH=api MONGO_URI=mongodb://localhost:27017 MONGO_DB_NAME=flights_test python -m pytest

# chart
helm lint deploy/helm/secureflight-api --strict --set image.tag=dev
helm template secureflight-api deploy/helm/secureflight-api --set image.tag=dev

# image + smoke test
docker build -t secureflight-api:dev .
docker run --rm -p 8000:8000 -e MONGO_URI=mongodb://host.docker.internal:27017 -e MONGO_DB_NAME=flights secureflight-api:dev
curl -i http://localhost:8000/   # 204
```
