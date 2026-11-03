# NudgeOps | AI-Powered Kubernetes Incident & Root Cause Analysis

### Overview

NudgeOps combines Kubernetes diagnostics with LLM-based reasoning to automate incident investigation, identify probable root causes, and generate actionable remediation recommendations.

### Capabilities

- **Cluster Diagnostics:** Kubernetes resource inspection and evidence collection.
- **Root Cause Analysis:** AI-assisted analysis of cluster state, logs, and events.
- **Remediation:** Confidence scoring and actionable resolution recommendations.
- **Live Investigations:** Real-time progress updates and investigation history.

### Architecture

```text
       Next.js Dashboard
               |
               v
         FastAPI Backend
               |
       +-------+-------+
       |               |
       v               v
 Kubernetes API    OpenRouter LLM
       |               |
       +-------+-------+
               |
               v
      Incident Analysis
       & Resolutions
               |
               v
          PostgreSQL
```

### Tech Stack

| Component | Technologies |
|---|---|
| Frontend | Next.js, TypeScript, Tailwind CSS |
| Backend | Python, FastAPI |
| AI Integration | OpenRouter, LLMs |
| Infrastructure | Kubernetes, Docker |
| Database | PostgreSQL |

---
