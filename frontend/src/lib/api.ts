export function apiBaseUrl(): string {
  const configured = import.meta.env.VITE_API_URL;
  if (configured) {
    return configured.replace(/\/$/, "");
  }
  return "";
}
