#!/usr/bin/env bash
# Task 0.1: create the GCP project HOLD deploys to, with Workload Identity Federation for GitHub
# Actions (no JSON key anywhere) and the Secret Manager entries deploy.yml reads. Idempotent: every
# step checks before it creates. Run under the account that owns the trial credits:
#
#   gcloud auth login                      # pick the trial account in the browser
#   HOLD_BILLING_ACCOUNT=XXXXXX-XXXXXX-XXXXXX bash scripts/gcp_setup.sh
#
# Then set the runtime secret values (none are committed):
#   printf '%s' "<bootstrap>" | gcloud secrets versions add CONFLUENT_BOOTSTRAP --data-file=- --project hold-2026
# and record the WIF provider id in PLAN.md Notes.
set -u
PROJECT_ID="${HOLD_PROJECT_ID:-hold-2026}"
REGION="${HOLD_REGION:-us-central1}"
REPO="${HOLD_GITHUB_REPO:-StephenSook/hold}"
CONFIG="${HOLD_GCLOUD_CONFIG:-hold}"
POOL="github"; PROVIDER="hold-repo"; SA_NAME="hold-deploy"

step() { printf '\n== %s\n' "$*"; }
need() { command -v "$1" >/dev/null 2>&1 || { echo "missing: $1"; exit 1; }; }
need gcloud; need gh

step "gcloud configuration ${CONFIG} (keeps other projects' default config untouched)"
# The account is read before switching configurations (a fresh configuration has none active);
# HOLD_ACCOUNT overrides it so the trial account is named explicitly.
ACCOUNT="${HOLD_ACCOUNT:-$(gcloud auth list --filter=status:ACTIVE --format='value(account)' | head -1)}"
[ -n "$ACCOUNT" ] || { echo "no active gcloud account: run gcloud auth login first or set HOLD_ACCOUNT"; exit 1; }
if ! gcloud config configurations describe "$CONFIG" >/dev/null 2>&1; then
  gcloud config configurations create "$CONFIG" --no-activate || exit 1
fi
gcloud config configurations activate "$CONFIG" || exit 1
gcloud config set account "$ACCOUNT" >/dev/null && gcloud config set project "$PROJECT_ID" >/dev/null
echo "account ${ACCOUNT}, project ${PROJECT_ID}"

step "project"
if ! gcloud projects describe "$PROJECT_ID" >/dev/null 2>&1; then
  gcloud projects create "$PROJECT_ID" --name="HOLD" || exit 1
fi
PROJECT_NUMBER="$(gcloud projects describe "$PROJECT_ID" --format='value(projectNumber)')"
echo "project number ${PROJECT_NUMBER}"

step "billing"
if [ "$(gcloud billing projects describe "$PROJECT_ID" --format='value(billingEnabled)' 2>/dev/null)" != "True" ]; then
  [ -n "${HOLD_BILLING_ACCOUNT:-}" ] || { echo "billing not linked: set HOLD_BILLING_ACCOUNT (gcloud billing accounts list)"; exit 1; }
  gcloud billing projects link "$PROJECT_ID" --billing-account="$HOLD_BILLING_ACCOUNT" || exit 1
fi

step "APIs"
gcloud services enable run.googleapis.com cloudbuild.googleapis.com artifactregistry.googleapis.com \
  secretmanager.googleapis.com aiplatform.googleapis.com iamcredentials.googleapis.com iam.googleapis.com \
  sts.googleapis.com --project "$PROJECT_ID" || exit 1

step "Artifact Registry repository hold (${REGION})"
if ! gcloud artifacts repositories describe hold --location="$REGION" --project "$PROJECT_ID" >/dev/null 2>&1; then
  gcloud artifacts repositories create hold --repository-format=docker --location="$REGION" --project "$PROJECT_ID" || exit 1
fi

step "deploy service account"
SA="${SA_NAME}@${PROJECT_ID}.iam.gserviceaccount.com"
if ! gcloud iam service-accounts describe "$SA" --project "$PROJECT_ID" >/dev/null 2>&1; then
  gcloud iam service-accounts create "$SA_NAME" --display-name="HOLD deploy (GitHub Actions via WIF)" --project "$PROJECT_ID" || exit 1
fi
for role in roles/run.admin roles/iam.serviceAccountUser roles/artifactregistry.writer roles/secretmanager.secretAccessor; do
  gcloud projects add-iam-policy-binding "$PROJECT_ID" --member="serviceAccount:${SA}" --role="$role" --condition=None --quiet >/dev/null || exit 1
