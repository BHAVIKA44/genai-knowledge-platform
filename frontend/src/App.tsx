import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Toaster, toast } from "sonner";
import {
  decideContributorReview,
  getContributorReview,
  getDocument,
  uploadDocument,
} from "./api/documents";
import { DocumentOutcome } from "./features/upload/DocumentOutcome";
import { KnowledgeUploadPanel } from "./features/upload/KnowledgeUploadPanel";
import { KnowledgeSearch } from "./features/search/KnowledgeSearch";
import { useState } from "react";

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
      toast.success("Your resource has been accepted for processing.");
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
        updated.status === "APPROVED" ? "Change accepted. Document approved." : "Upload rejected.",
      );
    },
    onError: (error) => toast.error(error.message),
  });
  return (
    <main className="min-h-screen bg-[#090b10] px-5 py-16 text-slate-100">
      <Toaster theme="dark" />
      <div className="mx-auto max-w-3xl">
        <p className="text-sm font-medium uppercase tracking-[0.2em] text-sky-200">
          GenAI knowledge platform
        </p>
        <h1 className="mt-4 text-4xl font-semibold tracking-tight sm:text-5xl">
          Knowledge that earns its place.
        </h1>
        <p className="mt-4 max-w-2xl text-lg text-slate-400">
          Contribute a GenAI learning resource. It will be extracted, checked, and only then
          considered for the shared knowledge base.
        </p>
        <div className="mt-10 grid gap-6">
          <KnowledgeUploadPanel
            onSubmit={(file, title) => upload.mutate({ file, title })}
            isSubmitting={upload.isPending}
          />
          {document.data && (
            <DocumentOutcome
              document={document.data}
              review={review.data}
              onDecision={(action) => decision.mutate(action)}
              isDeciding={decision.isPending}
            />
          )}
          {document.isError && (
            <p className="rounded-xl border border-red-300/20 bg-red-300/10 p-4 text-red-100">
              We could not refresh this result. Please try again.
            </p>
          )}
          <KnowledgeSearch />
        </div>
      </div>
    </main>
  );
}
