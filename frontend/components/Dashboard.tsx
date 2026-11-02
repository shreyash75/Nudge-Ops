"use client";

import { useEffect, useRef, useState } from "react";

import { useAuth } from "@/components/AuthProvider";
import { AppSidebar, type SidebarSection } from "@/components/AppSidebar";
import { DiagnosisCard } from "@/components/DiagnosisCard";
import { HistoryList } from "@/components/HistoryList";
import { InvestigateButton } from "@/components/InvestigateButton";
import { ProgressTimeline } from "@/components/ProgressTimeline";
import { useClusters } from "@/hooks/useClusters";
import { useInvestigate } from "@/hooks/useInvestigate";
import { useInvestigationHistory } from "@/hooks/useInvestigationHistory";
import { getStoredToken } from "@/lib/token";
import { getFriendlyApiError } from "@/services/api";
import { subscribeToInvestigationProgress } from "@/services/sse";
import type {
  InvestigateResponse,
  InvestigationHistory,
  InvestigationProgressEvent,
} from "@/types";

function MenuIcon() {
  return (
    <svg
      width="18"
      height="18"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.75"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <path d="M4 6h16M4 12h16M4 18h16" />
    </svg>
  );
}

function isHealthyResult(
  result: InvestigateResponse | InvestigationHistory,
): boolean {
  if ("cluster_healthy" in result) {
    return result.cluster_healthy;
  }

  return result.root_cause === "No critical Kubernetes issues detected";
}

