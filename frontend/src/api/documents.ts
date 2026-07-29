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
  original_value: string | null;
  suggested_value: string | null;
  admin_review_required: boolean;
};

export type AnalysisClaim = {
  text: string;
  confidence: number;
  is_time_sensitive: boolean;
  requires_external_verification: boolean;
};

export type DocumentAnalysis = {
  proposed_title: string | null;
  summary: string;
  topics: string[];
  claims: AnalysisClaim[];
  model: string;
  prompt_version: string;
  analyzed_at: string;
};

export type GroundedEvidenceSource = {
  title: string | null;
  url: string;
  domain: string | null;
  summary: string | null;
};

export type GroundedClaimVerification = {
  claim: string;
  verdict: "SUPPORTED" | "PARTIALLY_SUPPORTED" | "NOT_SUPPORTED" | "INSUFFICIENT_EVIDENCE";
  confidence: number;
  explanation: string;
  evidence_sources: GroundedEvidenceSource[];
  verified_at: string;
};

export type KnowledgeDocument = {
  id: string;
  title: string;
  source_filename: string;
  document_type: "MARKDOWN" | "TEXT" | "PDF";
  status: DocumentStatus;
  detected_topics: string[];
  validation_findings: Finding[];
  contributor_review_decision: string | null;
  analysis: DocumentAnalysis | null;
  grounded_claim_verifications: GroundedClaimVerification[] | null;
  created_at: string;
  updated_at: string;
};

type ApiError = {
  error: { code: string; message: string; action: string | null; request_id: string };
};

async function request<T>(input: RequestInfo, init?: RequestInit): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`${apiUrl}${input}`, init);
  } catch {
    throw new Error("We could not reach the service. Please try again.");
  }
  if (!response.ok) {
    let payload: ApiError;
    try {
      payload = (await response.json()) as ApiError;
    } catch {
      throw new Error("We could not finish that request. Please try again.");
    }
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

export type ContributorReviewDetails = { document: KnowledgeDocument; finding: Finding };

export function getContributorReview(id: string): Promise<ContributorReviewDetails> {
  return request<ContributorReviewDetails>(`/api/documents/${id}/contributor-review`);
}

export function decideContributorReview(
  id: string,
  action: "ACCEPT" | "DECLINE",
): Promise<KnowledgeDocument> {
  return request<KnowledgeDocument>(`/api/documents/${id}/contributor-review`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ action }),
  });
}
