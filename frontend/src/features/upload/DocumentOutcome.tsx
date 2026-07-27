import { AnimatePresence, motion, useReducedMotion } from "framer-motion";
import { Check, ChevronRight, Clock3, FileText } from "lucide-react";
import type { ReactNode } from "react";
import type {
  ContributorReviewDetails,
  GroundedClaimVerification,
  KnowledgeDocument,
} from "../../api/documents";

type Props = {
  document: KnowledgeDocument;
  review?: ContributorReviewDetails;
  onDecision?: (action: "ACCEPT" | "DECLINE") => void;
  isDeciding?: boolean;
};

type Outcome = {
  title: string;
  description: string;
  tone: "approved" | "review" | "attention" | "rejected" | "failed" | "working";
};

const outcomes: Record<KnowledgeDocument["status"], Outcome> = {
  UPLOADED: {
    title: "Your resource is in review",
    description: "We’ve received it and are preparing to understand the content.",
    tone: "working",
  },
  PROCESSING: {
    title: "We’re reviewing your content",
    description: "Reading carefully. No rubber stamps here.",
    tone: "working",
  },
  VALIDATING: {
    title: "We’re preparing your decision",
    description: "Checking clarity, relevance, and what may need more attention.",
    tone: "working",
  },
  APPROVED: {
    title: "Added to your knowledge base",
    description: "This resource is ready to find when you search your trusted knowledge.",
    tone: "approved",
  },
  CONTRIBUTOR_REVIEW_REQUIRED: {
    title: "Your review is needed",
    description: "A small decision from you will help finish this resource’s review.",
    tone: "review",
  },
  ADMIN_REVIEW_REQUIRED: {
    title: "Needs further review",
    description: "This resource needs a closer look before it can be added to the knowledge base.",
    tone: "attention",
  },
  REJECTED: {
    title: "Not added to your knowledge base",
    description: "This resource was kept out so your library stays useful and trustworthy.",
    tone: "rejected",
  },
  FAILED: {
    title: "We could not complete the review",
    description:
      "Please try again shortly. Your resource has not been added to the knowledge base.",
    tone: "failed",
  },
};

const verificationLabels: Record<GroundedClaimVerification["verdict"], string> = {
  SUPPORTED: "Supported",
  PARTIALLY_SUPPORTED: "Partially supported",
  NOT_SUPPORTED: "Not supported",
  INSUFFICIENT_EVIDENCE: "Not enough evidence",
};

const progress = [
  ["Resource received", "received"],
  ["Understanding the content", "processing"],
  ["Reviewing clarity and relevance", "validating"],
  ["Preparing the decision", "decision"],
  ["Adding approved knowledge", "approved"],
] as const;

function progressState(status: KnowledgeDocument["status"], stage: (typeof progress)[number][1]) {
  const index = progress.findIndex(([, id]) => id === stage);
  const activeIndex =
    status === "UPLOADED" ? 0 : status === "PROCESSING" ? 1 : status === "VALIDATING" ? 2 : 4;
  if (
    ["CONTRIBUTOR_REVIEW_REQUIRED", "ADMIN_REVIEW_REQUIRED", "REJECTED", "FAILED"].includes(status)
  ) {
    return index < 4 ? "complete" : "skipped";
  }
  if (index < activeIndex) return "complete";
  if (index === activeIndex) return status === "APPROVED" ? "complete" : "active";
  return "pending";
}

export function DocumentOutcome({ document, review, onDecision, isDeciding }: Props) {
  const reducedMotion = useReducedMotion();
  const outcome = outcomes[document.status];
  const final = !["UPLOADED", "PROCESSING", "VALIDATING"].includes(document.status);
  const informationalFindings = document.validation_findings.filter(
    (finding) => finding.severity === "INFO",
  );
  const actionableFindings = document.validation_findings.filter(
    (finding) => finding.severity !== "INFO",
  );

  return (
    <motion.section
      className={`decision-report tone-${outcome.tone}`}
      aria-live="polite"
      initial={{ opacity: 0, y: reducedMotion ? 0 : 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: reducedMotion ? 0 : 0.35 }}
    >
      <header className="decision-hero">
        <div>
          <p className="report-label">{final ? "Review complete" : "Review in progress"}</p>
          <h2>{outcome.title}</h2>
          <p>{outcome.description}</p>
        </div>
        <div className="document-meta">
          <FileText size={16} aria-hidden="true" />
          <span>{document.source_filename}</span>
        </div>
      </header>

      {!final && <ReviewProgress status={document.status} />}

      <AnimatePresence mode="wait">
        {final && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ duration: reducedMotion ? 0 : 0.3 }}
          >
            {document.analysis && (
              <ReportSection title="What this resource covers">
                <p className="report-summary">{document.analysis.summary}</p>
                {document.analysis.topics.length > 0 && (
                  <div className="topic-list" aria-label="Topics in this resource">
                    {document.analysis.topics.map((topic) => (
                      <span key={topic}>{topic}</span>
                    ))}
                  </div>
                )}
              </ReportSection>
            )}

            {informationalFindings.length > 0 && (
              <ReportSection title="What we found">
                <FindingsSection findings={informationalFindings} />
              </ReportSection>
            )}

            {actionableFindings.length > 0 && (
              <ReportSection title="What needs attention">
                <p className="report-intro">
                  These are the points that influenced the decision for this resource.
                </p>
                <FindingsSection findings={actionableFindings} compact />
              </ReportSection>
            )}

            {document.analysis?.claims.length ? (
              <ReportSection title="Important ideas">
                <div className="idea-list">
                  {document.analysis.claims.map((claim) => (
                    <article key={claim.text}>
                      <p>{claim.text}</p>
                    </article>
                  ))}
                </div>
              </ReportSection>
            ) : null}

            {document.grounded_claim_verifications?.length ? (
              <ReportSection title="External references">
                <EvidenceSection verifications={document.grounded_claim_verifications} />
              </ReportSection>
            ) : null}

            {review && onDecision ? (
              <ContributorReviewPanel
                review={review}
                onDecision={onDecision}
                isDeciding={isDeciding}
              />
            ) : (
              <ReportSection title="What happens next">
                <p className="report-intro">
                  {document.status === "APPROVED"
                    ? "This resource is now available when you search your trusted knowledge."
                    : document.status === "ADMIN_REVIEW_REQUIRED"
                      ? "No action is needed from you right now. This resource will stay out of search until a closer review is complete."
                      : document.status === "REJECTED"
                        ? "You can return with a clearer or more relevant GenAI learning resource whenever you are ready."
                        : "Please try this resource again shortly. It has not been added to search."}
                </p>
              </ReportSection>
            )}
          </motion.div>
        )}
      </AnimatePresence>
    </motion.section>
  );
}

