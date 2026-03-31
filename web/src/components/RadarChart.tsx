/**
 * RadarChart — 五角雷達圖（SVG）
 */
import React, { useMemo } from "react";

interface Props {
  scores: Record<string, number>;
  size?: number;
}

const SENSE_KEYS = ["eye", "ear", "nose", "tongue", "body"];
const SENSE_LABELS: Record<string, string> = {
  eye: "👁️ Eye",
  ear: "👂 Ear",
  nose: "👃 Nose",
  tongue: "👅 Tongue",
  body: "💪 Body",
};

const COLORS = {
  eye: "#3b82f6",
  ear: "#8b5cf6",
  nose: "#f59e0b",
  tongue: "#ec4899",
  body: "#14b8a6",
};

function pentagonPoints(cx: number, cy: number, r: number, count: number = 5) {
  const points: [number, number][] = [];
  for (let i = 0; i < count; i++) {
    const angle = (Math.PI * 2 * i) / count - Math.PI / 2;
    points.push([cx + r * Math.cos(angle), cy + r * Math.sin(angle)]);
  }
  return points;
}

export default function RadarChart({ scores, size = 320 }: Props) {
  const cx = size / 2;
  const cy = size / 2;
  const maxR = size * 0.38;

  const gridLevels = [0.2, 0.4, 0.6, 0.8, 1.0];
  const outerPoints = useMemo(() => pentagonPoints(cx, cy, maxR), [cx, cy, maxR]);

  const dataPoints = useMemo(() => {
    return SENSE_KEYS.map((key, i) => {
      const score = scores[key] ?? 0.5;
      const angle = (Math.PI * 2 * i) / 5 - Math.PI / 2;
      const r = maxR * score;
      return [cx + r * Math.cos(angle), cy + r * Math.sin(angle)] as [number, number];
    });
  }, [scores, cx, cy, maxR]);

  const dataPath = dataPoints.map((p, i) => `${i === 0 ? "M" : "L"}${p[0]},${p[1]}`).join(" ") + " Z";

  // 計算綜合分數用於填充顏色
  const avgScore = SENSE_KEYS.reduce((sum, k) => sum + (scores[k] ?? 0.5), 0) / 5;
  const fillColor = avgScore > 0.6 ? "rgba(34,197,94,0.2)" : avgScore < 0.4 ? "rgba(239,68,68,0.2)" : "rgba(234,179,8,0.2)";

  return (
    <div className="flex flex-col items-center">
      <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`}>
        {/* 網格線 */}
        {gridLevels.map((level) => {
          const pts = pentagonPoints(cx, cy, maxR * level);
          const path = pts.map((p, i) => `${i === 0 ? "M" : "L"}${p[0]},${p[1]}`).join(" ") + " Z";
          return (
            <path
              key={level}
              d={path}
              fill="none"
              stroke="#334155"
              strokeWidth={1}
              opacity={0.6}
            />
          );
        })}

        {/* 軸線 */}
        {outerPoints.map((p, i) => (
          <line
            key={i}
            x1={cx}
            y1={cy}
            x2={p[0]}
            y2={p[1]}
            stroke="#334155"
            strokeWidth={1}
            opacity={0.4}
          />
        ))}

        {/* 數據多邊形 */}
        <path
          d={dataPath}
          fill={fillColor}
          stroke="#3b82f6"
          strokeWidth={2}
          strokeLinejoin="round"
        />

        {/* 數據點 */}
        {dataPoints.map((p, i) => (
          <circle
            key={i}
            cx={p[0]}
            cy={p[1]}
            r={5}
            fill={COLORS[SENSE_KEYS[i]]}
            stroke="#0f172a"
            strokeWidth={2}
          />
        ))}

        {/* 標籤 */}
        {outerPoints.map((p, i) => {
          const key = SENSE_KEYS[i];
          const score = scores[key] ?? 0.5;
          const labelAngle = (Math.PI * 2 * i) / 5 - Math.PI / 2;
          const labelR = maxR + 28;
          const lx = cx + labelR * Math.cos(labelAngle);
          const ly = cy + labelR * Math.sin(labelAngle);

          return (
            <g key={key}>
              <text
                x={lx}
                y={ly - 8}
                textAnchor="middle"
                fill="#e2e8f0"
                fontSize={13}
                fontWeight="bold"
              >
                {SENSE_LABELS[key]}
              </text>
              <text
                x={lx}
                y={ly + 8}
                textAnchor="middle"
                fill={COLORS[key]}
                fontSize={12}
                fontWeight="bold"
              >
                {(score * 100).toFixed(0)}
              </text>
            </g>
          );
        })}
      </svg>
    </div>
  );
}