export function Dashboard() {
  const { user, signOut } = useAuth();
  const investigation = useInvestigate();
  const history = useInvestigationHistory(user?.id);
  const clustersQuery = useClusters(user?.id);
  const clusters = clustersQuery.data?.clusters ?? [];
  const [selectedCluster, setSelectedCluster] = useState<string | null>(null);
  const [progressEvents, setProgressEvents] = useState<
    InvestigationProgressEvent[]
  >([]);
  const [realtimeWarning, setRealtimeWarning] = useState<string | null>(null);
  const [clientError, setClientError] = useState<string | null>(null);
  const [selectedHistory, setSelectedHistory] =
    useState<InvestigationHistory | null>(null);
  const [activeSection, setActiveSection] = useState<SidebarSection>("investigation");
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const unsubscribeRef = useRef<(() => void) | null>(null);

  useEffect(() => {
    if (clusters.length === 0) {
      if (selectedCluster !== null) {
        setSelectedCluster(null);
      }
      return;
    }

    if (
      selectedCluster &&
      clusters.some((cluster) => cluster.name === selectedCluster)
    ) {
      return;
    }

    const preferred =
      clusters.find((cluster) => cluster.is_current) ?? clusters[0];
    setSelectedCluster(preferred.name);
  }, [clusters, selectedCluster]);

  useEffect(() => {
    return () => {
      unsubscribeRef.current?.();
    };
  }, []);

  function selectCluster(name: string) {
    setSelectedCluster(name);
    setSelectedHistory(null);
    setProgressEvents([]);
    setRealtimeWarning(null);
    setClientError(null);
    investigation.reset();
    unsubscribeRef.current?.();
    unsubscribeRef.current = null;
  }

  async function runInvestigation() {
    if (!selectedCluster) {
      setClientError("Select a cluster first.");
      return;
    }

    setSelectedHistory(null);
    setProgressEvents([]);
    setRealtimeWarning(null);
    setClientError(null);
    setActiveSection("investigation");

    const investigationId = crypto.randomUUID();
    const accessToken = getStoredToken();
    if (!accessToken) {
      setClientError("Your session has expired. Please sign in again.");
      return;
    }

    unsubscribeRef.current?.();
    unsubscribeRef.current = null;

    try {
      unsubscribeRef.current = await subscribeToInvestigationProgress(
        investigationId,
        accessToken,
        (event) => {
          setProgressEvents((current) => [...current, event]);
        },
      );
    } catch (error) {
      setRealtimeWarning(
        error instanceof Error
          ? `Live progress unavailable: ${error.message}`
          : "Live progress unavailable",
      );
    }

    investigation.mutate({
      investigationId,
      accessToken,
      cluster: selectedCluster,
    });
  }

  const displayedResult = selectedHistory ?? investigation.data ?? null;
  const displayedMessage =
    investigation.isError && !selectedHistory
      ? getFriendlyApiError(investigation.error)
      : clientError;
  const clustersError = clustersQuery.error
    ? getFriendlyApiError(clustersQuery.error)
    : (clustersQuery.data?.error ?? null);
  const clusterHealthy = displayedResult
    ? isHealthyResult(displayedResult)
    : false;
  const historyItems = history.data ?? [];
  const selectedClusterInfo = clusters.find(
    (cluster) => cluster.name === selectedCluster,
  );

  return (
    <div className="min-h-screen">
      {sidebarOpen && (
        <button
          type="button"
          aria-label="Close navigation"
          onClick={() => setSidebarOpen(false)}
          className="fixed inset-0 z-30 bg-black/60 lg:hidden"
        />
      )}

      <AppSidebar
        userEmail={user?.email ?? null}
        clusters={clusters}
        selectedCluster={selectedCluster}
        onSelectCluster={(name) => {
          selectCluster(name);
          setSidebarOpen(false);
        }}
        clustersLoading={clustersQuery.isLoading}
        clustersRefreshing={clustersQuery.isFetching && !clustersQuery.isLoading}
        clustersError={clustersError}
        onRefreshClusters={() => {
          void clustersQuery.refetch();
        }}
        activeSection={activeSection}
        onNavigate={setActiveSection}
        historyCount={historyItems.length}
        onSignOut={() => {
          void signOut().catch((error: unknown) => {
            setClientError(
              error instanceof Error ? error.message : "Sign out failed",
            );
          });
          setSidebarOpen(false);
        }}
        sidebarOpen={sidebarOpen}
        onCloseMobile={() => setSidebarOpen(false)}
      />

      <div className="flex min-h-screen flex-col lg:pl-64">
        <header className="sticky top-0 z-20 flex h-14 shrink-0 items-center justify-between gap-4 border-b border-slate-800/80 bg-slate-950/95 px-4 sm:px-6">
          <div className="flex min-w-0 items-center gap-3">
            <button
              type="button"
              onClick={() => setSidebarOpen(true)}
              aria-label="Open navigation"
              className="rounded-md border border-slate-700 p-1.5 text-slate-300 transition-colors hover:bg-slate-800 lg:hidden"
            >
              <MenuIcon />
            </button>
            <div className="min-w-0">
              <h1 className="truncate text-sm font-semibold text-slate-100">
                {activeSection === "investigation"
                  ? "Cluster Investigation"
                  : "Investigation History"}
              </h1>
              <p className="truncate text-[11px] text-slate-500">
                {activeSection === "investigation" && selectedCluster
                  ? `Target: ${selectedCluster}`
                  : `${historyItems.length} saved investigation${
                      historyItems.length === 1 ? "" : "s"
                    }`}
              </p>
            </div>
          </div>

          {activeSection === "investigation"
            ? selectedClusterInfo && (
                <span className="hidden items-center gap-2 rounded-full border border-slate-800 bg-slate-900 px-3 py-1 text-xs text-slate-400 sm:flex">
                  <span
                    className={`h-1.5 w-1.5 rounded-full ${
                      selectedClusterInfo.is_current
                        ? "bg-emerald-400"
                        : "bg-slate-600"
                    }`}
                  />
                  <span className="max-w-[220px] truncate">
                    {selectedClusterInfo.name}
                  </span>
                </span>
              )
            : null}
        </header>

        <main className="flex-1 px-4 py-5 sm:px-6 sm:py-6">
          <div className="mx-auto w-full max-w-6xl">
            {activeSection === "investigation" ? (
              <>
                <div className="mb-5 flex items-end justify-between gap-4">
                  <div>
                    <p className="text-xs font-medium uppercase tracking-widest text-indigo-400">
                      Live workspace
                    </p>
                    <p className="mt-1 text-sm text-slate-500">
                      {selectedCluster ? (
                        <>
                          Evidence collection and AI diagnosis for{" "}
                          <span className="break-all font-medium text-slate-300">
                            {selectedCluster}
                          </span>
                        </>
                      ) : (
                        "Select a cluster in the sidebar to begin."
                      )}
                    </p>
                  </div>
                  <InvestigateButton
                    onClick={() => {
                      void runInvestigation();
                    }}
                    isPending={investigation.isPending}
                    disabled={!selectedCluster}
                  />
                </div>

                {realtimeWarning && (
                  <p className="mb-5 rounded-md border border-amber-500/20 bg-amber-500/10 px-4 py-3 text-sm text-amber-300">
                    {realtimeWarning}
                  </p>
                )}

                {displayedMessage && (
                  <p className="mb-5 rounded-md border border-red-500/20 bg-red-500/10 px-4 py-3 text-sm text-red-300">
                    {displayedMessage}
                  </p>
                )}

                <div className="grid items-start gap-5 xl:grid-cols-[1.4fr_1fr]">
                  <div className="space-y-5">
                    {displayedResult ? (
                      <DiagnosisCard
                        status={displayedResult.status}
                        message={displayedResult.message}
                        diagnosis={displayedResult.diagnosis}
                        clusterHealthy={clusterHealthy}
                      />
                    ) : (
                      <EmptyWorkspaceCard />
                    )}
                  </div>

                  <ProgressTimeline
                    events={progressEvents}
                    isRunning={investigation.isPending}
                  />
                </div>
              </>
            ) : (
              <HistoryList
                items={historyItems}
                isLoading={history.isLoading}
                error={history.error}
                selectedId={selectedHistory?.id ?? null}
                onSelect={(item) => {
                  setSelectedHistory(item);
                  setActiveSection("investigation");
                }}
              />
            )}
          </div>
        </main>
      </div>
    </div>
  );
}

function EmptyWorkspaceCard() {
  return (
    <section className="rounded-xl border border-dashed border-slate-800 bg-slate-900/30 p-8">
      <p className="text-xs font-medium uppercase tracking-widest text-slate-600">
        AI diagnosis
      </p>
      <h2 className="mt-2 text-xl font-semibold text-slate-300">
        No active investigation
      </h2>
      <p className="mt-2 max-w-md text-sm leading-6 text-slate-500">
        Choose a cluster connection, start an investigation, and the AI
        diagnosis will appear here with severity, confidence, kubectl commands
        and prevention guidance.
      </p>
      <div className="mt-5 grid gap-2 text-sm text-slate-500 sm:grid-cols-3">
        <span className="rounded-md border border-slate-800 bg-slate-900/60 px-3 py-2">
          1 · Collect evidence
        </span>
        <span className="rounded-md border border-slate-800 bg-slate-900/60 px-3 py-2">
          2 · Live progress
        </span>
        <span className="rounded-md border border-slate-800 bg-slate-900/60 px-3 py-2">
          3 · AI diagnosis
        </span>
      </div>
    </section>
  );
}
