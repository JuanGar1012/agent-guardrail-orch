type StatusPillProps = {
  label: string;
  tone?: "ok" | "warn" | "neutral";
};

export function StatusPill({ label, tone = "neutral" }: StatusPillProps): JSX.Element {
  const palette =
    tone === "ok"
      ? "border-emerald-300/70 bg-emerald-100/70 text-emerald-900 dark:border-emerald-500/40 dark:bg-emerald-900/40 dark:text-emerald-100"
      : tone === "warn"
        ? "border-amber-300/70 bg-amber-100/70 text-amber-900 dark:border-amber-500/40 dark:bg-amber-900/40 dark:text-amber-100"
        : "border-bluecore-300/70 bg-bluecore-100/70 text-bluecore-900 dark:border-bluecore-500/40 dark:bg-bluecore-900/50 dark:text-bluecore-100";
  return (
    <span className={`rounded-full border px-2 py-0.5 text-xs font-semibold ${palette}`}>{label}</span>
  );
}
