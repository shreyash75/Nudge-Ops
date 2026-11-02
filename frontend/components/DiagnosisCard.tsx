import type { Diagnosis } from "@/types";

type DiagnosisCardProps = {
  diagnosis?: Diagnosis | null;
  status: string;
  message?: string | null;
  clusterHealthy?: boolean;
};

type Severity = "healthy" | "critical" | "neutral";

const SEVERITY_META: Record<
  Severity,
  { label: string; dot: string; chip: string; accent: string }
> = {
  healthy: {
    label: "Cluster healthy",
    dot: "bg-emerald-400",
    chip: "border-emerald-500/25 bg-emerald-500/10 text-emerald-300",
    accent: "bg-emerald-400/70",
  },
  critical: {
    label: "Attention required",
    dot: "bg-red-400",
    chip: "border-red-500/25 bg-red-500/10 text-red-300",
    accent: "bg-red-400/70",
  },
  neutral: {
    label: "Status unknown",
    dot: "bg-slate-500",
    chip: "border-slate-700 bg-slate-800/60 text-slate-400",
    accent: "bg-slate-500/70",
  },
};

function ConfidenceMeter({ confidence }: { confidence: number }) {
  return (
    <div className="min-w-[160px] shrink-0">
      <div className="flex items-baseline justify-between gap-2">
        <span className="text-[11px] font-medium uppercase tracking-widest text-slate-500">
          Confidence
        </span>
        <span className="text-xs font-semibold text-slate-200">
          {confidence}%
        </span>
      </div>
      <div className="mt-1.5 h-1 w-full overflow-hidden rounded-full bg-slate-800">
        <div
          className="h-full rounded-full bg-indigo-400"
          style={{ width: `${Math.min(100, Math.max(0, confidence))}%` }}
        />
      </div>
    </div>
  );
}

function SeverityBadge({ severity }: { severity: Severity }) {
  const meta = SEVERITY_META[severity];
  return (
    <span
      className={`inline-flex items-center gap-2 rounded-full border px-3 py-1 text-xs font-medium ${meta.chip}`}
    >
      <span className={`h-1.5 w-1.5 rounded-full ${meta.dot}`} />
      {meta.label}
    </span>
  );
}

