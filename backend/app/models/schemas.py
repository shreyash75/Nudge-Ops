from uuid import UUID

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: str
    service: str


class CurrentUser(BaseModel):
    id: str
    email: str | None = None


class AuthRequest(BaseModel):
    email: str
    password: str


class AuthResponse(BaseModel):
    access_token: str
    user: CurrentUser


class KubectlResult(BaseModel):
    success: bool
    command: list[str]
    stdout: str = ""
    stderr: str = ""
    exit_code: int = 0
    error: str | None = None


class ProblematicPod(BaseModel):
    name: str
    namespace: str
    status: str
    message: str | None = None
    age_seconds: int | None = None


class PodsInvestigation(BaseModel):
    healthy: bool
    problematic_pods: list[ProblematicPod] = Field(default_factory=list)
    total_pods: int = 0
    error: str | None = None


class PodLogs(BaseModel):
    name: str
    namespace: str
    highlights: list[str] = Field(default_factory=list)
    truncated: bool = False


class LogsInvestigation(BaseModel):
    items: list[PodLogs] = Field(default_factory=list)
    error: str | None = None


class EventFinding(BaseModel):
    reason: str
    count: int
    namespace: str
    object: str
    message: str
    last_seen: str | None = None


class EventsInvestigation(BaseModel):
    healthy: bool
    findings: list[EventFinding] = Field(default_factory=list)
    error: str | None = None


class UnhealthyDeployment(BaseModel):
    name: str
    namespace: str
    replicas: int
    available_replicas: int
    unavailable_replicas: int
    conditions: list[str] = Field(default_factory=list)
    rollout_failed: bool = False


class DeploymentsInvestigation(BaseModel):
    healthy: bool
    unhealthy_deployments: list[UnhealthyDeployment] = Field(default_factory=list)
    error: str | None = None


class NetworkIssue(BaseModel):
    kind: str
    name: str
    namespace: str
    details: str


class NetworkInvestigation(BaseModel):
    healthy: bool
    issues: list[NetworkIssue] = Field(default_factory=list)
    error: str | None = None


class InvestigationPayload(BaseModel):
    pods: PodsInvestigation
    logs: LogsInvestigation
    events: EventsInvestigation
    deployments: DeploymentsInvestigation
    network: NetworkInvestigation


class Diagnosis(BaseModel):
    root_cause: str
    namespace: str | None = None
    explanation: str
    fix: str
    kubectl_command: str | None = None
    kubectl_commands: list[str] = Field(default_factory=list)
    prevention: str = ""
    confidence: int = Field(default=0, ge=0, le=100)
    confidence_reasoning: list[str] = Field(default_factory=list)


class ClusterInfo(BaseModel):
    name: str
    cluster: str
    server: str | None = None
    namespace: str | None = None
    is_current: bool = False


class ClusterListResponse(BaseModel):
    clusters: list[ClusterInfo] = Field(default_factory=list)
    current_context: str | None = None
    error: str | None = None


class InvestigateRequest(BaseModel):
    investigation_id: UUID | None = None
    cluster: str | None = None


class InvestigateResponse(BaseModel):
    investigation_id: str | None = None
    cluster: str | None = None
    cluster_healthy: bool = False
    status: str
    investigation: InvestigationPayload
    message: str | None = None
    diagnosis: Diagnosis | None = None
