import { Moon, Sun } from "lucide-react";

type Theme = "light" | "dark";

type ThemeToggleProps = {
  theme: Theme;
  onToggle: () => void;
};

export function ThemeToggle({ theme, onToggle }: ThemeToggleProps): JSX.Element {
  const isDark = theme === "dark";
  return (
    <button
      type="button"
      onClick={onToggle}
      className="inline-flex items-center gap-2 rounded-full border border-bluecore-200/80 bg-white/85 px-3 py-1.5 text-xs font-semibold tracking-wide text-bluecore-900 shadow-blue-glow transition hover:bg-white dark:border-bluecore-700/70 dark:bg-bluecore-900/70 dark:text-bluecore-100 dark:hover:bg-bluecore-900"
      aria-label="Toggle dark mode"
    >
      {isDark ? <Sun size={14} /> : <Moon size={14} />}
      {isDark ? "Light" : "Dark"}
    </button>
  );
}