function ReviewProgress({ status }: { status: KnowledgeDocument["status"] }) {
  return (
    <section className="review-progress" aria-label="Resource review progress">
      <div className="progress-heading">
        <Clock3 size={16} aria-hidden="true" />
        <p>We’ll update this report as the review moves forward.</p>
      </div>
      <ol>
        {progress.map(([label, id]) => {
          const state = progressState(status, id);
          return (
            <li className={`progress-${state}`} key={id}>
              <span aria-hidden="true">{state === "complete" ? <Check size={12} /> : ""}</span>
              <p>{label}</p>
              {state === "active" && <small>In progress</small>}
            </li>
          );
        })}
      </ol>
    </section>
  );
}

function ReportSection({ title, children }: { title: string; children: ReactNode }) {
  return (
    <section className="report-section">
      <h3>{title}</h3>
      {children}
    </section>
  );
}

function FindingsSection({
  findings,
  compact = false,
}: {
  findings: KnowledgeDocument["validation_findings"];
  compact?: boolean;
}) {
  return (
    <div className={`findings-list${compact ? " compact" : ""}`}>
      {findings.map((finding) => (
        <article key={finding.code}>
          <span
            className={`finding-marker severity-${finding.severity.toLowerCase()}`}
            aria-hidden="true"
          />
          <div>
            <h4>{finding.title}</h4>
            <p>{finding.explanation}</p>
            {finding.suggested_action && <small>{finding.suggested_action}</small>}
          </div>
        </article>
      ))}
    </div>
  );
}

function EvidenceSection({ verifications }: { verifications: GroundedClaimVerification[] }) {
  return (
    <div className="evidence-list">
      {verifications.map((verification) => (
        <article key={`${verification.claim}-${verification.verified_at}`}>
          <p className="evidence-claim">{verification.claim}</p>
          <p className="evidence-verdict">{verificationLabels[verification.verdict]}</p>
          <p className="evidence-explanation">{verification.explanation}</p>
          {verification.evidence_sources.length > 0 && (
            <details>
              <summary>View supporting sources ({verification.evidence_sources.length})</summary>
              <ul>
                {verification.evidence_sources.map((source) => (
                  <li key={source.url}>
                    <a href={source.url} target="_blank" rel="noreferrer noopener">
                      {source.title || source.domain || "Reference source"}
                    </a>
                    {source.domain && <span>{source.domain}</span>}
                    {source.summary && <p>{source.summary}</p>}
                  </li>
                ))}
              </ul>
            </details>
          )}
        </article>
      ))}
    </div>
  );
}

function ContributorReviewPanel({
  review,
  onDecision,
  isDeciding,
}: {
  review: ContributorReviewDetails;
  onDecision: (action: "ACCEPT" | "DECLINE") => void;
  isDeciding?: boolean;
}) {
  return (
    <section className="contributor-review-panel" aria-labelledby="review-panel-heading">
      <p className="report-label">A shared decision</p>
      <h3 id="review-panel-heading">We need your input.</h3>
      <p>{review.finding.explanation}</p>
      <div className="suggestion-comparison">
        <div>
          <span>Current value</span>
          <strong>{review.finding.original_value || "No title provided"}</strong>
        </div>
        <ChevronRight aria-hidden="true" />
        <div>
          <span>Suggested improvement</span>
          <strong>{review.finding.suggested_value}</strong>
        </div>
      </div>
      <div className="review-actions">
        <button
          className="button button-primary"
          disabled={isDeciding}
          onClick={() => onDecision("ACCEPT")}
        >
          {isDeciding ? "Saving your decision…" : "Accept suggestion and add"}
        </button>
        <button
          className="button button-quiet"
          disabled={isDeciding}
          onClick={() => onDecision("DECLINE")}
        >
          Do not add this resource
        </button>
      </div>
    </section>
  );
}
