import type { ContributorReviewDetails, KnowledgeDocument } from "../../api/documents";

const labels: Record<KnowledgeDocument["status"], string> = {
  UPLOADED: "Upload accepted",
  PROCESSING: "Extracting content",
  VALIDATING: "Checking knowledge quality",
  APPROVED: "Approved for the knowledge base",
  CONTRIBUTOR_REVIEW_REQUIRED: "Your input is needed",
  ADMIN_REVIEW_REQUIRED: "Manual review required",
  REJECTED: "Not published",
  FAILED: "Processing could not finish",
};

type Props = {
  document: KnowledgeDocument;
  review?: ContributorReviewDetails;
  onDecision?: (action: "ACCEPT" | "DECLINE") => void;
  isDeciding?: boolean;
};

export function DocumentOutcome({ document, review, onDecision, isDeciding }: Props) {
  const finished = [
    "APPROVED",
    "CONTRIBUTOR_REVIEW_REQUIRED",
    "ADMIN_REVIEW_REQUIRED",
    "REJECTED",
    "FAILED",
  ].includes(document.status);
  return (
    <section aria-live="polite" className="rounded-3xl border border-white/10 bg-white/[0.03] p-6">
      <p className="text-sm font-medium uppercase tracking-[0.2em] text-sky-200">
        Knowledge quality
      </p>
      <h2 className="mt-2 text-2xl font-semibold">{labels[document.status]}</h2>
      <p className="mt-2 text-slate-400">
        {document.source_filename}
        {document.detected_topics.length ? ` · ${document.detected_topics.join(", ")}` : ""}
      </p>
      {!finished && (
        <p className="mt-6 text-sm text-slate-300">
          This may take a moment. We will update this result as each real stage completes.
        </p>
      )}
      <div className="mt-6 space-y-3">
        {document.validation_findings.map((finding) => (
          <article key={finding.code} className="rounded-xl border border-white/10 bg-black/20 p-4">
            <p className="font-medium text-white">{finding.title}</p>
            <p className="mt-1 text-sm text-slate-400">{finding.explanation}</p>
            {finding.suggested_action && (
              <p className="mt-2 text-sm text-sky-200">{finding.suggested_action}</p>
            )}
          </article>
        ))}
      </div>
      {review && onDecision && (
        <div className="mt-6 rounded-xl border border-sky-300/20 bg-sky-300/[0.04] p-4">
          <p className="font-medium text-white">Review the suggested change</p>
          <p className="mt-2 text-sm text-slate-400">
            Original value: {review.finding.original_value || "No title"}
          </p>
          <p className="mt-1 text-sm text-sky-100">
            Suggested value: {review.finding.suggested_value}
          </p>
          <div className="mt-4 flex gap-3">
            <button
              disabled={isDeciding}
              onClick={() => onDecision("ACCEPT")}
              className="rounded-lg bg-sky-300 px-3 py-2 text-sm font-semibold text-slate-950 disabled:opacity-50"
            >
              Accept change
            </button>
            <button
              disabled={isDeciding}
              onClick={() => onDecision("DECLINE")}
              className="rounded-lg border border-white/15 px-3 py-2 text-sm font-semibold text-white disabled:opacity-50"
            >
              Decline upload
            </button>
          </div>
        </div>
      )}
    </section>
  );
}
