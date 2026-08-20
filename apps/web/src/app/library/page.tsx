import { LibraryExplorer } from "@/components/library/library-explorer";

export default function LibraryPage() {
  return (
    <div className="space-y-8">
      <div className="animate-fade-in border-b border-border pb-5">
        <h1 className="page-title">Library</h1>
        <p className="mt-1.5 max-w-prose text-sm text-muted-foreground">
          A scoped view of everything this sample has written to Backblaze B2,
          grouped by pipeline stage: ingested sessions and extraction runs. For
          the whole bucket, use the Files tab.
        </p>
      </div>
      <div className="animate-fade-in-up stagger-2">
        <LibraryExplorer />
      </div>
    </div>
  );
}
