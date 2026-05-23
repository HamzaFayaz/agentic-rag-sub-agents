export function apiBaseUrl(): string {
  const configured = import.meta.env.VITE_API_URL;
  if (configured) {
    return configured.replace(/\/$/, "");
  }
  return "";
}

export type DocumentRecord = {
  id: string;
  filename: string;
  status: "pending" | "processing" | "ready" | "failed";
  byte_size: number;
  error_message: string | null;
  created_at: string;
};

function authHeaders(accessToken: string): HeadersInit {
  return { Authorization: `Bearer ${accessToken}` };
}

export async function listDocuments(
  accessToken: string,
): Promise<DocumentRecord[]> {
  const response = await fetch(`${apiBaseUrl()}/api/documents`, {
    headers: authHeaders(accessToken),
  });
  if (!response.ok) {
    throw new Error(await response.text());
  }
  return (await response.json()) as DocumentRecord[];
}

export async function uploadDocument(
  accessToken: string,
  file: File,
): Promise<DocumentRecord> {
  const formData = new FormData();
  formData.append("file", file);

  const response = await fetch(`${apiBaseUrl()}/api/documents/upload`, {
    method: "POST",
    headers: authHeaders(accessToken),
    body: formData,
  });
  if (!response.ok) {
    throw new Error(await response.text());
  }
  return (await response.json()) as DocumentRecord;
}

export async function deleteDocument(
  accessToken: string,
  documentId: string,
): Promise<void> {
  const response = await fetch(`${apiBaseUrl()}/api/documents/${documentId}`, {
    method: "DELETE",
    headers: authHeaders(accessToken),
  });
  if (!response.ok && response.status !== 204) {
    throw new Error(await response.text());
  }
}

export const MAX_UPLOAD_BYTES = 10_485_760;
export const ACCEPTED_FILE_TYPES = ".txt,.md,.pdf";
