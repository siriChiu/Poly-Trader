import { useMemo } from "react";
import { useGlobalProgressSnapshot } from "../hooks/useGlobalProgress";

const TONE_STYLES = {
  blue: {
    wrap: "border-blue-800/40 bg-slate-950/95",
    text: "text-blue-200",
    detail: "text-blue-100/70",
    bar: "from-blue-400 via-sky-300 to-blue-500",
  },
  cyan: {
    wrap: "border-cyan-800/40 bg-slate-950/95",
    text: "text-cyan-200",
    detail: "text-cyan-100/70",
    bar: "from-cyan-400 via-sky-300 to-cyan-500",
  },
  emerald: {
    wrap: "border-emerald-800/40 bg-slate-950/95",
    text: "text-emerald-200",
    detail: "text-emerald-100/70",
    bar: "from-emerald-400 via-teal-300 to-emerald-500",
  },
  violet: {
    wrap: "border-violet-800/40 bg-slate-950/95",
    text: "text-violet-200",
    detail: "text-violet-100/70",
    bar: "from-violet-400 via-fuchsia-300 to-violet-500",
  },
} as const;

export default function GlobalTopProgress() {
  const snapshot = useGlobalProgressSnapshot();

  const width = useMemo(() => {
    if (typeof snapshot.progress === "number" && Number.isFinite(snapshot.progress)) {
      return Math.max(2, Math.min(100, snapshot.progress));
    }
    return 38;
  }, [snapshot.progress]);

  if (!snapshot.active) return null;

  const palette = TONE_STYLES[snapshot.tone] ?? TONE_STYLES.blue;
  const statusText = typeof snapshot.progress === "number" && Number.isFinite(snapshot.progress)
    ? `${Math.round(snapshot.progress)}%`
    : "處理中";

  return (
    <div className={`border-b ${palette.wrap}`}>
      <div className="w-full px-4 sm:px-6 lg:px-8 py-2">
        <div className="flex items-center justify-between gap-4 text-xs">
          <div className="min-w-0">
            <div className={`truncate font-medium ${palette.text}`}>{snapshot.label}</div>
            {snapshot.detail ? <div className={`truncate ${palette.detail}`}>{snapshot.detail}</div> : null}
          </div>
          <div className="shrink-0 text-slate-400">{statusText}</div>
        </div>
        <div className="mt-2 h-1.5 overflow-hidden rounded-full bg-slate-800/90">
          <div
            className={`h-full rounded-full bg-gradient-to-r transition-[width] duration-300 ease-out ${palette.bar}`}
            style={{ width: `${width}%` }}
          />
        </div>
      </div>
    </div>
  );
}
