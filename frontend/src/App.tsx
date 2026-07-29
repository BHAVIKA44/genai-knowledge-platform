import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Toaster, toast } from "sonner";
import { useRef, useState } from "react";
import {
  decideContributorReview,
  getContributorReview,
  getDocument,
  uploadDocument,
} from "./api/documents";
import { EditorialHero, KnowledgeStory, ProductHeader } from "./features/landing";
import { KnowledgeSearch } from "./features/search/KnowledgeSearch";
import { SearchTerminalVisual } from "./features/search/SearchTerminalVisual";
import { DocumentOutcome } from "./features/upload/DocumentOutcome";
import { KnowledgeUploadPanel } from "./features/upload/KnowledgeUploadPanel";

const finalStates = [
  "APPROVED",
  "CONTRIBUTOR_REVIEW_REQUIRED",
  "ADMIN_REVIEW_REQUIRED",
  "REJECTED",
  "FAILED",
];

export default function App() {
  const queryClient = useQueryClient();
  const [documentId, setDocumentId] = useState<string | null>(null);
  const [uploadResetKey, setUploadResetKey] = useState(0);
  const [decisionAction, setDecisionAction] = useState<"ACCEPT" | "DECLINE" | null>(null);
  const [decisionConfirmation, setDecisionConfirmation] = useState<string | null>(null);
  const uploadInFlight = useRef(false);
  const decisionInFlight = useRef(false);
  const upload = useMutation({
    mutationFn: ({ file, title }: { file: File; title: string }) => uploadDocument(file, title),
    onSuccess: (document) => {
      setDocumentId(document.id);
      toast.success("Your resource is now being reviewed.");
    },
    onError: (error) => toast.error(error.message),
    onSettled: () => {
      uploadInFlight.current = false;
    },
  });
  const document = useQuery({
    queryKey: ["document", documentId],
    queryFn: () => getDocument(documentId ?? ""),
    enabled: Boolean(documentId),
    refetchInterval: (query) =>
      finalStates.includes(query.state.data?.status ?? "") ? false : 1000,
  });
  const review = useQuery({
    queryKey: ["contributor-review", documentId],
    queryFn: () => getContributorReview(documentId ?? ""),
    enabled: document.data?.status === "CONTRIBUTOR_REVIEW_REQUIRED",
  });
  const decision = useMutation({
    mutationFn: (action: "ACCEPT" | "DECLINE") => decideContributorReview(documentId ?? "", action),
    onSuccess: async (updated) => {
      queryClient.setQueryData(["document", documentId], updated);
      await queryClient.invalidateQueries({ queryKey: ["document", documentId] });
      queryClient.removeQueries({ queryKey: ["contributor-review", documentId] });
      const confirmation =
        updated.status === "APPROVED"
          ? "Resource added to your knowledge base."
          : "Resource was not added.";
      setDecisionConfirmation(confirmation);
      setUploadResetKey((current) => current + 1);
      toast.success(confirmation);
    },
    onError: (error) => toast.error(error.message),
    onSettled: () => {
      decisionInFlight.current = false;
      setDecisionAction(null);
    },
  });

  const isProcessing =
    upload.isPending || (document.data != null && !finalStates.includes(document.data.status));

  function submitUpload(file: File, title: string) {
    if (uploadInFlight.current) return;
    uploadInFlight.current = true;
    setDecisionConfirmation(null);
    setDocumentId(null);
    upload.mutate({ file, title });
  }

  function decideReview(action: "ACCEPT" | "DECLINE") {
    if (decisionInFlight.current) return;
    decisionInFlight.current = true;
    setDecisionAction(action);
    decision.mutate(action);
  }

  function resetUpload() {
    setDocumentId(null);
    setDecisionConfirmation(null);
    setUploadResetKey((current) => current + 1);
  }

  function clearPreviousOutcome() {
    upload.reset();
    setDocumentId(null);
    setDecisionConfirmation(null);
  }

  return (
    <main className="app-shell">
      <Toaster theme="dark" position="top-right" />
      <ProductHeader />
      <EditorialHero />
      <KnowledgeStory />
      <section
        className="workspace-section workspace-search-section"
        id="search"
        aria-labelledby="learn-heading"
      >
        <div className="search-discovery-layout">
          <div className="workspace-column">
            <div className="workspace-column-heading">
              <h3 id="learn-heading">Discover trusted GenAI knowledge</h3>
            </div>
            <KnowledgeSearch />
          </div>
          <SearchTerminalVisual />
        </div>
      </section>
      <section
        className="workspace-section workspace-upload-section"
        id="add-knowledge"
        aria-labelledby="share-heading"
      >
        <div className="workspace-column">
          <div className="workspace-column-heading">
            <h3 id="share-heading">Add what you have learned</h3>
          </div>
          <KnowledgeUploadPanel
            onSubmit={submitUpload}
            onFileSelected={clearPreviousOutcome}
            isSubmitting={upload.isPending}
            error={upload.isError ? upload.error.message : null}
            resetKey={uploadResetKey}
          />
          {isProcessing && (
            <p className="review-status-message" role="status" aria-live="polite">
              Reviewing your resource. This may take a few seconds to a few minutes depending on the
              document size.
            </p>
          )}
          {decisionConfirmation && (
            <p className="decision-confirmation" role="status" aria-live="polite">
              {decisionConfirmation}
            </p>
          )}
        </div>
        {document.data && (
          <DocumentOutcome
            document={document.data}
            review={
              document.data.status === "CONTRIBUTOR_REVIEW_REQUIRED" ? review.data : undefined
            }
            onDecision={decideReview}
            isDeciding={decision.isPending}
            decisionAction={decisionAction}
            onRetry={document.data.status === "FAILED" ? resetUpload : undefined}
          />
        )}
        {document.isError && (
          <p className="safe-error" role="alert">
            We could not refresh this review. Please try again.
          </p>
        )}
      </section>
    </main>
  );
}
