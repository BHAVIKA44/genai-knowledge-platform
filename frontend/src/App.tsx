import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Toaster, toast } from "sonner";
import { useState } from "react";
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
  const upload = useMutation({
    mutationFn: ({ file, title }: { file: File; title: string }) => uploadDocument(file, title),
    onSuccess: (document) => {
      setDocumentId(document.id);
      toast.success("Your resource is now being reviewed.");
    },
    onError: (error) => toast.error(error.message),
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
    onSuccess: (updated) => {
      queryClient.setQueryData(["document", documentId], updated);
      queryClient.invalidateQueries({ queryKey: ["contributor-review", documentId] });
      toast.success(
        updated.status === "APPROVED"
          ? "Suggestion accepted. Your resource is now in the knowledge base."
          : "This resource was not added.",
      );
    },
    onError: (error) => toast.error(error.message),
  });
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
            onSubmit={(file, title) => upload.mutate({ file, title })}
            isSubmitting={upload.isPending}
          />
        </div>
        {document.data && (
          <DocumentOutcome
            document={document.data}
            review={review.data}
            onDecision={(action) => decision.mutate(action)}
            isDeciding={decision.isPending}
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
