"use client";

import { useRouter } from "next/navigation";
import { AlertTriangle, Download, FileJson, Play, Trash2 } from "lucide-react";
import { toast } from "sonner";

import { Button, buttonVariants } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Skeleton } from "@/components/ui/skeleton";
import { Progress } from "@/components/ui/progress";
import { ErrorState } from "@/components/ui/error-state";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from "@/components/ui/alert-dialog";
import { RunStatusBadge } from "@/components/runs/run-status-badge";
import { OverlayGallery } from "@/components/runs/overlay-gallery";
import { EditRunForm } from "@/components/runs/run-form";
import {
  useDeleteRun,
  useEngineStatus,
  useExecuteRun,
  useObjectPreviewUrl,
  useRun,
  useSessions,
} from "@/lib/queries";
import { formatDate } from "@/lib/utils";

/** Open a B2 object (manifest / keypoints JSON) via a short-lived presigned URL. */
function ObjectOpenButton({
  objectKey,
  label,
  icon: Icon,
}: {
  objectKey: string;
  label: string;
  icon: typeof Download;
}) {
  const preview = useObjectPreviewUrl();

  return (
    <Button
      variant="outline"
      size="sm"
      disabled={preview.isPending}
      onClick={() =>
        preview.mutate(objectKey, {
          onSuccess: ({ url }) => window.open(url, "_blank", "noopener"),
          onError: (e) => toast.error("Could not open object", { description: e.message }),
        })
      }
    >
      <Icon className="h-3.5 w-3.5" />
      {label}
    </Button>
  );
}

function Meta({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <div className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">
        {label}
      </div>
      <div className="text-sm font-medium tabular-nums">{value}</div>
    </div>
  );
}

