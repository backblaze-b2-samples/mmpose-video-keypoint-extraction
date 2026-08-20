"use client";

import Link from "next/link";
import { Activity, Trash2 } from "lucide-react";
import { toast } from "sonner";

import { Button, buttonVariants } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Skeleton } from "@/components/ui/skeleton";
import { EmptyState } from "@/components/ui/empty-state";
import { ErrorState } from "@/components/ui/error-state";
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
import { useDeleteRun, useRuns } from "@/lib/queries";
import { formatDate } from "@/lib/utils";
import type { RunRecord } from "@mmpose-video-keypoint-extraction/shared";

function DeleteRunButton({ run }: { run: RunRecord }) {
  const deleteRun = useDeleteRun();
  return (
    <AlertDialog>
      <AlertDialogTrigger asChild>
        <Button variant="ghost" size="icon" aria-label={`Delete ${run.label}`}>
          <Trash2 className="h-4 w-4 text-muted-foreground" />
        </Button>
      </AlertDialogTrigger>
      <AlertDialogContent>
        <AlertDialogHeader>
          <AlertDialogTitle>Delete this run?</AlertDialogTitle>
          <AlertDialogDescription>
            This permanently deletes every artifact under this run&apos;s prefix
            on B2 — keypoint JSON, overlays, and the manifest. Ingested source
            frames are not touched. This cannot be undone.
          </AlertDialogDescription>
        </AlertDialogHeader>
        <AlertDialogFooter>
          <AlertDialogCancel>Cancel</AlertDialogCancel>
          <AlertDialogAction
            onClick={() =>
              deleteRun.mutate(run.id, {
                onSuccess: () => toast.success("Run deleted"),
                onError: (e) =>
                  toast.error("Could not delete run", { description: e.message }),
              })
            }
            className={buttonVariants({ variant: "destructive" })}
          >
            Delete run
          </AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  );
}

export function RunsList() {
  const { data: runs = [], isLoading, error, refetch } = useRuns();

  if (isLoading) {
    return (
      <div className="space-y-3">
        {Array.from({ length: 4 }).map((_, i) => (
          <Skeleton key={i} className="h-12 w-full" />
        ))}
      </div>
    );
  }
  if (error) return <ErrorState error={error} onRetry={() => refetch()} />;
  if (runs.length === 0) {
    return (
      <EmptyState
        icon={Activity}
        title="No runs yet"
        description="Create an extraction run above to pull keypoints from a session."
      />
    );
  }

  return (
    <Card>
      <CardContent className="p-0">
        <Table>
          <TableHeader>
            <TableRow className="bg-muted/40 hover:bg-muted/40">
              <TableHead className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                Label
              </TableHead>
              <TableHead className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                Session
              </TableHead>
              <TableHead className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                Model
              </TableHead>
              <TableHead className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                Frames
              </TableHead>
              <TableHead className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                Created
              </TableHead>
              <TableHead className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                Status
              </TableHead>
              <TableHead className="w-10" />
            </TableRow>
          </TableHeader>
          <TableBody>
            {runs.map((run) => (
              <TableRow key={run.id} className="table-row-hover">
                <TableCell className="font-medium">
                  <Link
                    href={`/runs/${run.id}`}
                    className="rounded-sm underline-offset-4 hover:underline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring"
                  >
                    {run.label}
                  </Link>
                </TableCell>
                <TableCell className="text-muted-foreground">{run.session}</TableCell>
                <TableCell className="font-mono text-xs text-muted-foreground">
                  {run.model}
                </TableCell>
                <TableCell className="tabular-nums text-muted-foreground">
                  {run.summary.frame_count || "—"}
                </TableCell>
                <TableCell className="text-muted-foreground whitespace-nowrap">
                  {formatDate(run.created_at)}
                </TableCell>
                <TableCell>
                  <RunStatusBadge status={run.status} />
                </TableCell>
                <TableCell>
                  <DeleteRunButton run={run} />
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </CardContent>
    </Card>
  );
}
