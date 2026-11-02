import axios from "axios";

import type {
  AuthResponse,
  AuthUser,
  ClusterListResponse,
  HealthStatus,
  InvestigateResponse,
  InvestigationHistory,
} from "@/types";

const api = axios.create({
  baseURL: process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000",
  headers: {
    "Content-Type": "application/json",
  },
  timeout: 300000,
});

export async function getHealth(): Promise<HealthStatus> {
  const response = await api.get<HealthStatus>("/health");
  return response.data;
}

export async function getClusters(
  accessToken: string,
): Promise<ClusterListResponse> {
  const response = await api.get<ClusterListResponse>("/clusters", {
    headers: { Authorization: `Bearer ${accessToken}` },
    timeout: 20000,
  });
  return response.data;
}

export async function registerUser({
  email,
  password,
}: {
  email: string;
  password: string;
}): Promise<AuthResponse> {
  try {
    const response = await api.post<AuthResponse>("/auth/register", {
      email,
      password,
    });
    return response.data;
  } catch (error) {
    throw new Error(getFriendlyApiError(error));
  }
}

export async function loginUser({
  email,
  password,
}: {
  email: string;
  password: string;
}): Promise<AuthResponse> {
  try {
    const response = await api.post<AuthResponse>("/auth/login", {
      email,
      password,
    });
    return response.data;
  } catch (error) {
    throw new Error(getFriendlyApiError(error));
  }
}

export async function getCurrentUser(
  accessToken: string,
): Promise<AuthUser> {
  const response = await api.get<AuthUser>("/auth/me", {
    headers: { Authorization: `Bearer ${accessToken}` },
  });
  return response.data;
}

export async function getInvestigationHistory(
  accessToken: string,
): Promise<InvestigationHistory[]> {
  const response = await api.get<InvestigationHistory[]>(
    "/investigate/history",
    {
      headers: { Authorization: `Bearer ${accessToken}` },
      timeout: 20000,
    },
  );
  return response.data;
}

type InvestigateClusterInput = {
  investigationId: string;
  accessToken: string;
  cluster: string;
};

export async function investigateCluster({
  investigationId,
  accessToken,
  cluster,
}: InvestigateClusterInput): Promise<InvestigateResponse> {
  const response = await api.post<InvestigateResponse>(
    "/investigate",
    { investigation_id: investigationId, cluster },
    { headers: { Authorization: `Bearer ${accessToken}` } },
  );
  return response.data;
}

export function getFriendlyApiError(error: unknown): string {
  if (!axios.isAxiosError(error)) {
    return error instanceof Error
      ? error.message
      : "Something went wrong. Please try again.";
  }

  if (error.code === "ECONNABORTED") {
    return "The request timed out. The cluster may be slow or unreachable. Please try again.";
  }

  if (!error.response) {
    return "Unable to reach the backend service. Verify that it is running and try again.";
  }

  const status = error.response.status;
  const data = error.response.data as
    | { detail?: unknown; message?: unknown }
    | undefined;
  const serverMessage =
    typeof data?.detail === "string"
      ? data.detail
      : typeof data?.message === "string"
        ? data.message
        : null;

  if (status === 401 || status === 403) {
    return serverMessage ?? "Your session has expired. Please sign in again.";
  }

  if (status === 503) {
    return "The backend service is temporarily unavailable. Please try again in a moment.";
  }

  if (serverMessage) {
    return serverMessage;
  }

  return "Something went wrong while contacting the backend. Please try again.";
}
