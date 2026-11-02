import type { ClusterInfo } from "@/types";

export type SidebarSection = "investigation" | "history";

type AppSidebarProps = {
  userEmail: string | null;
  clusters: ClusterInfo[];
  selectedCluster: string | null;
  onSelectCluster: (name: string) => void;
  clustersLoading: boolean;
  clustersRefreshing: boolean;
  clustersError: string | null;
  onRefreshClusters: () => void;
  activeSection: SidebarSection;
  onNavigate: (section: SidebarSection) => void;
  historyCount: number;
  onSignOut: () => void;
  sidebarOpen: boolean;
  onCloseMobile: () => void;
};

const NAV_ITEMS = [
  {
    id: "investigation" as const,
    label: "Investigation",
    icon: <ActivityIcon />,
  },
  {
    id: "history" as const,
    label: "History",
    icon: <HistoryIcon />,
  },
];

export function AppSidebar({
  userEmail,
  clusters,
  selectedCluster,
  onSelectCluster,
  clustersLoading,
  clustersRefreshing,
  clustersError,
  onRefreshClusters,
  activeSection,
  onNavigate,
  historyCount,
  onSignOut,
  sidebarOpen,
  onCloseMobile,
}: AppSidebarProps) {
  return (
    <aside
      className={`fixed inset-y-0 left-0 z-40 flex w-64 flex-col border-r border-slate-800/80 bg-slate-900/95 transition-transform duration-200 lg:translate-x-0 ${
        sidebarOpen ? "translate-x-0" : "-translate-x-full"
      }`}
    >
      <div className="flex h-14 shrink-0 items-center gap-3 border-b border-slate-800/80 px-4">
        <LogoMark />
        <div className="min-w-0 flex-1">
          <p className="truncate text-sm font-semibold tracking-tight text-slate-50">
            NudgeOps
          </p>
          <p className="truncate text-[11px] text-slate-500">
            AI cluster troubleshooting
          </p>
        </div>
        {onCloseMobile && (
          <button
            type="button"
            onClick={onCloseMobile}
            aria-label="Close navigation"
            className="rounded-md p-1.5 text-slate-400 transition-colors hover:bg-slate-800 hover:text-slate-200 lg:hidden"
          >
            <CloseIcon />
          </button>
        )}
      </div>

      <nav className="flex flex-col gap-1 px-3 py-3">
        {NAV_ITEMS.map((item) => {
          const isActive = activeSection === item.id;
          return (
            <button
              key={item.id}
              type="button"
              onClick={() => onNavigate(item.id)}
              className={`flex items-center gap-2.5 rounded-md px-3 py-2 text-sm font-medium transition-colors ${
                isActive
                  ? "bg-slate-800/70 text-slate-100"
                  : "text-slate-400 hover:bg-slate-800/40 hover:text-slate-200"
              }`}
            >
              <span
                className={isActive ? "text-indigo-400" : "text-slate-500"}
              >
                {item.icon}
              </span>
              <span className="flex-1 text-left">{item.label}</span>
              {item.id === "history" && historyCount > 0 && (
                <span className="rounded-full bg-slate-800 px-2 py-0.5 text-[11px] font-medium text-slate-400">
                  {historyCount}
                </span>
              )}
            </button>
          );
        })}
      </nav>

      <div className="flex min-h-0 flex-1 flex-col border-t border-slate-800/80">
        <div className="flex items-center justify-between px-4 pb-2 pt-4">
          <p className="text-[11px] font-semibold uppercase tracking-widest text-slate-500">
            Clusters
          </p>
          <button
            type="button"
            onClick={onRefreshClusters}
            disabled={clustersLoading || clustersRefreshing}
            aria-label="Refresh clusters"
            title="Refresh clusters"
            className="rounded-md p-1 text-slate-400 transition-colors hover:bg-slate-800 hover:text-slate-200 disabled:cursor-not-allowed disabled:opacity-40"
          >
            <RefreshIcon />
          </button>
        </div>

        <div className="min-h-0 flex-1 overflow-y-auto px-3 pb-3">
          {clustersError && (
            <p className="whitespace-pre-line rounded-md border border-red-500/20 bg-red-500/10 px-3 py-2 text-xs text-red-300">
              {clustersError}
            </p>
          )}

          {clustersLoading ? (
            <p className="px-3 py-2 text-xs text-slate-500">
              Loading clusters...
            </p>
          ) : clusters.length === 0 ? (
            <p className="px-3 py-2 text-xs text-slate-500">
              No clusters found in the kubeconfig. Add a context, then refresh.
            </p>
          ) : (
            <div className="flex flex-col gap-1">
              {clusters.map((cluster) => {
                const isSelected = selectedCluster === cluster.name;

                return (
                  <button
                    key={cluster.name}
                    type="button"
                    onClick={() => onSelectCluster(cluster.name)}
                    className={`group flex items-start gap-2.5 rounded-md px-3 py-2 text-left transition-colors ${
                      isSelected
                        ? "bg-indigo-500/10 ring-1 ring-inset ring-indigo-500/40"
                        : "hover:bg-slate-800/40"
                    }`}
                  >
                    <span
                      className={`mt-1 h-2 w-2 shrink-0 rounded-full ${
                        cluster.is_current ? "bg-emerald-400" : "bg-slate-600"
                      } ${
                        isSelected ? "ring-2 ring-indigo-500/30" : ""
                      } transition-colors`}
                    />
                    <span className="min-w-0 flex-1">
                      <span
                        className={`block truncate text-sm ${
                          isSelected
                            ? "font-medium text-indigo-200"
                            : "text-slate-300"
                        }`}
                      >
                        {cluster.name}
                      </span>
                      <span className="mt-0.5 block truncate text-[11px] text-slate-500">
                        {cluster.namespace ?? "default"}
                        {cluster.is_current ? " · current context" : ""}
                      </span>
                    </span>
                  </button>
                );
              })}
            </div>
          )}
        </div>
      </div>

      <div className="shrink-0 border-t border-slate-800/80 p-3">
        <div className="flex items-center gap-2 rounded-md px-2 py-1.5">
          <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-slate-800 text-xs font-semibold text-slate-300">
            {(userEmail?.[0] ?? "?").toUpperCase()}
          </div>
          <div className="min-w-0 flex-1">
            <p className="truncate text-xs font-medium text-slate-300">
              {userEmail ?? "Signed in"}
            </p>
          </div>
          <button
            type="button"
            onClick={onSignOut}
            aria-label="Sign out"
            title="Sign out"
            className="rounded-md p-1.5 text-slate-400 transition-colors hover:bg-slate-800 hover:text-slate-200"
          >
            <SignOutIcon />
          </button>
        </div>
      </div>
    </aside>
  );
}

