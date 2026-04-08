/**
 * RadarChart — Dynamic multi-axis radar with readable labels.
 */
import { useCallback, useMemo } from "react";
import { getSenseConfig } from "../config/senses";

interface RadarChartProps {
  scores: Record<string, number>;
  size?: number;
  onSenseClick?: (key: string) => void;
}

export default function RadarChart({ scores, size = 360, onSenseClick }: RadarChartProps) {
  const keys = Object.keys(scores);
  const n = keys.length;

  const items = useMemo(() => keys.map((key) => ({ key, meta: getSenseConfig(key) })), [keys]);
  const handleClick = useCallback((key: string) => {
    onSenseClick?.(key);
  }, [onSenseClick]);

  if (n < 3) {
    return (
      <div className="flex items-center justify-center h-48 text-slate-500">
        資料不足 (needs ≥3 scores, got {n})
      </div>
    );
  }

  const chartSize = size;
  const padding = Math.max(74, Math.round(chartSize * 0.18));
  const cx = chartSize / 2;
  const cy = chartSize / 2;
  const r = Math.min(cx, cy) - padding;

  const getPoint = (i: number, value: number, scale = 1) => {
    const angle = (2 * Math.PI * i) / n - Math.PI / 2;
    const dist = value * r * scale;
    return { x: cx + Math.cos(angle) * dist, y: cy + Math.sin(angle) * dist, angle };
  };

  const rings = [0.2, 0.4, 0.6, 0.8, 1.0];

  return (
    <svg width={chartSize} height={chartSize} viewBox={`0 0 ${chartSize} ${chartSize}`} className="select-none overflow-visible">
      {rings.map((ring, ri) => {
        const points = Array.from({ length: n }, (_, i) => {
          const p = getPoint(i, ring);
          return `${p.x},${p.y}`;
        }).join(" ");
        return (
          <polygon
            key={ri}
            points={points}
            fill={ri === rings.length - 1 ? "rgba(15, 23, 42, 0.35)" : "none"}
            stroke="#334155"
            strokeWidth={0.6}
            strokeDasharray={ri === rings.length - 1 ? "none" : "3,3"}
          />
        );
      })}

      {items.map(({ key }, i) => {
        const p = getPoint(i, 1);
        return <line key={key} x1={cx} y1={cy} x2={p.x} y2={p.y} stroke="#1e293b" strokeWidth={0.8} />;
      })}

      {(() => {
        const points = items.map(({ key }, i) => {
          const p = getPoint(i, scores[key] ?? 0.5);
          return `${p.x},${p.y}`;
        }).join(" ");
        return (
          <>
            <polygon points={points} fill="rgba(99, 102, 241, 0.16)" stroke="rgba(129, 140, 248, 0.9)" strokeWidth={2} />
            <polygon points={points} fill="none" stroke="rgba(139, 92, 246, 0.8)" strokeWidth={1} />
          </>
        );
      })()}

      {items.map(({ key, meta }, i) => {
        const val = scores[key] ?? 0.5;
        const p = getPoint(i, val);
        const lp = getPoint(i, 1, 1.18);
        const isRight = Math.cos(lp.angle) > 0.2;
        const isLeft = Math.cos(lp.angle) < -0.2;
        const anchor = isRight ? "start" : isLeft ? "end" : "middle";
        const label = meta.shortLabel;
        return (
          <g key={key}>
            <circle
              cx={p.x}
              cy={p.y}
              r={4}
              fill={meta.color}
              stroke="#e2e8f0"
              strokeWidth={0.8}
              style={{ cursor: onSenseClick ? "pointer" : "default" }}
              onClick={() => handleClick(key)}
            />
            <text
              x={lp.x}
              y={lp.y}
              fill="#cbd5e1"
              fontSize={11}
              textAnchor={anchor}
              dominantBaseline="central"
              className="pointer-events-none"
              style={{ fontWeight: 600 }}
            >
              {label}
            </text>
            <text
              x={p.x}
              y={p.y - 11}
              fill="#f8fafc"
              fontSize={9}
              textAnchor="middle"
              dominantBaseline="central"
              style={{ pointerEvents: "none", fontWeight: 700 }}
            >
              {(val * 100).toFixed(0)}
            </text>
          </g>
        );
      })}
    </svg>
  );
}
