# Deploying Clutch to Google Cloud Run

Two services: **backend** (FastAPI + LangGraph) and **frontend** (Next.js).
Deploy the backend first, then build the frontend with the backend's URL.

## Prerequisites

```bash
gcloud auth login
gcloud config set project YOUR_PROJECT_ID
gcloud services enable run.googleapis.com cloudbuild.googleapis.com artifactregistry.googleapis.com

# One-time Artifact Registry repo (used for the frontend image)
gcloud artifacts repositories create clutch --repository-format=docker --location=asia-south1
```

Set a region you like (examples use `asia-south1` / Mumbai):

```bash
export REGION=asia-south1
export PROJECT=$(gcloud config get-value project)
```

## 1. Backend

`gcloud run deploy --source` auto-detects `backend/Dockerfile`.

```bash
cd backend
gcloud run deploy clutch-backend \
  --source . \
  --region $REGION \
  --allow-unauthenticated \
  --set-env-vars "GOOGLE_API_KEY=YOUR_GEMINI_KEY,GEMINI_MODEL=gemini-2.5-flash,TIMEZONE=Asia/Kolkata"
```

Copy the service URL it prints, e.g. `https://clutch-backend-xxxx.a.run.app`. Verify:

```bash
curl https://clutch-backend-xxxx.a.run.app/api/health   # -> {"status":"ok"}
```

> Tip: store the key as a secret instead of plaintext:
> `--set-secrets GOOGLE_API_KEY=gemini-key:latest` (after `gcloud secrets create`).

## 2. Frontend

The backend URL is compiled into the client bundle, so pass it as a build arg.

```bash
cd ../frontend
export BACKEND_URL=https://clutch-backend-xxxx.a.run.app
export IMAGE=$REGION-docker.pkg.dev/$PROJECT/clutch/clutch-frontend

gcloud builds submit --config cloudbuild.yaml \
  --substitutions=_API_URL=$BACKEND_URL,_IMAGE=$IMAGE

gcloud run deploy clutch-frontend \
  --image $IMAGE \
  --region $REGION \
  --allow-unauthenticated
```

Open the frontend URL it prints — that is your submission link.

## Redeploys

- Backend code change → rerun step 1.
- Frontend change, or backend URL changed → rerun step 2.

## Notes

- CORS is open (`ALLOWED_ORIGINS=["*"]`, no cookies) so the browser can call the
  backend cross-origin and stream Server-Sent Events.
- The task store is in-memory and resets on cold start / new instance. For the demo,
  keep one instance warm: `--min-instances 1 --max-instances 1`. Swap `app/store.py`
  for Firestore to make it durable.