function LogoMark() {
  return (
    <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg border border-indigo-500/30 bg-indigo-500/10 text-indigo-400">
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
        <path d="M12 2.5 20 7v10l-8 4.5L4 17V7z" />
        <circle cx="12" cy="12" r="3" />
      </svg>
    </span>
  );
}

function ActivityIcon() {
  return (
    <svg
      width="16"
      height="16"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.75"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <path d="M3 12h4l2-6 4 12 2-6h4" />
    </svg>
  );
}

function HistoryIcon() {
  return (
    <svg
      width="16"
      height="16"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.75"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <circle cx="12" cy="12" r="9" />
      <path d="M12 7v5l3 2" />
    </svg>
  );
}

function RefreshIcon() {
  return (
    <svg
      width="14"
      height="14"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.75"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <path d="M21 12a9 9 0 1 1-2.64-6.36" />
      <path d="M21 3v6h-6" />
    </svg>
  );
}

function SignOutIcon() {
  return (
    <svg
      width="14"
      height="14"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.75"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <path d="M15 3h4a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2h-4" />
      <path d="M10 17l-5-5 5-5" />
      <path d="M5 12h11" />
    </svg>
  );
}

function CloseIcon() {
  return (
    <svg
      width="16"
      height="16"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.75"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <path d="M6 6l12 12" />
      <path d="M18 6L6 18" />
    </svg>
  );
}
