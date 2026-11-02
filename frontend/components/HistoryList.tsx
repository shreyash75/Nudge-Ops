import type { InvestigationHistory } from "@/types";

type HistoryListProps = {
  items: InvestigationHistory[];
  isLoading: boolean;
  error: Error | null;
  selectedId: string | null;
  onSelect: (item: InvestigationHistory) => void;
};

export function HistoryList({
  items,
  isLoading,
  error,
  selectedId,
  onSelect,
}: HistoryListProps) {
  return (
    <section className="overflow-hidden rounded-xl border border-slate-800 bg-slate-900/60">
      <header className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-800/80 px-5 py-3.5">
        <div>
          <h2 className="text-sm font-semibold text-slate-100">
            Saved investigations
          </h2>
          <p className="mt-0.5 text-[11px] text-slate-500">
            Select an entry to reopen its diagnosis in the workspace.
          </p>
        </div>
        {items.length > 0 && (
          <span className="rounded-full border border-slate-800 bg-slate-950/60 px-2.5 py-0.5 text-[11px] font-medium text-slate-400">
            {items.length} entr{items.length === 1 ? "y" : "ies"}
          </span>
        )}
      </header>

      {isLoading && (
        <p className="px-5 py-6 text-sm text-slate-500">Loading history...</p>
      )}

      {error && (
        <p className="px-5 py-6 text-sm text-red-400" title={error.message}>
          Unable to load history. Please refresh and try again.
        </p>
      )}

      {!isLoading && !error && items.length === 0 && (
        <div className="px-5 py-8 text-center">
          <p className="text-sm text-slate-400">No investigations saved yet</p>
          <p className="mt-1 text-xs text-slate-500">
            Completed investigations of your account are listed here.
          </p>
        </div>
      )}

      {items.length > 0 && (
        <ul className="divide-y divide-slate-800/80">
          {items.map((item) => {
            const rootCause =
              item.root_cause ??
              item.diagnosis?.root_cause ??
              "No diagnosis available";
            const namespace =
              item.namespace ?? item.diagnosis?.namespace ?? null;
            const confidence =
              item.confidence ?? item.diagnosis?.confidence ?? null;
            const cluster = item.cluster ?? "unknown cluster";
            const isHealthy = item.status !== "error";
            const isSelected = selectedId === item.id;

            return (
              <li key={item.id}>
                <button
                  type="button"
                  onClick={() => onSelect(item)}
                  className={`flex w-full items-start gap-3.5 px-5 py-3.5 text-left transition-colors ${
                    isSelected
                      ? "bg-indigo-500/10"
                      : "hover:bg-slate-800/40"
                  }`}
                >
                  <span
                    className={`mt-1.5 h-2 w-2 shrink-0 rounded-full ${
                      isHealthy ? "bg-emerald-400" : "bg-red-400"
                    }`}
                    aria-hidden="true"
                  />

                  <div className="min-w-0 flex-1">
                    <p className="truncate text-sm font-medium text-slate-200">
                      {rootCause}
                    </p>
                    <p className="mt-0.5 truncate text-xs text-slate-500">
                      {cluster}
                      {namespace ? ` · ${namespace}` : ""}
                    </p>
                  </div>

                  <div className="shrink-0 text-right">
                    <p className="whitespace-nowrap text-xs text-slate-400">
                      {new Date(item.created_at).toLocaleString()}
                    </p>
                    <p
                      className={`mt-1 inline-flex items-center gap-1.5 rounded-full border px-2 py-0.5 text-[11px] font-medium ${
                        isHealthy
                          ? "border-emerald-500/25 bg-emerald-500/10 text-emerald-300"
                          : "border-red-500/25 bg-red-500/10 text-red-300"
                      }`}
                    >
                      {item.status}
                      {typeof confidence === "number" &&
                        ` · ${confidence}% conf`}
                    </p>
                  </div>
                </button>
              </li>
            );
          })}
        </ul>
      )}
    </section>
  );
}