export function DiagnosisCard({
  diagnosis,
  status,
  message,
  clusterHealthy = false,
}: DiagnosisCardProps) {
  const isError = status === "error";

  if (!diagnosis && clusterHealthy && !isError) {
    return (
      <section className="overflow-hidden rounded-xl border border-slate-800 bg-slate-900/60">
        <div
          className="h-0.5 w-full bg-emerald-400/70"
          aria-hidden="true"
        />
        <div className="p-6">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <p className="text-xs font-medium uppercase tracking-widest text-indigo-400">
                AI diagnosis
              </p>
              <h2 className="mt-1.5 text-xl font-semibold text-slate-100">
                Cluster appears healthy
              </h2>
            </div>
            <SeverityBadge severity="healthy" />
          </div>
          <p className="mt-3 whitespace-pre-line text-sm leading-6 text-slate-400">
            {message ??
              "No critical Kubernetes issues were detected in this cluster."}
          </p>
        </div>
      </section>
    );
  }

  if (!diagnosis) {
    return (
      <section className="overflow-hidden rounded-xl border border-slate-800 bg-slate-900/60">
        <div
          className={`h-0.5 w-full ${isError ? "bg-red-400/70" : "bg-slate-700"}`}
          aria-hidden="true"
        />
        <div className="p-6">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <h2
              className={`text-xl font-semibold ${
                isError ? "text-red-300" : "text-slate-100"
              }`}
            >
              {isError ? "Investigation failed" : "AI diagnosis unavailable"}
            </h2>
            {isError && <SeverityBadge severity="critical" />}
          </div>
          <p className="mt-3 text-sm text-slate-400">
            {isError
              ? "The investigation could not be completed."
              : "The investigation did not produce an AI diagnosis."}
          </p>
          {message && (
            <p
              className={`mt-2 whitespace-pre-line rounded-md px-3 py-2 text-sm leading-6 ${
                isError
                  ? "border border-red-500/20 bg-red-500/10 text-red-300"
                  : "border border-slate-800 bg-slate-950/60 text-slate-500"
              }`}
            >
              {message}
            </p>
          )}
        </div>
      </section>
    );
  }

  const severity: Severity = clusterHealthy ? "healthy" : "critical";

  const commands =
    diagnosis.kubectl_commands.length > 0
      ? diagnosis.kubectl_commands
      : diagnosis.kubectl_command
        ? [diagnosis.kubectl_command]
        : [];

  return (
    <section className="overflow-hidden rounded-xl border border-slate-800 bg-slate-900/60">
      <div
        className={`h-0.5 w-full ${SEVERITY_META[severity].accent}`}
        aria-hidden="true"
      />
      <div className="p-6">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div className="min-w-0">
            <p className="text-xs font-medium uppercase tracking-widest text-indigo-400">
              AI diagnosis
            </p>
            <h2 className="mt-1.5 text-2xl font-semibold leading-snug tracking-tight text-slate-50">
              {diagnosis.root_cause}
            </h2>
          </div>
          <ConfidenceMeter confidence={diagnosis.confidence} />
        </div>

        <div className="mt-4 flex flex-wrap items-center gap-2">
          <SeverityBadge severity={severity} />
          {diagnosis.namespace && (
            <span className="rounded-full border border-slate-800 bg-slate-950/60 px-3 py-1 text-xs font-medium text-slate-400">
              Namespace: {diagnosis.namespace}
            </span>
          )}
          {status !== "success" && (
            <span className="rounded-full border border-slate-800 bg-slate-950/60 px-3 py-1 text-xs font-medium text-slate-400">
              Status: {status}
            </span>
          )}
        </div>

        <p className="mt-5 whitespace-pre-wrap text-sm leading-6 text-slate-300">
          {diagnosis.explanation}
        </p>

        <div className="mt-6 border-t border-slate-800/80 pt-5">
          <h3 className="text-sm font-semibold text-slate-100">
            Recommended fix
          </h3>
          <p className="mt-2 whitespace-pre-wrap text-sm leading-6 text-slate-400">
            {diagnosis.fix}
          </p>
        </div>

        {commands.length > 0 && (
          <div className="mt-6 border-t border-slate-800/80 pt-5">
            <h3 className="text-sm font-semibold text-slate-100">
              kubectl commands
            </h3>
            <pre className="mt-2 overflow-auto rounded-lg border border-slate-800 bg-slate-950 p-4 font-mono text-xs leading-5 text-slate-300">
              {commands.join("\n")}
            </pre>
          </div>
        )}

        {diagnosis.prevention && (
          <div className="mt-6 border-t border-slate-800/80 pt-5">
            <h3 className="text-sm font-semibold text-slate-100">Prevention</h3>
            <p className="mt-2 whitespace-pre-wrap text-sm leading-6 text-slate-400">
              {diagnosis.prevention}
            </p>
          </div>
        )}

        {diagnosis.confidence_reasoning.length > 0 && (
          <div className="mt-6 border-t border-slate-800/80 pt-5">
            <h3 className="text-sm font-semibold text-slate-100">
              Confidence reasoning
            </h3>
            <ul className="mt-2.5 space-y-2 text-sm text-slate-500">
              {diagnosis.confidence_reasoning.map((reason) => (
                <li
                  key={reason}
                  className="flex gap-2.5 text-slate-400"
                >
                  <span
                    className="mt-[7px] h-1 w-1 shrink-0 rounded-full bg-indigo-400/70"
                    aria-hidden="true"
                  />
                  {reason}
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>
    </section>
  );
}
