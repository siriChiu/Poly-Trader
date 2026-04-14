import { useEffect, useMemo, useState } from "react";

interface ProgressBarProps {
  active: boolean;
  label: string;
  detail?: string | null;
  progress?: number | null;
  className?: string;
  compact?: boolean;
  tone?: "blue" | "cyan" | "emerald" | "violet";
}

const TONE_STYLES: Record<NonNullable<ProgressBarProps["tone"]>, { track: string; bar: string; glow: string; text: string }> = {
  blue: {
    track: "bg-blue-950/40 border-blue-800/30",
    bar: "from-blue-400 via-sky-300 to-blue-500",
    glow: "shadow-[0_0_18px_rgba(59,130,246,0.35)]",
    text: "text-blue-200",
  },
  cyan: {
    track: "bg-cyan-950/30 border-cyan-800/30",
    bar: "from-cyan-400 via-sky-300 to-cyan-500",
    glow: "shadow-[0_0_18px_rgba(34,211,238,0.35)]",
    text: "text-cyan-200",
  },
  emerald: {
    track: "bg-emerald-950/30 border-emerald-800/30",
    bar: "from-emerald-400 via-teal-300 to-emerald-500",
    glow: "shadow-[0_0_18px_rgba(16,185,129,0.35)]",
    text: "text-emerald-200",
  },
  violet: {
    track: "bg-violet-950/30 border-violet-800/30",
    bar: "from-violet-400 via-fuchsia-300 to-violet-500",
    glow: "shadow-[0_0_18px_rgba(139,92,246,0.35)]",
    text: "text-violet-200",
  },
};

const clampProgress = (value?: number | null) => {
  if (typeof value !== "number" || !Number.isFinite(value)) return null;
  return Math.max(0, Math.min(100, value));
};

export default function ProgressBar({
  active,
  label,
  detail,
  progress,
  className = "",
  compact = false,
  tone = "blue",
}: ProgressBarProps) {
  const [frame, setFrame] = useState(0);
  const palette = TONE_STYLES[tone];
  const normalizedProgress = clampProgress(progress);

  useEffect(() => {
    if (!active || normalizedProgress !== null) return;
    const timer = window.setInterval(() => {
      setFrame((current) => current + 1);
    }, 520);
    return () => window.clearInterval(timer);
  }, [active, normalizedProgress]);

  const animatedWidth = useMemo(() => {
    const sequence = [16, 28, 42, 57, 71, 84, 92, 68, 48, 34];
    return sequence[frame % sequence.length];
  }, [frame]);

  if (!active) return null;

  const width = normalizedProgress ?? animatedWidth;
  const statusText = normalizedProgress !== null ? `${Math.round(width)}%` : "處理中";

  return (
    <div className={`rounded-xl border px-3 ${compact ? "py-2" : "py-3"} ${palette.track} ${className}`}>
      <div className="mb-2 flex items-center justify-between gap-3">
        <div className="min-w-0">
          <div className={`truncate text-sm font-medium ${palette.text}`}>{label}</div>
          {detail ? <div className="mt-0.5 text-[11px] text-slate-400">{detail}</div> : null}
        </div>
        <div className="shrink-0 text-[11px] text-slate-400">{statusText}</div>
      </div>
      <div className="h-2 overflow-hidden rounded-full bg-slate-800/80">
        <div
          className={`h-full rounded-full bg-gradient-to-r transition-[width] duration-500 ease-out ${palette.bar} ${palette.glow}`}
          style={{ width: `${width}%` }}
        />
      </div>
    </div>
  );
}
