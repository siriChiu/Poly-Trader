/**
 * Senses — 感官管理頁面
 * 每個感官一個卡片，可調整子模組權重、啟用/停用
 */
import { useState, useEffect, useCallback } from "react";
import SenseModule from "../components/SenseModule";
import RadarChart from "../components/RadarChart";
import { useApi, fetchApi } from "../hooks/useApi";

interface SenseModuleData {
  name: string;
  source: string;
  description: string;
  enabled: boolean;
  weight: number;
  value: number | null;
}

interface SenseData {
  name: string;
  emoji: string;
  description: string;
  modules: Record<string, SenseModuleData>;
  score: number;
}

type SensesConfig = Record<string, SenseData>;

const SENSE_COLORS: Record<string, string> = {
  eye: "#3b82f6",
  ear: "#8b5cf6",
  nose: "#f59e0b",
  tongue: "#ec4899",
  body: "#14b8a6",
  pulse: "#ef4444",
  aura: "#a855f7",
  mind: "#06b6d4",
};

export default function Senses() {
  const { data: config, refresh } = useApi<SensesConfig>("/api/senses/config");
  const [previewScores, setPreviewScores] = useState<Record<string, number>>({});
  const [saving, setSaving] = useState(false);
  const [lastUpdate, setLastUpdate] = useState<string>("");

  // Initialize preview scores
  useEffect(() => {
    if (config) {
      const scores: Record<string, number> = {};
      for (const [key, sense] of Object.entries(config)) {
        scores[key] = sense.score ?? 0.5;
      }
      setPreviewScores(scores);
    }
  }, [config]);

  const handleToggle = useCallback(async (senseKey: string, moduleKey: string, enabled: boolean) => {
    setSaving(true);
    try {
      const resp = await fetchApi<any>("/api/senses/config", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ sense: senseKey, module: moduleKey, enabled }),
      });
      if (resp.scores) {
        setPreviewScores(resp.scores);
      }
      setLastUpdate(new Date().toLocaleTimeString("zh-TW"));
      refresh();
    } catch (e) {
      console.error("Toggle failed:", e);
    }
    setSaving(false);
  }, [refresh]);

  const handleWeightChange = useCallback(async (senseKey: string, moduleKey: string, weight: number) => {
    // Optimistic update
    setPreviewScores((prev) => ({ ...prev }));

    try {
      const resp = await fetchApi<any>("/api/senses/config", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ sense: senseKey, module: moduleKey, weight }),
      });
      if (resp.scores) {
        setPreviewScores(resp.scores);
      }
      setLastUpdate(new Date().toLocaleTimeString("zh-TW"));
      refresh();
    } catch (e) {
      console.error("Weight change failed:", e);
    }
  }, [refresh]);

  if (!config) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-slate-400 animate-pulse">載入感官配置...</div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-xl font-bold text-slate-100">🎛️ 感官管理</h2>
        <div className="flex items-center gap-3 text-sm">
          {saving && <span className="text-blue-400 animate-pulse">儲存中...</span>}
          {lastUpdate && (
            <span className="text-slate-500">上次更新: {lastUpdate}</span>
          )}
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left: Radar preview */}
        <div className="lg:col-span-1 bg-slate-900/50 rounded-xl border border-slate-700/50 p-4 flex flex-col items-center justify-center">
          <h3 className="text-sm font-semibold text-slate-400 mb-3 self-start">即時預覽</h3>
          <RadarChart scores={previewScores} size={260} />
          <div className="mt-3 text-center">
            <div className="text-3xl font-mono font-bold text-slate-200">
              {Math.round(Object.values(previewScores).reduce((a, b) => a + b, 0) / Math.max(Object.keys(previewScores).length, 1) * 100)}
            </div>
            <div className="text-xs text-slate-500">綜合分數</div>
          </div>
        </div>

        {/* Right: Sense cards */}
        <div className="lg:col-span-2 space-y-4">
          {Object.entries(config).map(([senseKey, sense]) => (
            <div
              key={senseKey}
              className="bg-slate-900/50 rounded-xl border border-slate-700/50 p-4"
            >
              {/* Sense header */}
              <div className="flex items-center justify-between mb-3">
                <div className="flex items-center gap-2">
                  <span className="text-2xl">{sense.emoji}</span>
                  <div>
                    <span className="text-base font-bold text-slate-200">{sense.name}</span>
                    <span className="text-xs text-slate-500 ml-2">{sense.description}</span>
                  </div>
                </div>
                <div
                  className="text-2xl font-mono font-bold"
                  style={{ color: SENSE_COLORS[senseKey] }}
                >
                  {((previewScores[senseKey] ?? sense.score ?? 0.5) * 100).toFixed(0)}
                </div>
              </div>

              {/* Modules */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                {Object.entries(sense.modules).map(([modKey, mod]) => (
                  <SenseModule
                    key={modKey}
                    moduleName={mod.name}
                    source={mod.source}
                    description={mod.description}
                    value={mod.value}
                    weight={mod.weight}
                    enabled={mod.enabled}
                    color={SENSE_COLORS[senseKey]}
                    onToggle={(enabled) => handleToggle(senseKey, modKey, enabled)}
                    onWeightChange={(weight) => handleWeightChange(senseKey, modKey, weight)}
                  />
                ))}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
