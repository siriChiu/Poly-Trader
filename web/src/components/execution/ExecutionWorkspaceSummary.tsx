import { ReactNode } from "react";
import { ExecutionSectionCard } from "./ExecutionSurface";

type ExecutionWorkspaceSummaryProps = {
  title: string;
  subtitle: string;
  aside?: ReactNode;
  actions?: ReactNode;
  children: ReactNode;
  footer?: ReactNode;
  className?: string;
  gridClassName?: string;
};

export function ExecutionWorkspaceSummary({
  title,
  subtitle,
  aside,
  actions,
  children,
  footer,
  className = "",
  gridClassName = "grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-4",
}: ExecutionWorkspaceSummaryProps) {
  return (
    <ExecutionSectionCard
      title={title}
      subtitle={subtitle}
      aside={aside}
      className={`space-y-4 ${className}`.trim()}
    >
      {actions ? <div className="flex flex-wrap gap-2 text-xs">{actions}</div> : null}
      <div className={gridClassName}>{children}</div>
      {footer ? <div>{footer}</div> : null}
    </ExecutionSectionCard>
  );
}

type ExecutionWorkspaceMetricProps = {
  label: string;
  value: ReactNode;
  detail?: ReactNode;
  extra?: ReactNode;
  toneClass?: string;
};

export function ExecutionWorkspaceMetric({
  label,
  value,
  detail,
  extra,
  toneClass = "text-white",
}: ExecutionWorkspaceMetricProps) {
  return (
    <div className="execution-card-muted h-full text-xs">
      <div className="text-[10px] tracking-wide text-slate-500">{label}</div>
      <div className={`mt-1 text-base font-semibold ${toneClass}`}>{value}</div>
      {detail ? <div className="mt-1 text-[11px] leading-5 text-slate-300">{detail}</div> : null}
      {extra ? <div className="mt-2">{extra}</div> : null}
    </div>
  );
}
