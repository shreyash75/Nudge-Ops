export type HealthStatus = {
  status: string;
  service: string;
};

export type AuthUser = {
  id: string;
  email?: string | null;
};

export type AuthResponse = {
  access_token: string;
  user: AuthUser;
};

export type ClusterInfo = {
  name: string;
  cluster: string;
  server?: string | null;
  namespace?: string | null;
  is_current: boolean;
};

export type ClusterListResponse = {
  clusters: ClusterInfo[];
  current_context?: string | null;
  error?: string | null;
};

export type ProblematicPod = {
  name: string;
  namespace: string;
  status: string;
  message?: string | null;
  age_seconds?: number | null;
};

export type InvestigationPayload = {
  pods: {
    healthy: boolean;
    problematic_pods: ProblematicPod[];
    total_pods: number;
    error?: string | null;
  };
  logs: {
    items: Array<{
      name: string;
      namespace: string;
      highlights: string[];
      truncated: boolean;
    }>;
    error?: string | null;
  };
  events: {
    healthy: boolean;
    findings: Array<{
      reason: string;
      count: number;
      namespace: string;
      object: string;
      message: string;
      last_seen?: string | null;
    }>;
    error?: string | null;
  };
  deployments: {
    healthy: boolean;
    unhealthy_deployments: Array<{
      name: string;
      namespace: string;
      replicas: number;
      available_replicas: number;
      unavailable_replicas: number;
      conditions: string[];
      rollout_failed: boolean;
    }>;
    error?: string | null;
  };
  network: {
    healthy: boolean;
    issues: Array<{
      kind: string;
      name: string;
      namespace: string;
      details: string;
    }>;
    error?: string | null;
  };
};

export type Diagnosis = {
  root_cause: string;
  namespace?: string | null;
  explanation: string;
  fix: string;
  kubectl_command?: string | null;
  kubectl_commands: string[];
  prevention: string;
  confidence: number;
  confidence_reasoning: string[];
};

export type InvestigateResponse = {
  investigation_id?: string | null;
  cluster?: string | null;
  cluster_healthy: boolean;
  status: string;
  investigation: InvestigationPayload;
  message?: string | null;
  diagnosis?: Diagnosis | null;
};

export type InvestigationResult = InvestigateResponse;

export type InvestigationHistory = {
  id: string;
  user_id: string;
  cluster?: string | null;
  status: string;
  message?: string | null;
  root_cause?: string | null;
  namespace?: string | null;
  explanation?: string | null;
  confidence?: number | null;
  investigation: InvestigationPayload;
  diagnosis?: Diagnosis | null;
  created_at: string;
  completed_at?: string | null;
};

export type InvestigationProgressEvent = {
  investigation_id: string;
  stage: string;
  status: "running" | "completed" | "error";
  message: string;
  timestamp: string;
};
