/**
 * RadarChart — 多邊形雷達圖（SVG）+ Hover Tooltip
 */
import React, { useMemo, useState } from "react";

interface Props {
  scores: Record<string, number>;
  size?: number;
  onSenseClick?: (senseKey: string) => void;
}

export const SENSE_KEYS = ["eye", "ear", "nose", "tongue", "body", "pulse", "aura", "mind"];

export const SENSE_INFO: Record<string, { label: string; color: string; source: string }> = {
  eye:   { label: "👁️ Eye",   color: "#3b82f6", source: "72h Funding Rate 均值 (IC=-0.172)" },
  ear:   { label: "👂 Ear",   color: "#8b5cf6", source: "48h 價格動量 (IC=-0.200)" },
  nose:  { label: "👃 Nose",  color: "#f59e0b", source: "48h 收益率自相關 (IC=+0.062)" },
  tongue:{ label: "👅 Tongue",color: "#ec4899", source: "24h 波動率 (IC=+0.028)" },
  body:  { label: "💪 Body",  color: "#14b8a6", source: "24h 價格區間位置 (IC=+0.227)" },
  pulse: { label: "💓 Pulse", color: "#ef4444", source: "Funding Rate 趨勢 (IC=+0.037)" },
  aura:  { label: "🌀 Aura",  color: "#a855f7", source: "波動率×自相關交互 (IC=+0.303)" },
  mind:  { label: "🧠 Mind",  color: "#06b6d4", source: "24h Funding Z-score (IC=-0.034)" },
};

function polygon(cx: number, cy: number, r: number, count: number) {
  const points: [number, number][] = [];
  for (let i = 0; i < count; i++) {
    const angle = (Math.PI * 2 * i) / count - Math.PI / 2;
    points.push([cx + r * Math.cos(angle), cy + r * Math.sin(angle)]);
  }
  return points;
}

export default function RadarChart({ scores, size = 320, onSenseClick }: Props) {
  const cx = size / 2;
  const cy = size / 2;
  const maxR = size * 0.35;
  const count = SENSE_KEYS.length;
  const [hoveredSense, setHoveredSense] = useState<string | null>(null);
  const [tooltipPos, setTooltipPos] = useState({ x: 0, y: 0 });

  const gridLevels = [0.2, 0.4, 0.6, 0.8, 1.0];
  const outerPoints = useMemo(() => polygon(cx, cy, maxR, count), [cx, cy, maxR, count]);

  const dataPoints = useMemo(() => {
    return SENSE_KEYS.map((key, i) => {
      const score = scores[key] ?? 0.5;
      const angle = (Math.PI * 2 * i) / count - Math.PI / 2;
      const r = maxR * score;
      return [cx + r * Math.cos(angle), cy + r * Math.sin(angle)] as [number, number];
    });
  }, [scores, cx, cy, maxR, count]);

  const dataPath = dataPoints.map((p, i) => `${i === 0 ? "M" : "L"}${p[0]},${p[1]}`).join(" ") + " Z";

  const avgScore = SENSE_KEYS.reduce((sum, k) => sum + (scores[k] ?? 0.5), 0) / SENSE_KEYS.length;
  const fillColor = avgScore > 0.6 ? "rgba(34,197,94,0.15)" : avgScore < 0.4 ? "rgba(239,68,68,0.15)" : "rgba(234,179,8,0.15)";

  const handleMouseEnter = (key: string, e: React.MouseEvent) => {
    setHoveredSense(key);
    const rect = (e.target as SVGElement).closest("svg")?.getBoundingClientRect();
    if (rect) {
      setTooltipPos({ x: e.clientX - rect.left, y: e.clientY - rect.top });
    }
  };

  return (
    <div className="flex flex-col items-center relative">
      <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`}>
        {/* Grid */}
        {gridLevels.map((level) => {
          const pts = polygon(cx, cy, maxR * level, count);
          const path = pts.map((p, i) => `${i === 0 ? "M" : "L"}${p[0]},${p[1]}`).join(" ") + " Z";
          return <path key={level} d={path} fill="none" stroke="#334155" strokeWidth={1} opacity={0.5} />;
        })}

        {/* Axes */}
        {outerPoints.map((p, i) => (
          <line key={i} x1={cx} y1={cy} x2={p[0]} y2={p[1]} stroke="#334155" strokeWidth={1} opacity={0.3} />
        ))}

        {/* Data polygon */}
        <path d={dataPath} fill={fillColor} stroke="#3b82f6" strokeWidth={2} strokeLinejoin="round" />

        {/* Data points with hover */}
        {dataPoints.map((p, i) => {
          const key = SENSE_KEYS[i];
          const info = SENSE_INFO[key];
          const isHovered = hoveredSense === key;
          return (
            <g key={key}>
              {/* Invisible larger hit area */}
              <circle cx={p[0]} cy={p[1]} r={15} fill="transparent"
                onMouseEnter={(e) => handleMouseEnter(key, e)}
                onMouseLeave={() => setHoveredSense(null)}
                onClick={() => onSenseClick?.(key)}
                style={{ cursor: "pointer" }}
              />
              {/* Visible dot */}
              <circle cx={p[0]} cy={p[1]} r={isHovered ? 7 : 5}
                fill={info.color} stroke="#0f172a" strokeWidth={2}
                style={{ transition: "r 0.2s" }}
              />
            </g>
          );
        })}

        {/* Labels */}
        {outerPoints.map((p, i) => {
          const key = SENSE_KEYS[i];
          const info = SENSE_INFO[key];
          const score = scores[key] ?? 0.5;
          const labelAngle = (Math.PI * 2 * i) / count - Math.PI / 2;
          const labelR = maxR + 30;
          const lx = cx + labelR * Math.cos(labelAngle);
          const ly = cy + labelR * Math.sin(labelAngle);

          return (
            <g key={key}
              onMouseEnter={(e) => handleMouseEnter(key, e)}
              onMouseLeave={() => setHoveredSense(null)}
              onClick={() => onSenseClick?.(key)}
              style={{ cursor: "pointer" }}
            >
              <text x={lx} y={ly - 8} textAnchor="middle" fill="#e2e8f0" fontSize={13} fontWeight="bold">
                {info.label}
              </text>
              <text x={lx} y={ly + 8} textAnchor="middle" fill={info.color} fontSize={12} fontWeight="bold">
                {(score * 100).toFixed(0)}
              </text>
            </g>
          );
        })}
      </svg>

      {/* Tooltip */}
      {hoveredSense && (
        <div
          className="absolute bg-slate-800 border border-slate-600 rounded-lg px-3 py-2 text-sm shadow-xl z-50 pointer-events-none"
          style={{
            left: tooltipPos.x + 15,
            top: tooltipPos.y - 10,
            minWidth: 180,
          }}
        >
          <div className="font-bold text-white mb-1">
            {SENSE_INFO[hoveredSense].label}：{(scores[hoveredSense] ?? 0.5 * 100).toFixed(0)} 分
          </div>
          <div className="text-slate-400 text-xs">
            數據來源：{SENSE_INFO[hoveredSense].source}
          </div>
        </div>
      )}
    </div>
  );
}
