const apiUrl = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

export type DocumentStatus =
  | "UPLOADED"
  | "PROCESSING"
  | "VALIDATING"
  | "APPROVED"
  | "CONTRIBUTOR_REVIEW_REQUIRED"
  | "ADMIN_REVIEW_REQUIRED"
  | "REJECTED"
  | "FAILED";

export type Finding = {
  code: string;
  severity: "INFO" | "WARNING" | "BLOCKING";
  title: string;
  explanation: string;
  suggested_action: string | null;
};

export type KnowledgeDocument = {
  id: string;
  title: string;
  source_filename: string;
  document_type: "MARKDOWN" | "TEXT" | "PDF";
  status: DocumentStatus;
  detected_topics: string[];
  validation_findings: Finding[];
  created_at: string;
  updated_at: string;
};

type ApiError = {
  error: { code: string; message: string; action: string | null; request_id: string };
};

async function request<T>(input: RequestInfo, init?: RequestInit): Promise<T> {
  const response = await fetch(`${apiUrl}${input}`, init);
  if (!response.ok) {
    const payload = (await response.json()) as ApiError;
    throw new Error(
      payload.error.action
        ? `${payload.error.message} ${payload.error.action}`
        : payload.error.message,
    );
  }
  return (await response.json()) as T;
}

export function uploadDocument(file: File, title: string): Promise<KnowledgeDocument> {
  const form = new FormData();
  form.append("file", file);
  if (title.trim()) form.append("title", title.trim());
  return request<KnowledgeDocument>("/api/documents", { method: "POST", body: form });
}

export function getDocument(id: string): Promise<KnowledgeDocument> {
  return request<KnowledgeDocument>(`/api/documents/${id}`);
}
