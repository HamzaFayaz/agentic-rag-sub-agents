import { FileText } from "lucide-react";

type DocumentsEmptyStateProps = {
  onBrowse?: () => void;
};

export function DocumentsEmptyState({ onBrowse }: DocumentsEmptyStateProps) {
  return (
    <div className="flex flex-col items-center justify-center rounded-xl border border-dashed border-border bg-muted px-6 py-16 text-center">
      <div className="mb-4 flex h-14 w-14 items-center justify-center rounded-full bg-surface shadow-sm">
        <FileText className="h-7 w-7 text-muted-foreground" />
      </div>
      <h2 className="text-lg font-semibold text-foreground">No documents yet</h2>
      <p className="mt-2 max-w-sm text-sm text-muted-foreground">
        Upload text or PDF files to index them for retrieval-augmented chat.
        Supported formats: .txt, .md, .pdf.
      </p>
      {onBrowse && (
        <button
          type="button"
          onClick={onBrowse}
          className="mt-6 text-sm font-medium text-foreground underline-offset-4 hover:underline"
        >
          Upload your first document
        </button>
      )}
    </div>
  );
}
