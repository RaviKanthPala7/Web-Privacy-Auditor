# One-time setup: GitHub Actions → GCP Cloud Run

Do this once. After that, **push to `main`** deploys automatically.

> **JSON keys blocked?** If `gcloud iam service-accounts keys create` fails with `iam.disableServiceAccountKeyCreation`, use **Workload Identity Federation** below (recommended). No key file needed.

## What the workflows do

| Workflow | When | Action |
|----------|------|--------|
| `deploy.yml` | Push to **`main`** | Build images → deploy `privacy-api` + `privacy-web` → update CORS |
| `pr-check.yml` | **PR** targeting `main` | `npm run build` + `docker build` (no GCP) |

---

## A. Service account (Cloud Shell) — you may have done this already

```bash
export PROJECT_ID=web-privacy-auditor
export SA_NAME=github-actions-deploy
export SA_EMAIL="${SA_NAME}@${PROJECT_ID}.iam.gserviceaccount.com"

# Skip if already created
gcloud iam service-accounts create ${SA_NAME} \
  --display-name="GitHub Actions deploy" 2>/dev/null || true

for ROLE in run.admin artifactregistry.writer cloudbuild.builds.editor cloudbuild.builds.viewer logging.viewer storage.admin iam.serviceAccountUser; do
  gcloud projects add-iam-policy-binding ${PROJECT_ID} \
    --member="serviceAccount:${SA_EMAIL}" \
    --role="roles/${ROLE}"
done
```

---

## B. Workload Identity Federation (no JSON key)

Run in **Cloud Shell**. Replace repo if yours differs.

```bash
export PROJECT_ID=web-privacy-auditor
export PROJECT_NUMBER=$(gcloud projects describe $PROJECT_ID --format='value(projectNumber)')
export POOL_ID=github-pool
export PROVIDER_ID=github-provider
export SA_EMAIL="github-actions-deploy@${PROJECT_ID}.iam.gserviceaccount.com"
export REPO="RaviKanthPala7/Web-Privacy-Auditor"

gcloud iam workload-identity-pools create "${POOL_ID}" \
  --project="${PROJECT_ID}" \
  --location="global" \
  --display-name="GitHub Actions Pool" 2>/dev/null || true

gcloud iam workload-identity-pools providers create-oidc "${PROVIDER_ID}" \
  --project="${PROJECT_ID}" \
  --location="global" \
  --workload-identity-pool="${POOL_ID}" \
  --display-name="GitHub Provider" \
  --attribute-mapping="google.subject=assertion.sub,attribute.actor=assertion.actor,attribute.repository=assertion.repository,attribute.repository_owner=assertion.repository_owner" \
  --attribute-condition="assertion.repository=='${REPO}'" \
  --issuer-uri="https://token.actions.githubusercontent.com" 2>/dev/null || true

gcloud iam service-accounts add-iam-policy-binding "${SA_EMAIL}" \
  --project="${PROJECT_ID}" \
  --role="roles/iam.workloadIdentityUser" \
  --member="principalSet://iam.googleapis.com/projects/${PROJECT_NUMBER}/locations/global/workloadIdentityPools/${POOL_ID}/attribute.repository/${REPO}"

echo "Copy this into GitHub secret GCP_WORKLOAD_IDENTITY_PROVIDER:"
echo "projects/${PROJECT_NUMBER}/locations/global/workloadIdentityPools/${POOL_ID}/providers/${PROVIDER_ID}"
```

---

## C. GitHub secrets

Repo → **Settings** → **Secrets and variables** → **Actions** → **New repository secret**

| Secret name | Value |
|-------------|--------|
| `GCP_WORKLOAD_IDENTITY_PROVIDER` | Full line printed above (starts with `projects/`) |

You do **not** need `GCP_SA_KEY` when using Workload Identity.

---

## D. Push workflows

Commit `.github/workflows/` and push to `main`. Watch **Actions** → **Deploy to Cloud Run** (~10–20 min).

## Branch workflow

```text
feature/my-change  →  PR to main  →  pr-check.yml
merge PR           →  push to main →  deploy.yml
```

## Troubleshooting

| Error | Fix |
|-------|-----|
| `iam.disableServiceAccountKeyCreation` | Use section **B** (WIF), not JSON keys |
| `GCP_WORKLOAD_IDENTITY_PROVIDER` missing | Add secret from section **C** |
| `storage.objects.get` / `uploadArtifacts` denied | Grant roles in section **A** to `github-actions-deploy@...` |
| Deploy fails on port | API `--port 8000`, web `--port 8080` |
| `can only stream logs if you are Viewer` | Grant `logging.viewer` + `cloudbuild.builds.viewer` to deploy SA, or use `--async` in workflow (already in `deploy.yml`) |
