"use client";

import { useMemo } from "react";
import { Bar, BarChart, CartesianGrid, XAxis, YAxis } from "recharts";
import { BarChart3 } from "lucide-react";
import {
  Card,
  CardAction,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  type ChartConfig,
  ChartContainer,
  ChartTooltip,
  ChartTooltipContent,
} from "@/components/ui/chart";
import { EmptyState } from "@/components/ui/empty-state";
import { ErrorState } from "@/components/ui/error-state";
import { Skeleton } from "@/components/ui/skeleton";
import { usePoseStats } from "@/lib/queries";

const chartConfig = {
  runs: { label: "Runs", color: "var(--chart-1)" },
} satisfies ChartConfig;

export function RunsActivityChart() {
  const { data: stats, isLoading, error, refetch } = usePoseStats();

  const data = useMemo(
    () =>
      (stats?.activity ?? []).map((d) => ({
        date: new Date(d.date + "T00:00:00").toLocaleDateString("en-US", {
          month: "short",
          day: "numeric",
        }),
        runs: d.runs,
      })),
    [stats],
  );

  const total = data.reduce((sum, d) => sum + d.runs, 0);

  return (
    <Card>
      <CardHeader className="border-b border-border py-4 px-5">
        <CardTitle className="card-title">Extraction Runs</CardTitle>
        <CardDescription className="text-xs">Runs created per day</CardDescription>
        <CardAction className="text-right self-center">
          {isLoading ? (
            <Skeleton className="ml-auto h-6 w-12" />
          ) : (
            <>
              <div className="text-[10px] font-semibold text-muted-foreground uppercase tracking-wider">
                Total
              </div>
              <div className="text-lg font-semibold tabular-nums tracking-tight leading-tight">
                {stats ? total : "-"}
              </div>
            </>
          )}
        </CardAction>
      </CardHeader>
      <CardContent className="p-5">
        {isLoading ? (
          <Skeleton className="h-[240px] w-full" />
        ) : error ? (
          <ErrorState error={error} onRetry={() => refetch()} />
        ) : data.length === 0 ? (
          <EmptyState
            icon={BarChart3}
            title="No runs yet"
            description="Create and execute an extraction run to see activity here."
          />
        ) : (
          <ChartContainer config={chartConfig} className="h-[240px] w-full">
            <BarChart data={data} margin={{ top: 8, right: 4, left: -16, bottom: 0 }}>
              <CartesianGrid vertical={false} strokeDasharray="3 3" stroke="var(--border)" />
              <XAxis dataKey="date" tickLine={false} axisLine={false} tickMargin={10} fontSize={11} />
              <YAxis allowDecimals={false} tickLine={false} axisLine={false} tickMargin={6} fontSize={11} width={28} />
              <ChartTooltip cursor={{ fill: "var(--accent-subtle)" }} content={<ChartTooltipContent />} />
              <Bar dataKey="runs" fill="var(--color-runs)" radius={[4, 4, 0, 0]} animationDuration={500} />
            </BarChart>
          </ChartContainer>
        )}
      </CardContent>
    </Card>
  );
}
