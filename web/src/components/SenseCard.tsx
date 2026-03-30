/**
 * SenseCard — Single sense status card
 */
interface Props {
  name: string;
  label: string;
  value: number | null | undefined;
  format?: "pct" | "int" | "fixed4" | "raw";
  description?: string;
}

function formatValue(val: number | null | undefined, format: string): string {
  if (val === null || val === undefined) return "—";
  switch (format) {
    case "pct":
      return `${(val * 100).toFixed(2)}%`;
    case "int":
      return `${Math.round(val)}`;
    case "fixed4":
      return val.toFixed(4);
    default:
      return val.toString();
  }
}

function getStatusColor(val: number | null | undefined): string {
  if (val === null || val === undefined) return "bg-slate-600";
  if (typeof val === "number" && Math.abs(val) > 0.5) return "bg-amber-500";
  return "bg-green-500";
}

export default function SenseCard({
  name,
  label,
  value,
  format = "raw",
  description,
}: Props) {
  return (
    <div className="flex items-center justify-between px-3 py-2 bg-slate-800/50 rounded-lg border border-slate-700/50 hover:border-slate-600 transition">
      <div className="flex items-center gap-2">
        <span className="text-lg">{name.split(" ")[0]}</span>
        <div>
          <div className="text-sm font-medium text-white">
            {name.split(" ").slice(1).join(" ")}
          </div>
          {description && (
            <div className="text-xs text-slate-500">{description}</div>
          )}
        </div>
      </div>
      <div className="flex items-center gap-2">
        <span className="text-sm font-mono text-slate-200">
          {formatValue(value, format)}
        </span>
        <span
          className={`w-2 h-2 rounded-full ${getStatusColor(value)}`}
          title={value !== null && value !== undefined ? "正常" : "無數據"}
        />
      </div>
    </div>
  );
}
