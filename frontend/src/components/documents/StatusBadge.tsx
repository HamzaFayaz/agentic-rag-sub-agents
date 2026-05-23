import { Badge } from "@/components/ui/badge";
import type { DocumentRecord } from "@/lib/api";

type StatusBadgeProps = {
  status: DocumentRecord["status"];
};

const labels: Record<DocumentRecord["status"], string> = {
  pending: "Pending",
  processing: "Processing",
  ready: "Ready",
  failed: "Failed",
};

const variants: Record<
  DocumentRecord["status"],
  "secondary" | "warning" | "success" | "destructive"
> = {
  pending: "secondary",
  processing: "warning",
  ready: "success",
  failed: "destructive",
};

export function StatusBadge({ status }: StatusBadgeProps) {
  return <Badge variant={variants[status]}>{labels[status]}</Badge>;
}
