# Architecture

The system is an on-demand troubleshooting agent, not a Kubernetes controller or operator.

## Request flow

```text
User clicks "Investigate Cluster"
        |
FastAPI-authenticated API call
        |
Kubernetes investigation (pods, logs, events, deployments, network)
        |
AI reasoning (OpenRouter)
        |
Diagnosis shown to user and saved to InsForge
```

## Current status

- FastAPI health endpoint
- Authenticated `POST /investigate` evidence collection via kubectl
- AI root-cause analysis with confidence and kubectl recommendations
- Next.js dashboard with login, live progress, diagnosis, and history
- FastAPI-managed email/password accounts (JWT HS256, SQLite user store), live
  progress over Server-Sent Events (`GET /investigate/progress/{id}?token=`)
- InsForge used only for investigation history storage (server API key; the
  `auth.users` foreign key on `investigation_history` is dropped)
- Docker Compose

## Reliability guarantees

- `GET /clusters` lists every Kubernetes context from the backend kubeconfig;
  investigations run against the selected context (`kubectl --context <name>`).
- Missing or failed evidence is never reported as a healthy cluster: any failed
  evidence section (pods, logs, events, deployments, network) sets
  `cluster_healthy: false` and surfaces a beginner-friendly message.
- kubectl, timeout, connectivity, and authentication errors are translated by
  `app/kubernetes/errors.py` into actionable messages instead of stack traces.
- OpenRouter calls retry with backoff on transient failures (429/5xx) and fail
  the AI stage gracefully, keeping the collected evidence.
- Backend tests live in `backend/tests/`; real-cluster failure manifests live in
  `k8s-test-scenarios/`.
