import { Badge } from "@/components/ui/badge";
import type { RunStatus } from "@mmpose-video-keypoint-extraction/shared";

const VARIANTS: Record<
  RunStatus,
  { label: string; variant: "default" | "secondary" | "destructive" | "outline"; dot: string }
> = {
  pending: { label: "Pending", variant: "outline", dot: "bg-muted-foreground" },
  running: { label: "Running", variant: "secondary", dot: "bg-[var(--chart-1)] animate-pulse" },
  done: { label: "Done", variant: "default", dot: "bg-[var(--success)]" },
  error: { label: "Error", variant: "destructive", dot: "bg-destructive" },
};

export function RunStatusBadge({ status }: { status: RunStatus }) {
  const cfg = VARIANTS[status] ?? VARIANTS.pending;
  return (
    <Badge variant={cfg.variant} className="gap-1.5">
      <span className={`h-1.5 w-1.5 rounded-full ${cfg.dot}`} />
      {cfg.label}
    </Badge>
  );
}
