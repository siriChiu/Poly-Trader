/**
 * RadarChart — Dynamic multi-axis radar
 * Renders axes based on whatever scores are provided (no hard-coded limit)
 * Uses hex grid layout for clean display with 5-25 axes
 */
import { useCallback } from "react";

interface RadarChartProps {
  scores: Record<string, number>;
  size?: number;
  onSenseClick?: (key: string) => void;
}

export default function RadarChart({ scores, size = 320, onSenseClick }: RadarChartProps) {
  const keys = Object.keys(scores);
  const n = keys.length;
  if (n < 3) {
    return (
      <div className="flex items-center justify-center h-48 text-slate-500">
        資料不足 (needs ≥3 scores, got {n})
      </div>
    );
  }

  const cx = size / 2;
  const cy = size / 2;
  const r = Math.min(cx, cy) - 30;

  const getPoint = (i: number, value: number) => {
    const angle = (2 * Math.PI * i) / n - Math.PI / 2;
    const dist = value * r;
    return { x: cx + Math.cos(angle) * dist, y: cy + Math.sin(angle) * dist };
  };

  // Grid rings
  const rings = [0.2, 0.4, 0.6, 0.8, 1.0];

  const handleClick = useCallback((key: string) => {
    onSenseClick?.(key);
  }, [onSenseClick]);

  return (
    <svg width={size} height={size} className="select-none">
      {/* Background rings */}
      {rings.map((ring, ri) => {
        const points = Array.from({ length: n }, (_, i) => {
          const p = getPoint(i, ring);
          return `${p.x},${p.y}`;
        }).join(" ");
        return (
          <polygon key={ri} points={points}
            fill="none" stroke="#334155" strokeWidth={0.5}
            strokeDasharray={ri === rings.length - 1 ? "none" : "2,2"} />
        );
      })}

      {/* Axis lines */}
      {keys.map((key, i) => {
        const p = getPoint(i, 1);
        return <line key={key} x1={cx} y1={cy} x2={p.x} y2={p.y} stroke="#1e293b" strokeWidth={0.75} />;
      })}

      {/* Data polygon (filled) */}
      {(() => {
        const points = keys.map((key, i) => {
          const p = getPoint(i, scores[key] ?? 0.5);
          return `${p.x},${p.y}`;
        }).join(" ");
        return (
          <>
            <polygon points={points} fill="rgba(99, 102, 241, 0.15)" stroke="rgba(99, 102, 241, 0.6)" strokeWidth={1.5} />
            {/* Inner highlight */}
            <polygon points={points} fill="none" stroke="rgba(139, 92, 246, 0.8)" strokeWidth={1} />
          </>
        );
      })()}

      {/* Data points + labels */}
      {keys.map((key, i) => {
        const val = scores[key] ?? 0.5;
        const p = getPoint(i, val);
        const lp = getPoint(i, 1.12);
        const angle = (2 * Math.PI * i) / n - Math.PI / 2;
        const isRight = Math.cos(angle) > 0.1;
        const isLeft = Math.cos(angle) < -0.1;
        const anchor = isRight ? "start" : isLeft ? "end" : "middle";

        return (
          <g key={key}>
            <circle cx={p.x} cy={p.y} r={3} fill="rgba(139, 92, 246, 0.9)" stroke="#fff" strokeWidth={0.5}
              style={{ cursor: onSenseClick ? "pointer" : "default" }}
              onClick={() => handleClick(key)} />
            <text x={lp.x} y={lp.y} fill="#94a3b8" fontSize={key.length > 8 ? 7 : key.length > 5 ? 8 : 9}
              textAnchor={anchor} dominantBaseline="central"
              className="pointer-events-none"
              transform={isLeft ? `rotate(180, ${lp.x}, ${lp.y})` : ""}>
              {key}
            </text>
            <text x={p.x} y={p.y} fill="#e2e8f0" fontSize={8} textAnchor="middle" dominantBaseline="central"
              style={{ pointerEvents: "none", fontWeight: 600 }}>
              {(val * 100).toFixed(0)}
            </text>
          </g>
        );
      })}
    </svg>
  );
}
