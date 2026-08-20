"use client";

import { Activity, Boxes, Layers, TrendingUp } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { ErrorState } from "@/components/ui/error-state";
import { LoadingNotice } from "@/components/common/loading-notice";
import { usePoseStats } from "@/lib/queries";

export function PoseStatsCards() {
  const { data: stats, isLoading, error, refetch } = usePoseStats();

  if (error) {
    return (
      <Card>
        <CardContent className="p-0">
          <ErrorState error={error} onRetry={() => refetch()} />
        </CardContent>
      </Card>
    );
  }

  const ratio = stats?.amplification_ratio ?? 0;
  const cards = [
    { title: "Extraction Runs", value: stats?.total_runs ?? 0, icon: Activity },
    { title: "Frames Processed", value: stats?.frames_processed ?? 0, icon: Layers },
    { title: "Keypoints Extracted", value: stats?.total_keypoints ?? 0, icon: Boxes },
    {
      title: "Write Amplification",
      value: ratio ? `${ratio.toFixed(2)}x` : "—",
      icon: TrendingUp,
    },
  ];

  return (
    <>
      {isLoading && <LoadingNotice className="mb-3" subject="pose metrics" />}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {cards.map((card, i) => (
          <Card
            key={card.title}
            className={`card-hover animate-fade-in-up stagger-${i + 1}`}
          >
            <CardHeader className="flex flex-row items-center justify-between pt-4 pb-2 px-4 space-y-0">
              <CardTitle className="text-xs font-semibold text-muted-foreground">
                {card.title}
              </CardTitle>
              <div className="stat-icon-wrap">
                <card.icon className="h-4 w-4" />
              </div>
            </CardHeader>
            <CardContent className="pb-5 px-4">
              {isLoading ? (
                <Skeleton className="h-8 w-24" />
              ) : (
                <div className="stat-value">{card.value}</div>
              )}
            </CardContent>
          </Card>
        ))}
      </div>
    </>
  );
}
