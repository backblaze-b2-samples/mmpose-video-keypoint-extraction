import { UploadForm } from "@/components/upload/upload-form";

export default function IngestPage() {
  return (
    <div className="space-y-8">
      <div className="animate-fade-in border-b border-border pb-5">
        <h1 className="page-title">Ingest</h1>
        <p className="mt-1.5 max-w-prose text-sm text-muted-foreground text-pretty">
          Upload source frames or clips to Backblaze B2. For a ready-made demo
          session with real skeletons, run{" "}
          <code>pnpm run seed</code>, which decodes license-clean footage into a
          frame session and uploads it under{" "}
          <code>sessions/&lt;session&gt;/frames/</code>. Uploaded files here land
          in the bucket and are browsable in Files (up to 100 MB each).
        </p>
      </div>
      <div className="animate-fade-in-up stagger-2">
        <UploadForm />
      </div>
    </div>
  );
}
