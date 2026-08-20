import Link from "next/link";
import { Plus } from "lucide-react";

import { Button } from "@/components/ui/button";
import { PoseStatsCards } from "@/components/dashboard/pose-stats-cards";
import { AmplificationCard } from "@/components/dashboard/amplification-card";
import { RunsActivityChart } from "@/components/dashboard/runs-activity-chart";
import { RecentRunsTable } from "@/components/dashboard/recent-runs-table";

export default function DashboardPage() {
  return (
    <div className="space-y-8">
      <div className="animate-fade-in border-b border-border pb-5 flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="page-title">Dashboard</h1>
          <p className="text-sm text-muted-foreground mt-1.5">
            Pose keypoint extraction across your video libraries, stored on
            Backblaze B2.
          </p>
        </div>
        <Button asChild size="sm" className="h-8">
          <Link href="/runs">
            <Plus className="h-3.5 w-3.5" />
            New run
          </Link>
        </Button>
      </div>
      <PoseStatsCards />
      <div className="animate-fade-in-up stagger-2">
        <AmplificationCard />
      </div>
      <div className="grid gap-6 lg:grid-cols-2">
        <div className="animate-fade-in-up stagger-3">
          <RunsActivityChart />
        </div>
        <div className="animate-fade-in-up stagger-4">
          <RecentRunsTable />
        </div>
      </div>
    </div>
  );
}
