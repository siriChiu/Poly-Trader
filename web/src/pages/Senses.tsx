/**
 * Senses — 特徵管理頁面
 */
import { useState, useEffect, useCallback, useMemo } from "react";
import SenseModule from "../components/SenseModule";
import RadarChart from "../components/RadarChart";
import { useApi, fetchApi } from "../hooks/useApi";
import { ALL_SENSES, FEATURE_GROUPS, getSenseConfig, type FeatureGroupKey } from "../config/senses";

interface ModelStats {
  sample_count: number;
  ic_values: Record<string, number>;
  feature_importance: Record<string, number>;
}

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
  emoji?: string;
  description: string;
  modules: Record<string, SenseModuleData>;
  score: number;
}

type SensesConfig = Record<string, SenseData>;

const SENSE_COLORS = Object.fromEntries(
  Object.entries(ALL_SENSES).map(([k, v]) => [k, v.color])
);

const GROUP_ORDER: FeatureGroupKey[] = ["microstructure", "technical", "macro", "structure4h"];

const formatScore = (score?: number | null) =>
  typeof score === "number" && Number.isFinite(score) ? `${(score * 100).toFixed(0)}` : "—";

const formatIc = (value?: number) =>
  typeof value === "number" && Number.isFinite(value) ? `${value > 0 ? "+" : ""}${value.toFixed(3)}` : "—";