export function RunDetail({ runId }: { runId: string }) {
  const router = useRouter();
  const { data: run, isLoading, error, refetch } = useRun(runId);
  const engine = useEngineStatus();
  const execute = useExecuteRun();
  const deleteRun = useDeleteRun();
  const sessions = useSessions();

  if (isLoading) return <Skeleton className="h-96 w-full" />;
  if (error) return <ErrorState error={error} onRetry={() => refetch()} />;
  if (!run) return null;

  const indexKey = run.manifest_key.replace(/run\.json$/, "keypoints_index.jsonl");
  const busy = run.status === "running" || run.status === "pending";
  const engineUnavailable = engine.data && engine.data.available === false;
  // Total frames the run will process, from the source session (no schema
  // change needed): the worker iterates exactly these frames.
  const framesTotal =
    sessions.data?.find((s) => s.session === run.session)?.frame_count ?? 0;
  // frame_count advances mid-run — the worker persists it after every frame.
  const framesDone = run.summary.frame_count || 0;

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-start justify-between gap-4 border-b border-border pb-5">
        <div className="min-w-0">
          <div className="flex items-center gap-3">
            <h1 className="page-title truncate">{run.label}</h1>
            <RunStatusBadge status={run.status} />
          </div>
          <p className="mt-1.5 text-sm text-muted-foreground">
            Session <span className="font-medium">{run.session}</span> · created{" "}
            {formatDate(run.created_at)}
          </p>
        </div>
        <div className="flex shrink-0 items-center gap-2">
          <Button
            size="sm"
            disabled={run.status === "running" || execute.isPending || !!engineUnavailable}
            onClick={() =>
              execute.mutate(run.id, {
                onSuccess: () => toast.success("Extraction started"),
                onError: (e) =>
                  toast.error("Could not start extraction", { description: e.message }),
              })
            }
          >
            <Play className="h-3.5 w-3.5" />
            {run.status === "done" ? "Re-run" : "Execute"}
          </Button>
          <AlertDialog>
            <AlertDialogTrigger asChild>
              <Button variant="outline" size="sm">
                <Trash2 className="h-3.5 w-3.5" />
                Delete
              </Button>
            </AlertDialogTrigger>
            <AlertDialogContent>
              <AlertDialogHeader>
                <AlertDialogTitle>Delete this run?</AlertDialogTitle>
                <AlertDialogDescription>
                  Permanently deletes every artifact under this run&apos;s prefix
                  on B2. Source frames are untouched. This cannot be undone.
                </AlertDialogDescription>
              </AlertDialogHeader>
              <AlertDialogFooter>
                <AlertDialogCancel>Cancel</AlertDialogCancel>
                <AlertDialogAction
                  className={buttonVariants({ variant: "destructive" })}
                  onClick={() =>
                    deleteRun.mutate(run.id, {
                      onSuccess: () => {
                        toast.success("Run deleted");
                        router.push("/runs");
                      },
                    })
                  }
                >
                  Delete run
                </AlertDialogAction>
              </AlertDialogFooter>
            </AlertDialogContent>
          </AlertDialog>
        </div>
      </div>

      {engineUnavailable && run.status !== "done" && (
        <Alert>
          <AlertTriangle />
          <AlertTitle>Engine not installed</AlertTitle>
          <AlertDescription>{engine.data?.detail}</AlertDescription>
        </Alert>
      )}

      {run.status === "error" && run.error && (
        <Alert variant="destructive">
          <AlertTriangle />
          <AlertTitle>Extraction failed</AlertTitle>
          <AlertDescription>{run.error}</AlertDescription>
        </Alert>
      )}

      {busy && (
        <Alert>
          <AlertTitle>
            {run.status === "pending" ? "Ready to run" : "Running — preparing model & extracting"}
          </AlertTitle>
          <AlertDescription>
            {run.status === "pending" ? (
              <p>
                This run hasn&apos;t started yet. Click <span className="font-medium">Execute</span>{" "}
                to extract keypoints from its {framesTotal || "source"} frames.
              </p>
            ) : (
              <>
                <p>
                  The first run of a model downloads its checkpoint from the
                  OpenMMLab zoo, which can take a few minutes. This page updates
                  automatically as frames are processed.
                </p>
                {framesTotal > 0 && (
                  <div className="mt-2 w-full max-w-md space-y-1">
                    <Progress value={Math.min(100, (framesDone / framesTotal) * 100)} />
                    <p className="text-xs tabular-nums text-muted-foreground">
                      Frame {framesDone} of {framesTotal}
                    </p>
                  </div>
                )}
              </>
            )}
          </AlertDescription>
        </Alert>
      )}

      <Card>
        <CardHeader className="border-b border-border py-4 px-5">
          <CardTitle className="card-title">Configuration & summary</CardTitle>
        </CardHeader>
        <CardContent className="grid grid-cols-2 gap-4 p-5 sm:grid-cols-4">
          <Meta label="Model" value={run.model} />
          <Meta label="Device" value={run.device} />
          <Meta label="Threshold" value={String(run.kpt_thr)} />
          <Meta label="Frames" value={String(run.summary.frame_count || 0)} />
          <Meta label="Instances" value={String(run.summary.total_instances)} />
          <Meta label="Keypoints" value={String(run.summary.total_keypoints)} />
          <Meta
            label="Source → Derived"
            value={`${humanize(run.summary.source_bytes)} → ${humanize(run.summary.derived_bytes)}`}
          />
          <Meta
            label="Amplification"
            value={run.summary.amplification_ratio ? `${run.summary.amplification_ratio.toFixed(2)}x` : "—"}
          />
        </CardContent>
      </Card>

      {run.summary.frame_count > 0 && (
        <div className="flex flex-wrap gap-2">
          <ObjectOpenButton objectKey={run.manifest_key} label="Open run.json" icon={FileJson} />
          <ObjectOpenButton objectKey={indexKey} label="Open keypoints_index.jsonl" icon={Download} />
        </div>
      )}

      <section className="space-y-3">
        <h2 className="card-title">Skeleton overlays</h2>
        <OverlayGallery frames={run.frames} />
      </section>

      {run.frames.length > 0 && (
        <section className="space-y-3">
          <h2 className="card-title">Per-frame keypoints</h2>
          <Card>
            <CardContent className="p-0">
              <Table>
                <TableHeader>
                  <TableRow className="bg-muted/40 hover:bg-muted/40">
                    <TableHead className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                      Frame
                    </TableHead>
                    <TableHead className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                      Instances
                    </TableHead>
                    <TableHead className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                      Keypoints
                    </TableHead>
                    <TableHead className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                      Mean score
                    </TableHead>
                    <TableHead className="w-10" />
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {run.frames.map((f) => (
                    <TableRow key={f.frame} className="table-row-hover">
                      <TableCell className="font-mono text-xs">{f.frame}</TableCell>
                      <TableCell className="tabular-nums">{f.num_instances}</TableCell>
                      <TableCell className="tabular-nums">{f.num_keypoints}</TableCell>
                      <TableCell className="tabular-nums">{f.mean_score.toFixed(3)}</TableCell>
                      <TableCell>
                        {f.keypoints_key && (
                          <ObjectOpenButton
                            objectKey={f.keypoints_key}
                            label="JSON"
                            icon={FileJson}
                          />
                        )}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </CardContent>
          </Card>
        </section>
      )}

      <section className="space-y-3">
        <h2 className="card-title">Edit run</h2>
        <Card>
          <CardContent className="p-5">
            <EditRunForm run={run} />
          </CardContent>
        </Card>
      </section>
    </div>
  );
}

function humanize(bytes: number): string {
  const units = ["B", "KB", "MB", "GB", "TB"];
  let size = bytes;
  for (const unit of units) {
    if (Math.abs(size) < 1024) return `${size.toFixed(1)} ${unit}`;
    size /= 1024;
  }
  return `${size.toFixed(1)} PB`;
}
