"use client";

import { useState } from "react";
import { Plus, X } from "lucide-react";

import { Button } from "@/components/ui/button";
import { CreateRunForm } from "@/components/runs/run-form";
import { RunsList } from "@/components/runs/runs-list";

export default function RunsPage() {
  const [showForm, setShowForm] = useState(false);

  return (
    <div className="space-y-8">
      <div className="animate-fade-in flex flex-wrap items-start justify-between gap-4 border-b border-border pb-5">
        <div className="min-w-0">
          <h1 className="page-title">Extraction Runs</h1>
          <p className="mt-1.5 max-w-prose text-sm text-muted-foreground">
            Create, execute, and manage MMPose keypoint-extraction runs. Each run
            reads a session&apos;s frames and writes keypoints, overlays, and a
            dataset manifest to Backblaze B2.
          </p>
        </div>
        <Button size="sm" className="h-8 shrink-0" onClick={() => setShowForm((v) => !v)}>
          {showForm ? (
            <>
              <X className="h-3.5 w-3.5" />
              Close
            </>
          ) : (
            <>
              <Plus className="h-3.5 w-3.5" />
              New run
            </>
          )}
        </Button>
      </div>

      {showForm && (
        <div className="animate-fade-in-up">
          <CreateRunForm onCreated={() => setShowForm(false)} />
        </div>
      )}

      <div className="animate-fade-in-up stagger-2">
        <RunsList />
      </div>
    </div>
  );
}