export default function Senses() {
  const { data: config, refresh } = useApi<SensesConfig>("/api/senses/config");
  const { data: modelStats } = useApi<ModelStats>("/api/model/stats", 60000);
  const [previewScores, setPreviewScores] = useState<Record<string, number>>({});
  const [saving, setSaving] = useState(false);
  const [lastUpdate, setLastUpdate] = useState<string>("");
  const [activeGroup, setActiveGroup] = useState<FeatureGroupKey>("microstructure");

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
      if (resp.scores) setPreviewScores(resp.scores);
      setLastUpdate(new Date().toLocaleTimeString("zh-TW"));
      refresh();
    } catch (e) {
      console.error("Toggle failed:", e);
    }
    setSaving(false);
  }, [refresh]);

  const handleWeightChange = useCallback(async (senseKey: string, moduleKey: string, weight: number) => {
    try {
      const resp = await fetchApi<any>("/api/senses/config", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ sense: senseKey, module: moduleKey, weight }),
      });
      if (resp.scores) setPreviewScores(resp.scores);
      setLastUpdate(new Date().toLocaleTimeString("zh-TW"));
      refresh();
    } catch (e) {
      console.error("Weight change failed:", e);
    }
  }, [refresh]);

  const groupedFeatures = useMemo(() => {
    if (!config) return [] as Array<[FeatureGroupKey, Array<[string, SenseData]>]>;
    const groupMap = new Map<FeatureGroupKey, Array<[string, SenseData]>>();
    for (const groupKey of GROUP_ORDER) groupMap.set(groupKey, []);
    for (const [senseKey, sense] of Object.entries(config)) {
      const meta = getSenseConfig(senseKey);
      const bucket = groupMap.get(meta.category) ?? [];
      bucket.push([senseKey, sense]);
      groupMap.set(meta.category, bucket);
    }
    return GROUP_ORDER
      .map((groupKey) => [groupKey, (groupMap.get(groupKey) ?? []).sort((a, b) => getSenseConfig(a[0]).name.localeCompare(getSenseConfig(b[0]).name, "zh-Hant"))] as [FeatureGroupKey, Array<[string, SenseData]>])
      .filter(([, items]) => items.length > 0);
  }, [config]);

  const averageScore = useMemo(() => {
    const values = Object.values(previewScores);
    if (values.length === 0) return 0;
    return Math.round(values.reduce((a, b) => a + b, 0) / values.length * 100);
  }, [previewScores]);

  const groupSummaries = useMemo(() => {
    return GROUP_ORDER.map((groupKey) => {
      const items = groupedFeatures.find(([key]) => key === groupKey)?.[1] ?? [];
      const avg = items.length
        ? Math.round(
            (items.reduce((sum, [senseKey]) => sum + (previewScores[senseKey] ?? 0.5), 0) / items.length) * 100
          )
        : 0;
      return {
        groupKey,
        items,
        count: items.length,
        avg,
      };
    });
  }, [groupedFeatures, previewScores]);

  const activeItems = groupSummaries.find((group) => group.groupKey === activeGroup)?.items ?? [];

  if (!config) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-slate-400 animate-pulse">載入特徵配置...</div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-2 lg:flex-row lg:items-end lg:justify-between">
        <div>
          <h2 className="text-xl font-bold text-slate-100">🎛️ 特徵管理</h2>
          <p className="text-sm text-slate-500">把特徵改成「市場面向」來看：短線微結構、技術指標、宏觀風險、4H 結構。</p>
        </div>
        <div className="flex items-center gap-3 text-sm">
          {saving && <span className="text-blue-400 animate-pulse">儲存中...</span>}
          {lastUpdate && <span className="text-slate-500">上次更新: {lastUpdate}</span>}
        </div>
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-12 gap-6">
        <div className="xl:col-span-4 space-y-4">
          <div className="bg-slate-900/60 rounded-xl border border-slate-700/50 p-5 flex flex-col items-center">
            <div className="flex items-center justify-between w-full mb-3">
              <h3 className="text-sm font-semibold text-slate-300">即時雷達預覽</h3>
              <span className="text-xs text-slate-500">標籤已改為市場語義短名</span>
            </div>
            <RadarChart scores={previewScores} size={420} />
            <div className="mt-3 text-center">
              <div className="text-4xl font-mono font-bold text-slate-100">{averageScore}</div>
              <div className="text-xs text-slate-500">綜合分數</div>
            </div>
          </div>

          <div className="bg-slate-900/60 rounded-xl border border-slate-700/50 p-5">
            <h3 className="text-sm font-semibold text-slate-300 mb-3">特徵面向說明</h3>
            <div className="space-y-3">
              {GROUP_ORDER.map((groupKey) => (
                <div key={groupKey} className="rounded-lg border border-slate-700/50 bg-slate-800/40 p-3">
                  <div className="text-sm font-semibold text-slate-200">{FEATURE_GROUPS[groupKey].label}</div>
                  <div className="text-xs text-slate-500 mt-1">{FEATURE_GROUPS[groupKey].description}</div>
                </div>
              ))}
            </div>
          </div>
        </div>

        <div className="xl:col-span-8 space-y-5">
          <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-3">
            {groupSummaries.map(({ groupKey, count, avg }) => {
              const active = activeGroup === groupKey;
              return (
                <button
                  key={groupKey}
                  type="button"
                  onClick={() => setActiveGroup(groupKey)}
                  className={`rounded-xl border p-4 text-left transition ${
                    active
                      ? "border-blue-500/60 bg-blue-500/10 shadow-[0_0_0_1px_rgba(59,130,246,0.25)]"
                      : "border-slate-700/50 bg-slate-900/50 hover:border-slate-600"
                  }`}
                >
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <div className="text-sm font-semibold text-slate-100">{FEATURE_GROUPS[groupKey].label}</div>
                      <div className="mt-1 text-xs leading-5 text-slate-500">{FEATURE_GROUPS[groupKey].description}</div>
                    </div>
                    <div className="text-right shrink-0">
                      <div className="text-2xl font-mono font-bold text-slate-100">{avg}</div>
                      <div className="text-[11px] text-slate-500">平均分數</div>
                    </div>
                  </div>
                  <div className="mt-3 flex items-center justify-between text-[11px] text-slate-500">
                    <span>{count} 個特徵</span>
                    <span>{active ? "目前檢視中" : "點擊切換"}</span>
                  </div>
                </button>
              );
            })}
          </div>

          <section className="space-y-3">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="text-base font-semibold text-slate-200">{FEATURE_GROUPS[activeGroup].label}</h3>
                <p className="text-xs text-slate-500">{FEATURE_GROUPS[activeGroup].description}</p>
              </div>
              <span className="text-xs text-slate-500">{activeItems.length} 個特徵 · 卡片已改為雙欄，避免頁面過長</span>
            </div>

            <div className="grid grid-cols-1 2xl:grid-cols-2 gap-4">
              {activeItems.map(([senseKey, sense]) => {
                const meta = getSenseConfig(senseKey);
                const liveScore = previewScores[senseKey] ?? sense.score ?? 0.5;
                const icValue = modelStats?.ic_values?.[senseKey];
                return (
                  <div key={senseKey} className="bg-slate-900/60 rounded-xl border border-slate-700/50 p-4">
                    <div className="flex flex-col gap-3 xl:flex-row xl:items-start xl:justify-between mb-3">
                      <div className="space-y-2 min-w-0">
                        <div className="flex flex-wrap items-center gap-2">
                          <span className="text-base font-bold text-slate-100">{meta.name}</span>
                          <span className="px-2 py-0.5 rounded-full text-[11px] bg-slate-800 text-slate-400 border border-slate-700/60">
                            {FEATURE_GROUPS[meta.category].label}
                          </span>
                        </div>
                        <p className="text-sm text-slate-400">{meta.description}</p>
                        <p className="text-xs leading-6 text-slate-500">{meta.meaning}</p>
                      </div>

                      <div className="min-w-[170px] rounded-lg border border-slate-700/50 bg-slate-800/40 px-4 py-3">
                        <div className="flex items-end justify-between gap-2">
                          <div>
                            <div className="text-xs text-slate-500">即時分數</div>
                            <div className="text-3xl font-mono font-bold" style={{ color: meta.color }}>{formatScore(liveScore)}</div>
                          </div>
                          <div className="text-right">
                            <div className="text-xs text-slate-500">IC</div>
                            <div className={`text-sm font-mono ${typeof icValue === "number" && Math.abs(icValue) > 0.05 ? "text-green-400" : "text-slate-400"}`}>
                              {formatIc(icValue)}
                            </div>
                          </div>
                        </div>
                      </div>
                    </div>

                    <div className="grid grid-cols-1 gap-2">
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
                );
              })}
            </div>
          </section>
        </div>
      </div>
    </div>
  );
}
