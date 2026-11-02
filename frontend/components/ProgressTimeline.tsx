import type { InvestigationProgressEvent } from "@/types";

type ProgressTimelineProps = {
  events: InvestigationProgressEvent[];
  isRunning: boolean;
};

const STEPS = [
  { stage: "pods", label: "Checking pods" },
  { stage: "logs", label: "Reading logs" },
  { stage: "events", label: "Analyzing events" },
  { stage: "deployments", label: "Inspecting deployments" },
  { stage: "network", label: "Checking networking" },
  { stage: "diagnosis", label: "AI reasoning" },
] as const;

type StepStatus = "pending" | "running" | "completed" | "error";

function getDotClasses(status: StepStatus) {
  if (status === "completed") {
    return "border-emerald-500/40 bg-emerald-500/15 text-emerald-300";
  }
  if (status === "error") {
    return "border-red-500/40 bg-red-500/15 text-red-300";
  }
  if (status === "running") {
    return "border-amber-500/50 bg-amber-500/15 text-amber-300";
  }
  return "border-slate-700 bg-slate-950 text-slate-600";
}

function getStepIcon(status: StepStatus) {
  if (status === "completed") {
    return "✓";
  }
  if (status === "error") {
    return "!";
  }
  if (status === "running") {
    return "…";
  }
  return null;
}

function getStatusLabel(status: StepStatus) {
  if (status === "completed") {
    return "Done";
  }
  if (status === "error") {
    return "Failed";
  }
  if (status === "running") {
    return "Running";
  }
  return "Pending";
}

export function ProgressTimeline({
  events,
  isRunning,
}: ProgressTimelineProps) {
  const latestByStage = new Map<string, InvestigationProgressEvent>();
  for (const event of events) {
    latestByStage.set(event.stage, event);
  }
  const completedEvent = latestByStage.get("completed");
  const doneCount = events.filter(
    (event) => event.status === "completed" || event.status === "error",
  ).length;

  return (
    <section className="overflow-hidden rounded-xl border border-slate-800 bg-slate-900/60">
      <header className="flex items-center justify-between gap-3 border-b border-slate-800/80 px-5 py-3.5">
        <div className="flex items-center gap-2.5">
          <h2 className="text-sm font-semibold text-slate-100">
            Live progress
          </h2>
          {doneCount > 0 && (
            <span className="text-[11px] text-slate-500">
              {doneCount} step{doneCount === 1 ? "" : "s"} done
            </span>
          )}
        </div>
        {isRunning && (
          <span className="inline-flex items-center gap-2 rounded-full border border-amber-500/25 bg-amber-500/10 px-2.5 py-0.5 text-[11px] font-medium text-amber-300">
            <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-amber-400" />
            Live
          </span>
        )}
      </header>

      <div className="px-5 py-4">
        {events.length === 0 && !isRunning ? (
          <div className="py-2">
            <p className="text-sm text-slate-400">
              No investigation in progress
            </p>
            <p className="mt-1 text-xs leading-5 text-slate-500">
              Start an investigation to watch each evidence step complete in
              real time.
            </p>
          </div>
        ) : (
          <ol className="relative space-y-0.5" aria-live="polite">
            <div
              className="absolute bottom-4 left-[11px] top-4 w-px bg-slate-800"
              aria-hidden="true"
            />
            {STEPS.map((step) => {
              const event = latestByStage.get(step.stage);
              const status: StepStatus = event?.status ?? "pending";
              const icon = getStepIcon(status);

              return (
                <li key={step.stage} className="relative flex gap-3 py-1.5">
                  <span
                    className={`z-10 mt-0.5 flex h-[18px] w-[18px] shrink-0 items-center justify-center rounded-full border text-[10px] font-semibold ${getDotClasses(
                      status,
                    )}`}
                  >
                    {icon}
                  </span>
                  <div className="min-w-0 flex-1">
                    <div className="flex items-baseline justify-between gap-2">
                      <p
                        className={`text-sm ${
                          status === "pending"
                            ? "text-slate-500"
                            : "font-medium text-slate-200"
                        }`}
                      >
                        {step.label}
                      </p>
                      <span className="whitespace-nowrap text-[11px] uppercase tracking-wide text-slate-500">
                        {getStatusLabel(status)}
                      </span>
                    </div>
                    <p className="mt-0.5 truncate text-xs text-slate-500">
                      {event?.message ?? "Waiting"}
                    </p>
                  </div>
                </li>
              );
            })}
          </ol>
        )}

        {completedEvent && (
          <div
            className={`mt-4 whitespace-pre-line rounded-md border px-3.5 py-2.5 text-sm leading-6 ${
              completedEvent.status === "error"
                ? "border-red-500/20 bg-red-500/10 text-red-300"
                : "border-emerald-500/20 bg-emerald-500/10 text-emerald-300"
            }`}
          >
            {completedEvent.message}
          </div>
        )}

        {events.length === 0 && isRunning && (
          <p className="mt-3 text-xs text-slate-500">
            Waiting for progress updates...
          </p>
        )}
      </div>
    </section>
  );
}
