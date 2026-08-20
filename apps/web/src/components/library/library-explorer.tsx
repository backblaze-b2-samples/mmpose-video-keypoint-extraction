"use client";

import { Boxes, FolderTree } from "lucide-react";
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from "@/components/ui/accordion";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { EmptyState } from "@/components/ui/empty-state";
import { ErrorState } from "@/components/ui/error-state";
import { useLibrary } from "@/lib/queries";
import { SAMPLE_PREFIX } from "@/lib/sample-prefix";

const STAGE_COPY: Record<string, string> = {
  sessions: "Ingested source frames, grouped by session under sessions/<session>/frames/.",
  runs: "Extraction-run manifests plus derived keypoint JSON, overlay PNGs, and keypoints_index.jsonl under runs/<run_id>/.",
};

export function LibraryExplorer() {
  const { data, isLoading, error, refetch } = useLibrary();

  if (isLoading) return <Skeleton className="h-64 w-full" />;
  if (error) return <ErrorState error={error} onRetry={() => refetch()} />;
  if (!data) return null;

  const empty = data.total_objects === 0;

  return (
    <Card>
      <CardHeader className="border-b border-border py-4 px-5">
        <CardTitle className="card-title flex items-center gap-2">
          <FolderTree className="h-4 w-4 text-muted-foreground" />
          <code className="text-sm">{SAMPLE_PREFIX}</code>
        </CardTitle>
        <p className="text-xs text-muted-foreground">
          {data.total_objects} objects · {data.total_bytes_human} — scoped to this
          sample&apos;s prefix (the Files tab browses the whole bucket).
        </p>
      </CardHeader>
      <CardContent className="p-3">
        {empty ? (
          <EmptyState
            icon={Boxes}
            title="Nothing here yet"
            description="Ingest a session and run an extraction to populate the library."
          />
        ) : (
          <Accordion type="multiple" className="w-full">
            {data.stages.map((stage) => (
              <AccordionItem key={stage.stage} value={stage.stage}>
                <AccordionTrigger className="px-2">
                  <span className="flex w-full items-center justify-between pr-3">
                    <span className="font-medium capitalize">{stage.stage}</span>
                    <span className="text-xs tabular-nums text-muted-foreground">
                      {stage.object_count} objects · {stage.total_bytes_human}
                    </span>
                  </span>
                </AccordionTrigger>
                <AccordionContent className="px-2 text-sm text-muted-foreground">
                  {STAGE_COPY[stage.stage] ?? "Objects under this stage prefix."}
                </AccordionContent>
              </AccordionItem>
            ))}
          </Accordion>
        )}
      </CardContent>
    </Card>
  );
}
