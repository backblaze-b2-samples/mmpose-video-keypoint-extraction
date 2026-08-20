"use client";

import { ArrowRight, HardDrive } from "lucide-react";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { ErrorState } from "@/components/ui/error-state";
import { usePoseStats } from "@/lib/queries";

/**
 * The headline B2 story: every source frame fans out into keypoint JSON + an
 * overlay image, so the derived footprint dwarfs the source. This card makes
 * that write-amplification visible.
 */
export function AmplificationCard() {
  const { data: stats, isLoading, error, refetch } = usePoseStats();

  return (
    <Card>
      <CardHeader className="border-b border-border py-4 px-5">
        <CardTitle className="card-title flex items-center gap-2">
          <HardDrive className="h-4 w-4 text-muted-foreground" />
          Write Amplification on B2
        </CardTitle>
        <CardDescription className="text-xs">
          Source frames vs derived artifacts (keypoint JSON + overlays + manifest)
        </CardDescription>
      </CardHeader>
      <CardContent className="p-5">
        {isLoading ? (
          <Skeleton className="h-20 w-full" />
        ) : error ? (
          <ErrorState error={error} onRetry={() => refetch()} />
        ) : (
          <div className="flex flex-wrap items-center gap-4">
            <div>
              <div className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">
                Source
              </div>
              <div className="text-2xl font-semibold tabular-nums">
                {stats?.source_bytes_human ?? "0.0 B"}
              </div>
            </div>
            <ArrowRight className="h-5 w-5 text-muted-foreground" />
            <div>
              <div className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">
                Derived on B2
              </div>
              <div className="text-2xl font-semibold tabular-nums text-[var(--brand-b2)]">
                {stats?.derived_bytes_human ?? "0.0 B"}
              </div>
            </div>
            <div className="ml-auto rounded-lg bg-muted px-4 py-2 text-center">
              <div className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">
                Ratio
              </div>
              <div className="text-2xl font-semibold tabular-nums">
                {stats?.amplification_ratio
                  ? `${stats.amplification_ratio.toFixed(2)}x`
                  : "—"}
              </div>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
