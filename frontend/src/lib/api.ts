const API_BASE =
  (process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000") + "/api";

const WS_BASE =
  process.env.NEXT_PUBLIC_WS_URL ?? "ws://localhost:8000";

export { WS_BASE };

export async function uploadDocument(
  file: File
): Promise<{ doc_id: string; filename: string; status: string }> {
  const formData = new FormData();
  formData.append("file", file);

  const res = await fetch(`${API_BASE}/upload`, {
    method: "POST",
    body: formData,
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "Upload failed" }));
    throw new Error(err.detail || "Upload failed");
  }

  return res.json();
}

export async function sendChatMessage(
  query: string,
  documentId: string,
  history: { role: string; content: string }[] = []
): Promise<{ answer: string; document_id: string }> {
  const res = await fetch(`${API_BASE}/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ query, document_id: documentId, history }),
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: `HTTP ${res.status}` }));
    throw new Error(err.detail || `HTTP ${res.status}`);
  }

  return res.json();
}

export async function getDocuments(): Promise<{
  documents: { id: string; filename: string; status: string }[];
}> {
  const res = await fetch(`${API_BASE}/documents`);
  if (!res.ok) throw new Error("Failed to fetch documents");
  return res.json();
}
