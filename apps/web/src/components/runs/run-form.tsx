"use client";

import { useRouter } from "next/navigation";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Form,
  FormControl,
  FormDescription,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "@/components/ui/form";
import { useCreateRun, useSessions, useUpdateRun } from "@/lib/queries";
import type { RunRecord } from "@mmpose-video-keypoint-extraction/shared";

const MODELS = ["human", "wholebody", "hand", "human3d"] as const;
const DEVICES = ["auto", "cpu", "cuda", "mps"] as const;

// CREATE-only safe-default hints (shown as FormDescription, never an autofill button).
const MODEL_HINTS: Record<(typeof MODELS)[number], string> = {
  human: "17 COCO body keypoints, CPU-friendly, recommended default",
  wholebody: "133 keypoints (body + feet + face + hands)",
  hand: "21 hand keypoints",
  human3d: "3D lifted keypoints",
};

const createSchema = z.object({
  label: z.string().min(1, "Give the run a label").max(120),
  session: z.string().min(1, "Pick a session to extract from"),
  model: z.enum(MODELS),
  device: z.enum(DEVICES),
  kpt_thr: z.coerce.number().min(0, "0–1").max(1, "0–1"),
});
type CreateValues = z.input<typeof createSchema>;

export function CreateRunForm({ onCreated }: { onCreated?: () => void }) {
  const router = useRouter();
  const { data: sessions = [], isLoading } = useSessions();
  const createRun = useCreateRun();

  const form = useForm<CreateValues>({
    resolver: zodResolver(createSchema),
    defaultValues: {
      label: "",
      session: "",
      model: "human",
      device: "auto",
      kpt_thr: 0.3,
    },
  });

  const onSubmit = form.handleSubmit((values) => {
    createRun.mutate(
      {
        label: values.label,
        session: values.session,
        model: values.model,
        device: values.device,
        kpt_thr: Number(values.kpt_thr),
      },
      {
        onSuccess: (run) => {
          toast.success("Run created", { description: "Execute it to extract keypoints." });
          onCreated?.();
          router.push(`/runs/${run.id}`);
        },
        onError: (e) => toast.error("Could not create run", { description: e.message }),
      },
    );
  });

  const noSessions = !isLoading && sessions.length === 0;

  return (
    <Card>
      <CardHeader className="border-b border-border py-4 px-5">
        <CardTitle className="card-title">New extraction run</CardTitle>
      </CardHeader>
      <CardContent className="p-5">
        {noSessions ? (
          <p className="text-sm text-muted-foreground">
            No ingested sessions yet. Ingest frames first (Ingest tab or{" "}
            <code>pnpm run seed</code>), then create a run.
          </p>
        ) : (
          <Form {...form}>
            <form onSubmit={onSubmit} className="space-y-5">
              <FormField
                control={form.control}
                name="session"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Session</FormLabel>
                    <Select onValueChange={field.onChange} value={field.value}>
                      <FormControl>
                        <SelectTrigger className="w-full">
                          <SelectValue placeholder="Select a session" />
                        </SelectTrigger>
                      </FormControl>
                      <SelectContent>
                        {sessions.map((s) => (
                          <SelectItem key={s.session} value={s.session}>
                            {s.session} ({s.frame_count} frames)
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                    <FormDescription>
                      The source session is fixed once the run is created — a
                      re-config is a new run.
                    </FormDescription>
                    <FormMessage />
                  </FormItem>
                )}
              />

              <FormField
                control={form.control}
                name="label"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Label</FormLabel>
                    <FormControl>
                      <Input placeholder="e.g. Squat form, session A" {...field} />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />

              <FormField
                control={form.control}
                name="model"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Model</FormLabel>
                    <Select onValueChange={field.onChange} value={field.value}>
                      <FormControl>
                        <SelectTrigger className="w-full">
                          <SelectValue />
                        </SelectTrigger>
                      </FormControl>
                      <SelectContent>
                        {MODELS.map((m) => (
                          <SelectItem key={m} value={m}>
                            {m}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                    <FormDescription>
                      {field.value} — {MODEL_HINTS[field.value as (typeof MODELS)[number]]}
                    </FormDescription>
                    <FormMessage />
                  </FormItem>
                )}
              />

              <div className="grid gap-5 sm:grid-cols-2">
                <FormField
                  control={form.control}
                  name="device"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Device</FormLabel>
                      <Select onValueChange={field.onChange} value={field.value}>
                        <FormControl>
                          <SelectTrigger className="w-full">
                            <SelectValue />
                          </SelectTrigger>
                        </FormControl>
                        <SelectContent>
                          {DEVICES.map((d) => (
                            <SelectItem key={d} value={d}>
                              {d}
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                      <FormDescription>auto → CUDA if present, else CPU.</FormDescription>
                      <FormMessage />
                    </FormItem>
                  )}
                />

                <FormField
                  control={form.control}
                  name="kpt_thr"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Keypoint threshold</FormLabel>
                      <FormControl>
                        <Input
                          type="number"
                          min={0}
                          max={1}
                          step={0.05}
                          className="font-mono tabular-nums"
                          {...field}
                        />
                      </FormControl>
                      <FormDescription>
                        Keypoint confidence cutoff, 0–1. Default 0.3.
                      </FormDescription>
                      <FormMessage />
                    </FormItem>
                  )}
                />
              </div>

              <div className="flex justify-end">
                <Button type="submit" disabled={createRun.isPending}>
                  {createRun.isPending ? "Creating…" : "Create run"}
                </Button>
              </div>
            </form>
          </Form>
        )}
      </CardContent>
    </Card>
  );
}

const editSchema = z.object({
  label: z.string().min(1, "Give the run a label").max(120),
  notes: z.string().max(1000).optional(),
  tags: z.string().optional(),
});
type EditValues = z.infer<typeof editSchema>;

export function EditRunForm({ run }: { run: RunRecord }) {
  const updateRun = useUpdateRun(run.id);
  const form = useForm<EditValues>({
    resolver: zodResolver(editSchema),
    defaultValues: {
      label: run.label,
      notes: run.notes ?? "",
      tags: (run.tags ?? []).join(", "),
    },
  });

  const onSubmit = form.handleSubmit((values) => {
    if (!form.formState.isDirty) return; // no-op when unchanged
    updateRun.mutate(
      {
        label: values.label,
        notes: values.notes ?? "",
        tags: (values.tags ?? "")
          .split(",")
          .map((t) => t.trim())
          .filter(Boolean),
      },
      {
        onSuccess: () => {
          toast.success("Run updated");
          form.reset(values);
        },
        onError: (e) => toast.error("Could not update run", { description: e.message }),
      },
    );
  });

  return (
    <Form {...form}>
      <form onSubmit={onSubmit} className="space-y-4">
        <FormField
          control={form.control}
          name="label"
          render={({ field }) => (
            <FormItem>
              <FormLabel>Label</FormLabel>
              <FormControl>
                <Input {...field} />
              </FormControl>
              <FormMessage />
            </FormItem>
          )}
        />
        <FormField
          control={form.control}
          name="notes"
          render={({ field }) => (
            <FormItem>
              <FormLabel>Notes</FormLabel>
              <FormControl>
                <Textarea className="resize-none" {...field} />
              </FormControl>
              <FormMessage />
            </FormItem>
          )}
        />
        <FormField
          control={form.control}
          name="tags"
          render={({ field }) => (
            <FormItem>
              <FormLabel>Tags</FormLabel>
              <FormControl>
                <Input placeholder="comma, separated, tags" {...field} />
              </FormControl>
              <FormDescription>The source session cannot be changed here.</FormDescription>
              <FormMessage />
            </FormItem>
          )}
        />
        <div className="flex justify-end">
          <Button type="submit" disabled={updateRun.isPending || !form.formState.isDirty}>
            {updateRun.isPending ? "Saving…" : "Save changes"}
          </Button>
        </div>
      </form>
    </Form>
  );
}
