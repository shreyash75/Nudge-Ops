# NudgeOps | AI-Powered Kubernetes Incident & Root Cause Analysis

NudgeOps is an AI-powered Kubernetes troubleshooting platform designed to simplify incident investigation and root cause analysis. It connects to a Kubernetes cluster, collects operational signals such as pod status, logs, events, and deployment information, and uses LLM-based reasoning to identify potential causes and recommend corrective actions.

The platform brings cluster diagnostics and AI-assisted troubleshooting together through a centralized dashboard.

## Architecture

NudgeOps follows a modular architecture with five primary layers:

```text
                  ┌─────────────────────────┐
                  │    Kubernetes Cluster   │
                  │                         │
                  │  Pods, Logs, Events,    │
                  │  Deployments, Services  │
                  └────────────┬────────────┘
                               │
                               ▼
                  ┌─────────────────────────┐
                  │  Investigation Layer   │
                  │                         │
                  │  Cluster Diagnostics   │
                  │  Log & Event Collection│
                  │  Workload Inspection   │
                  │  Network Diagnostics   │
                  └────────────┬────────────┘
                               │
                               ▼
                  ┌─────────────────────────┐
                  │   AI Reasoning Engine  │
                  │                         │
                  │  LLM-Based Analysis    │
                  │  Signal Correlation    │
                  │  Root Cause Detection  │
                  │  Fix Recommendations   │
                  └────────────┬────────────┘
                               │
                               ▼
                  ┌─────────────────────────┐
                  │     FastAPI Backend    │
                  │                         │
                  │  Investigation APIs    │
                  │  Orchestration         │
                  │  Authentication       │
                  │  History & Persistence │
                  └────────────┬────────────┘
                               │
                               ▼
                  ┌─────────────────────────┐
                  │    Frontend Dashboard  │
                  │                         │
                  │  Incident Reports      │
                  │  Investigation Status  │
                  │  Root Cause Analysis   │
                  │  Suggested Resolutions │
                  └─────────────────────────┘
```

### Investigation Workflow

1. A user initiates an investigation from the dashboard.
2. The FastAPI backend orchestrates the investigation.
3. Kubernetes APIs are queried to collect cluster state, logs, events, and workload information.
4. Collected evidence is structured and passed to the AI reasoning engine.
5. The LLM analyzes correlated signals to identify probable root causes and generate remediation suggestions.
6. Investigation results and history are made available through the dashboard.

## Key Capabilities

- **Cluster Diagnostics:** Inspect pods, deployments, services, and workload health.
- **Log & Event Analysis:** Collect and analyze Kubernetes logs and events to identify failure patterns.
- **AI-Powered RCA:** Correlate multiple diagnostic signals to determine probable root causes.
- **Remediation Suggestions:** Generate actionable troubleshooting steps and recommended configuration changes.
- **Investigation History:** Maintain records of previous investigations and their findings.
- **Live Progress Tracking:** Display investigation stages and results through the dashboard.

## Supported Failure Scenarios

The investigation engine is designed to analyze common Kubernetes issues, including:

- CrashLoopBackOff and ImagePullBackOff
- OOMKilled and resource exhaustion
- Pending pods and scheduling failures
- Deployment and rollout failures
- Readiness and liveness probe failures
- Service selector mismatches
- DNS and networking issues
