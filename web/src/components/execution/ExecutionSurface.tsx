import { ReactNode } from "react";

type ExecutionHeroProps = {
  eyebrow: string;
  title: string;
  subtitle: string;
  statusPills?: ReactNode;
  actions?: ReactNode;
  children?: ReactNode;
  className?: string;
};

export function ExecutionHero({ eyebrow, title, subtitle, statusPills, actions, children, className = "" }: ExecutionHeroProps) {
  return (
    <section className={`execution-hero ${className}`.trim()}>
      <div className="flex flex-col gap-4 xl:flex-row xl:items-start xl:justify-between">
        <div>
          <div className="execution-kicker">{eyebrow}</div>
          <h1 className="execution-title">{title}</h1>
          <p className="execution-subtitle">{subtitle}</p>
          {statusPills ? <div className="mt-3 flex flex-wrap gap-2 text-[11px] text-slate-300">{statusPills}</div> : null}
        </div>
        {actions ? <div className="flex flex-wrap gap-2 text-sm">{actions}</div> : null}
      </div>
      {children ? <div className="mt-4 space-y-3">{children}</div> : null}
    </section>
  );
}

type ExecutionSectionCardProps = {
  title: string;
  subtitle?: string;
  aside?: ReactNode;
  children: ReactNode;
  className?: string;
};

export function ExecutionSectionCard({ title, subtitle, aside, children, className = "" }: ExecutionSectionCardProps) {
  return (
    <section className={`execution-card ${className}`.trim()}>
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <div className="text-lg font-semibold text-white">{title}</div>
          {subtitle ? <div className="mt-1 text-sm text-slate-400">{subtitle}</div> : null}
        </div>
        {aside ? <div>{aside}</div> : null}
      </div>
      <div className="mt-4">{children}</div>
    </section>
  );
}

type ExecutionMetricCardProps = {
  title: string;
  value: ReactNode;
  detail?: ReactNode;
  toneClass?: string;
};

export function ExecutionMetricCard({ title, value, detail, toneClass = "text-white" }: ExecutionMetricCardProps) {
  return (
    <div className="execution-card-muted">
      <div className="text-[11px] tracking-[0.22em] text-slate-500">{title}</div>
      <div className={`mt-2 text-3xl font-semibold ${toneClass}`}>{value}</div>
      {detail ? <div className="mt-2 text-sm text-slate-400">{detail}</div> : null}
    </div>
  );
}

export function ExecutionPill({ children, className = "" }: { children: ReactNode; className?: string }) {
  return <span className={`execution-pill ${className}`.trim()}>{children}</span>;
}
