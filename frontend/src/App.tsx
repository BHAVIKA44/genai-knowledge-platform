import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Toaster, toast } from "sonner";
import { useState } from "react";
import {
  decideContributorReview,
  getContributorReview,
  getDocument,
  uploadDocument,
} from "./api/documents";
import { EditorialFooter, EditorialHero, KnowledgeStory, ProductHeader } from "./features/landing";
import { KnowledgeSearch } from "./features/search/KnowledgeSearch";
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
      <section className="workspace-section" aria-labelledby="workspace-heading">
        <div className="workspace-heading">
          <p className="section-kicker">Learn and contribute</p>
          <h2 id="workspace-heading">Learn from the community. Contribute to it.</h2>
        </div>
        <div className="workspace-grid">
          <section className="workspace-column" id="search" aria-labelledby="learn-heading">
            <div className="workspace-column-heading">
              <p className="section-kicker">Learn</p>
              <h3 id="learn-heading">Discover trusted GenAI knowledge</h3>
              <p>
                Search reviewed notes, papers, guides, and practical learning resources shared by
                the community.
              </p>
            </div>
            <KnowledgeSearch />
          </section>
          <section className="workspace-column" id="add-knowledge" aria-labelledby="share-heading">
            <div className="workspace-column-heading">
              <p className="section-kicker">Share</p>
              <h3 id="share-heading">Add what you have learned</h3>
              <p>
                Share useful GenAI material and help others learn from resources, explanations, and
                ideas worth keeping.
              </p>
            </div>
            <KnowledgeUploadPanel
              onSubmit={(file, title) => upload.mutate({ file, title })}
              isSubmitting={upload.isPending}
            />
          </section>
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
      <EditorialFooter />
    </main>
  );
}
