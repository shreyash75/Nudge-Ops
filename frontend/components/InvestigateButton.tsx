type InvestigateButtonProps = {
  onClick: () => void;
  isPending: boolean;
  disabled?: boolean;
};

export function InvestigateButton({
  onClick,
  isPending,
  disabled = false,
}: InvestigateButtonProps) {
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={isPending || disabled}
      className="inline-flex shrink-0 items-center gap-2 rounded-md bg-indigo-500 px-4 py-2.5 text-sm font-medium text-white transition-colors hover:bg-indigo-400 disabled:cursor-not-allowed disabled:bg-slate-800 disabled:text-slate-500"
    >
      <svg
        width="15"
        height="15"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.75"
        strokeLinecap="round"
        strokeLinejoin="round"
        aria-hidden="true"
        className={isPending ? "animate-pulse" : undefined}
      >
        <path d="M3 12h4l2-6 4 12 2-6h4" />
      </svg>
      {isPending ? "Investigating..." : "Investigate"}
    </button>
  );
}