done
# Cloud Run runs as the default compute service account; it must read the secrets deploy.yml mounts.
COMPUTE_SA="${PROJECT_NUMBER}-compute@developer.gserviceaccount.com"
gcloud projects add-iam-policy-binding "$PROJECT_ID" --member="serviceAccount:${COMPUTE_SA}" --role="roles/secretmanager.secretAccessor" --condition=None --quiet >/dev/null || exit 1
gcloud projects add-iam-policy-binding "$PROJECT_ID" --member="serviceAccount:${COMPUTE_SA}" --role="roles/aiplatform.user" --condition=None --quiet >/dev/null || exit 1

step "Workload Identity Federation pool ${POOL}, provider ${PROVIDER}, bound to ${REPO}"
if ! gcloud iam workload-identity-pools describe "$POOL" --location=global --project "$PROJECT_ID" >/dev/null 2>&1; then
  gcloud iam workload-identity-pools create "$POOL" --location=global --display-name="GitHub Actions" --project "$PROJECT_ID" || exit 1
fi
if ! gcloud iam workload-identity-pools providers describe "$PROVIDER" --workload-identity-pool="$POOL" --location=global --project "$PROJECT_ID" >/dev/null 2>&1; then
  gcloud iam workload-identity-pools providers create-oidc "$PROVIDER" --workload-identity-pool="$POOL" --location=global \
    --issuer-uri="https://token.actions.githubusercontent.com" \
    --attribute-mapping="google.subject=assertion.sub,attribute.repository=assertion.repository" \
    --attribute-condition="assertion.repository == '${REPO}'" --project "$PROJECT_ID" || exit 1
fi
POOL_NAME="$(gcloud iam workload-identity-pools describe "$POOL" --location=global --project "$PROJECT_ID" --format='value(name)')"
gcloud iam service-accounts add-iam-policy-binding "$SA" --role=roles/iam.workloadIdentityUser \
  --member="principalSet://iam.googleapis.com/${POOL_NAME}/attribute.repository/${REPO}" --project "$PROJECT_ID" --quiet >/dev/null || exit 1
WIF_PROVIDER="$(gcloud iam workload-identity-pools providers describe "$PROVIDER" --workload-identity-pool="$POOL" --location=global --project "$PROJECT_ID" --format='value(name)')"
echo "WIF provider ${WIF_PROVIDER}"

step "Secret Manager entries deploy.yml mounts (values added separately; placeholders for the ones not yet known)"
# macOS ships bash 3.2 (no associative arrays), so the defaults are a case statement.
default_for() {
  case "$1" in
    GEMINI_MODEL) printf '%s' "gemini-3.1-flash-lite" ;;
    GOOGLE_CLOUD_PROJECT) printf '%s' "$PROJECT_ID" ;;
    GOOGLE_CLOUD_LOCATION) printf '%s' "$REGION" ;;
    GOOGLE_GENAI_USE_ENTERPRISE) printf '%s' "true" ;;
    *) printf '%s' "unset" ;;  # Secret Manager refuses an empty payload; the API reads "unset" as absent
  esac
}
for name in GEMINI_MODEL GOOGLE_CLOUD_PROJECT GOOGLE_CLOUD_LOCATION GOOGLE_GENAI_USE_ENTERPRISE CONFLUENT_BOOTSTRAP CONFLUENT_API_KEY CONFLUENT_API_SECRET; do
  if ! gcloud secrets describe "$name" --project "$PROJECT_ID" >/dev/null 2>&1; then
    gcloud secrets create "$name" --replication-policy=automatic --project "$PROJECT_ID" || exit 1
  fi
  if [ -z "$(gcloud secrets versions list "$name" --filter=state:ENABLED --format='value(name)' --project "$PROJECT_ID" 2>/dev/null)" ]; then
    default_for "$name" | gcloud secrets versions add "$name" --data-file=- --project "$PROJECT_ID" >/dev/null || exit 1
    echo "added version to ${name}"
  fi
done

step "GitHub Actions secrets on ${REPO}"
gh secret set WIF_PROVIDER -R "$REPO" --body "$WIF_PROVIDER" || exit 1
gh secret set WIF_SERVICE_ACCOUNT -R "$REPO" --body "$SA" || exit 1
gh secret set GCP_PROJECT -R "$REPO" --body "$PROJECT_ID" || exit 1
gh secret set GCP_PROJECT_NUMBER -R "$REPO" --body "$PROJECT_NUMBER" || exit 1
gh secret list -R "$REPO"

step "done: gcloud config get-value project"
gcloud config get-value project
echo "Record in PLAN.md Notes: WIF provider ${WIF_PROVIDER}; service account ${SA}; project number ${PROJECT_NUMBER}"
