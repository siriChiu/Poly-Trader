import { useEffect, useRef, useSyncExternalStore } from "react";

export type GlobalProgressTone = "blue" | "cyan" | "emerald" | "violet";

type GlobalProgressKind = "manual" | "network";

interface GlobalProgressTask {
  id: string;
  kind: GlobalProgressKind;
  label: string;
  detail?: string | null;
  progress?: number | null;
  tone?: GlobalProgressTone;
  priority: number;
  updatedAt: number;
}

interface GlobalProgressSnapshot {
  active: boolean;
  label: string;
  detail?: string | null;
  progress?: number | null;
  tone: GlobalProgressTone;
  activeCount: number;
}

interface GlobalProgressInput {
  label: string;
  detail?: string | null;
  progress?: number | null;
  tone?: GlobalProgressTone;
  priority?: number;
  kind?: GlobalProgressKind;
}

const listeners = new Set<() => void>();
const tasks = new Map<string, GlobalProgressTask>();

let networkBatchStarted = 0;
let networkBatchCompleted = 0;
let storeVersion = 0;
let cachedSnapshotVersion = -1;
let cachedSnapshot: GlobalProgressSnapshot = {
  active: false,
  label: "",
  detail: null,
  progress: null,
  tone: "blue",
  activeCount: 0,
};

const emit = () => {
  storeVersion += 1;
  listeners.forEach((listener) => listener());
};

const subscribe = (listener: () => void) => {
  listeners.add(listener);
  return () => listeners.delete(listener);
};

const clampProgress = (value?: number | null) => {
  if (typeof value !== "number" || !Number.isFinite(value)) return null;
  return Math.max(0, Math.min(100, value));
};

const createTaskId = () => `progress_${Date.now()}_${Math.random().toString(36).slice(2, 9)}`;

export function beginGlobalProgress(input: GlobalProgressInput): string {
  const kind = input.kind ?? "manual";
  if (kind === "network") {
    const activeNetwork = Array.from(tasks.values()).filter((task) => task.kind === "network").length;
    if (activeNetwork === 0) {
      networkBatchStarted = 0;
      networkBatchCompleted = 0;
    }
    networkBatchStarted += 1;
  }

  const id = createTaskId();
  tasks.set(id, {
    id,
    kind,
    label: input.label,
    detail: input.detail ?? null,
    progress: clampProgress(input.progress),
    tone: input.tone ?? (kind === "network" ? "blue" : "cyan"),
    priority: input.priority ?? (kind === "network" ? 10 : 50),
    updatedAt: Date.now(),
  });
  emit();
  return id;
}

export function updateGlobalProgress(id: string, patch: Partial<GlobalProgressInput>) {
  const current = tasks.get(id);
  if (!current) return;
  const next: GlobalProgressTask = {
    ...current,
    label: patch.label ?? current.label,
    detail: patch.detail === undefined ? current.detail : patch.detail,
    progress: patch.progress === undefined ? current.progress : clampProgress(patch.progress),
    tone: patch.tone ?? current.tone,
    priority: patch.priority ?? current.priority,
    updatedAt: Date.now(),
  };

  if (
    next.label === current.label &&
    next.detail === current.detail &&
    next.progress === current.progress &&
    next.tone === current.tone &&
    next.priority === current.priority
  ) {
    return;
  }

  tasks.set(id, next);
  emit();
}

export function endGlobalProgress(id: string) {
  const current = tasks.get(id);
  if (!current) return;
  if (current.kind === "network") {
    networkBatchCompleted += 1;
  }
  tasks.delete(id);
  emit();
}

const buildNetworkSnapshot = (networkTasks: GlobalProgressTask[]): GlobalProgressSnapshot => {
  const activeCount = networkTasks.length;
  const progress = networkBatchStarted > 0 ? clampProgress((networkBatchCompleted / networkBatchStarted) * 100) : null;
  const labels = Array.from(new Set(networkTasks.map((task) => task.label))).slice(0, 2);
  const detail = labels.length > 0
    ? `${labels.join(" · ")}${activeCount > labels.length ? ` 等 ${activeCount} 個請求` : ""}`
    : `${activeCount} 個請求進行中`;

  return {
    active: activeCount > 0,
    label: activeCount > 1 ? `載入中（${activeCount} 個請求）` : (networkTasks[0]?.label || "資料載入中"),
    detail,
    progress,
    tone: "blue",
    activeCount,
  };
};

const computeSnapshot = (): GlobalProgressSnapshot => {
  if (tasks.size === 0) {
    return {
      active: false,
      label: "",
      detail: null,
      progress: null,
      tone: "blue",
      activeCount: 0,
    };
  }

  const allTasks = Array.from(tasks.values());
  const manualTasks = allTasks.filter((task) => task.kind === "manual");
  if (manualTasks.length > 0) {
    const topTask = [...manualTasks].sort((a, b) => {
      if (a.priority !== b.priority) return b.priority - a.priority;
      return b.updatedAt - a.updatedAt;
    })[0];
    return {
      active: true,
      label: topTask.label,
      detail: topTask.detail ?? null,
      progress: clampProgress(topTask.progress),
      tone: topTask.tone ?? "cyan",
      activeCount: allTasks.length,
    };
  }

  return buildNetworkSnapshot(allTasks.filter((task) => task.kind === "network"));
};

const getSnapshot = (): GlobalProgressSnapshot => {
  if (cachedSnapshotVersion === storeVersion) {
    return cachedSnapshot;
  }
  cachedSnapshot = computeSnapshot();
  cachedSnapshotVersion = storeVersion;
  return cachedSnapshot;
};

export function useGlobalProgressSnapshot() {
  return useSyncExternalStore(subscribe, getSnapshot, getSnapshot);
}

export function useGlobalProgressTask(active: boolean, input: GlobalProgressInput | null) {
  const taskIdRef = useRef<string | null>(null);

  useEffect(() => {
    if (!active || !input) {
      if (taskIdRef.current) {
        endGlobalProgress(taskIdRef.current);
        taskIdRef.current = null;
      }
      return;
    }

    if (!taskIdRef.current) {
      taskIdRef.current = beginGlobalProgress(input);
      return;
    }

    updateGlobalProgress(taskIdRef.current, input);
  }, [active, input?.detail, input?.kind, input?.label, input?.priority, input?.progress, input?.tone]);

  useEffect(() => () => {
    if (taskIdRef.current) {
      endGlobalProgress(taskIdRef.current);
      taskIdRef.current = null;
    }
  }, []);
}
