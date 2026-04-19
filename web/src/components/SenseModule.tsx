/**
 * SenseModule — 特徵子模組卡片
 */
import React, { useState, useRef, useEffect } from "react";

interface Props {
  moduleName: string;
  source: string;
  description: string;
  value: number | null;
  weight: number;
  enabled: boolean;
  onToggle: (enabled: boolean) => void;
  onWeightChange: (weight: number) => void;
  color?: string;
}

export default function SenseModule({
  moduleName,
  source,
  description,
  value,
  weight,
  enabled,
  onToggle,
  onWeightChange,
  color = "#3b82f6",
}: Props) {
  const [localWeight, setLocalWeight] = useState(weight);
  const isDragging = useRef(false);

  // Sync local state when parent weight changes (e.g. from API or parent re-render)
  useEffect(() => {
    if (!isDragging.current) {
      setLocalWeight(weight);
    }
  }, [weight]);

  const handleDragStart = () => {
    isDragging.current = true;
  };

  const handleDragEnd = () => {
    isDragging.current = false;
    // Only commit to parent when dragging ends
    if (localWeight !== weight) {
      onWeightChange(localWeight);
    }
  };

  return (
    <div
      className={`app-surface-muted p-3 transition-all ${
        enabled
          ? "border-slate-600/50 bg-slate-800/50"
          : "border-slate-700/30 bg-slate-800/20 opacity-50"
      }`}
    >
      {/* Header */}
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          {/* Toggle */}
          <button
            type="button"
            role="switch"
            aria-checked={enabled}
            aria-label={`${moduleName} ${enabled ? "已啟用" : "已停用"}`}
            title={`${moduleName} ${enabled ? "已啟用" : "已停用"}`}
            onClick={() => onToggle(!enabled)}
            className={`relative inline-flex h-6 w-11 shrink-0 items-center rounded-full border transition-colors focus:outline-none focus:ring-2 focus:ring-blue-400/60 ${
              enabled ? "border-blue-400/50 bg-blue-600" : "border-slate-500/60 bg-slate-700"
            }`}
          >
            <span className="sr-only">{moduleName}</span>
            <span
              aria-hidden="true"
              className={`absolute top-0.5 h-4 w-4 rounded-full bg-white shadow transition-transform ${
                enabled ? "translate-x-5" : "translate-x-1"
              }`}
            />
          </button>
          <div>
            <div className="text-sm font-medium text-slate-200">{moduleName}</div>
            <div className="text-xs text-slate-500">{source}</div>
          </div>
        </div>
        <div className="text-right text-sm font-mono" style={{ color }}>
          {value === null ? (
            <span className="text-xs text-slate-600">—</span>
          ) : Number.isFinite(value) ? (
            Math.abs(value) > 10000 ? (value/1000).toFixed(1)+"k" :
            Math.abs(value) >= 100 ? value.toFixed(0) :
            Math.abs(value) >= 1 ? value.toFixed(2) :
            (value * 100).toFixed(1)
          ) : (
            <span className="text-xs text-slate-600">—</span>
          )}
        </div>
      </div>

      {/* Description */}
      <div className="text-xs text-slate-500 mb-2">{description}</div>

      {/* Weight slider */}
      <div className="flex items-center gap-2">
        <span className="text-xs text-slate-500 w-8">權重</span>
        <input
          type="range"
          min={0}
          max={1}
          step={0.05}
          value={localWeight}
          onChange={(e) => setLocalWeight(parseFloat(e.target.value))}
          onMouseDown={handleDragStart}
          onMouseUp={handleDragEnd}
          onTouchStart={handleDragStart}
          onTouchEnd={handleDragEnd}
          disabled={!enabled}
          className="flex-1 h-1 bg-slate-700 rounded-lg appearance-none cursor-pointer accent-blue-500 disabled:opacity-30"
        />
        <span className="text-xs font-mono text-slate-400 w-10 text-right">
          {(localWeight * 100).toFixed(0)}%
        </span>
      </div>
    </div>
  );
}
