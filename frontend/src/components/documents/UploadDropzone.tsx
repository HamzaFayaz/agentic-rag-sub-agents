import { useCallback, useRef, useState } from "react";
import { FileUp, Loader2 } from "lucide-react";

import { Button } from "@/components/ui/button";
import {
  ACCEPTED_FILE_TYPES,
  MAX_UPLOAD_BYTES,
  type IngestAction,
} from "@/lib/api";
import { cn } from "@/lib/utils";

type UploadDropzoneProps = {
  uploading: boolean;
  onUpload: (file: File) => Promise<IngestAction | void>;
};

const INGEST_MESSAGES: Record<IngestAction, string> = {
  created: "Uploaded — indexing started.",
  updated: "Updated — re-indexing in progress.",
  unchanged: "Already indexed — no changes detected.",
};

function formatBytes(bytes: number): string {
  if (bytes < 1024 * 1024) return `${Math.round(bytes / 1024)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export function UploadDropzone({ uploading, onUpload }: UploadDropzoneProps) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [dragOver, setDragOver] = useState(false);
  const [localError, setLocalError] = useState<string | null>(null);
  const [outcome, setOutcome] = useState<string | null>(null);

  const handleFile = useCallback(
    async (file: File) => {
      setLocalError(null);
      setOutcome(null);
      const ext = file.name.slice(file.name.lastIndexOf(".")).toLowerCase();
      if (![".txt", ".md", ".pdf"].includes(ext)) {
        setLocalError("Only .txt, .md, and .pdf files are supported.");
        return;
      }
      if (file.size > MAX_UPLOAD_BYTES) {
        setLocalError(`File exceeds ${formatBytes(MAX_UPLOAD_BYTES)} limit.`);
        return;
      }
      try {
        const action = await onUpload(file);
        if (action) {
          setOutcome(INGEST_MESSAGES[action]);
        }
      } catch {
        // Parent hook surfaces API errors
      }
    },
    [onUpload],
  );

  const onDrop = useCallback(
    (event: React.DragEvent) => {
      event.preventDefault();
      setDragOver(false);
      if (uploading) return;
      const file = event.dataTransfer.files[0];
      if (file) void handleFile(file);
    },
    [handleFile, uploading],
  );

  return (
    <div className="space-y-2">
      <div
        onDragOver={(e) => {
          e.preventDefault();
          if (!uploading) setDragOver(true);
        }}
        onDragLeave={() => setDragOver(false)}
        onDrop={onDrop}
        className={cn(
          "flex flex-col items-center justify-center rounded-xl border-2 border-dashed px-6 py-10 text-center transition-colors",
          dragOver
            ? "border-ring bg-muted"
            : "border-border bg-surface",
          uploading && "pointer-events-none opacity-60",
        )}
      >
        {uploading ? (
          <Loader2 className="mb-3 h-8 w-8 animate-spin text-muted-foreground" />
        ) : (
          <FileUp className="mb-3 h-8 w-8 text-muted-foreground" />
        )}
        <p className="text-sm font-medium text-foreground">
          Drag and drop a file here
        </p>
        <p className="mt-1 text-xs text-muted-foreground">
          {ACCEPTED_FILE_TYPES} · max {formatBytes(MAX_UPLOAD_BYTES)}
        </p>
        <Button
          type="button"
          variant="outline"
          size="sm"
          className="mt-4"
          disabled={uploading}
          onClick={() => inputRef.current?.click()}
        >
          Browse files
        </Button>
        <input
          ref={inputRef}
          type="file"
          accept={ACCEPTED_FILE_TYPES}
          className="hidden"
          disabled={uploading}
          onChange={(e) => {
            const file = e.target.files?.[0];
            if (file) void handleFile(file);
            e.target.value = "";
          }}
        />
      </div>
      {outcome && (
        <p className="text-sm text-emerald-600 dark:text-emerald-400" role="status">
          {outcome}
        </p>
      )}
      {localError && (
        <p className="text-sm text-red-600 dark:text-red-400" role="alert">
          {localError}
        </p>
      )}
    </div>
  );
}
