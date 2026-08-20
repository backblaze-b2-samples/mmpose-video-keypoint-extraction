"use client";

import Image from "next/image";
import { Skeleton } from "@/components/ui/skeleton";
import { usePreviewUrl } from "@/lib/queries";
import type { FrameKeypoints } from "@mmpose-video-keypoint-extraction/shared";

function OverlayThumb({ frame }: { frame: FrameKeypoints }) {
  const { data, isLoading } = usePreviewUrl(frame.overlay_key ?? undefined, !!frame.overlay_key);

  return (
    <figure className="space-y-1">
      <div className="relative aspect-video overflow-hidden rounded-md border border-border bg-muted/30">
        {isLoading || !data?.url ? (
          <Skeleton className="absolute inset-0" />
        ) : (
          <Image
            src={data.url}
            alt={`Skeleton overlay for ${frame.frame}`}
            fill
            unoptimized
            sizes="(max-width: 768px) 50vw, 25vw"
            className="object-contain"
          />
        )}
      </div>
      <figcaption className="flex items-center justify-between text-[11px] text-muted-foreground">
        <span className="truncate font-mono">{frame.frame}</span>
        <span className="tabular-nums">
          {frame.num_instances}p · {frame.num_keypoints}kp
        </span>
      </figcaption>
    </figure>
  );
}

export function OverlayGallery({ frames }: { frames: FrameKeypoints[] }) {
  const withOverlays = frames.filter((f) => f.overlay_key);
  if (withOverlays.length === 0) {
    return (
      <p className="text-sm text-muted-foreground">
        No overlays yet — execute the run to generate skeleton overlays.
      </p>
    );
  }
  return (
    <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
      {withOverlays.map((frame) => (
        <OverlayThumb key={frame.frame} frame={frame} />
      ))}
    </div>
  );
}
