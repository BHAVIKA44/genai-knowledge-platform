import { useQuery } from "@tanstack/react-query";
import { useState, type FormEvent, type KeyboardEvent } from "react";
import { ArrowUpRight, Search } from "lucide-react";
import ReactMarkdown from "react-markdown";
import { answerKnowledge } from "../../api/search";

export function KnowledgeSearch() {
  const [query, setQuery] = useState("");
  const [submittedQuery, setSubmittedQuery] = useState<string | null>(null);
  const search = useQuery({
    queryKey: ["knowledge-search", submittedQuery],
    queryFn: () => answerKnowledge(submittedQuery ?? ""),
    enabled: Boolean(submittedQuery),
  });
  const results = search.data?.results ?? [];

  function submitQuery() {
    const normalizedQuery = query.trim();
    if (normalizedQuery) setSubmittedQuery(normalizedQuery);
  }

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    submitQuery();
  }

  function submitFromKeyboard(event: KeyboardEvent<HTMLInputElement>) {
    if (event.key !== "Enter") return;
    event.preventDefault();
    submitQuery();
  }

  return (
    <div className="trusted-search">
      <form className="trusted-search-form" onSubmit={submit}>
        <label htmlFor="knowledge-search" className="sr-only">
          Search trusted knowledge
        </label>
        <Search size={21} aria-hidden="true" />
        <input
          id="knowledge-search"
          value={query}
          onKeyDown={submitFromKeyboard}
          onChange={(event) => {
            const nextQuery = event.target.value;
            setQuery(nextQuery);
            if (!nextQuery.trim()) setSubmittedQuery(null);
          }}
          placeholder="Search Generative AI topics, concepts, or techniques"
        />
        <button
          type="submit"
          disabled={search.isFetching || !query.trim()}
          className="button button-primary"
        >
          {search.isFetching ? "Searching…" : "Search"}
        </button>
      </form>

      {!submittedQuery && (
        <div className="search-empty-state">
          <Search size={20} aria-hidden="true" />
          <p>Your reviewed resources will appear here when they are ready to search.</p>
        </div>
      )}
      {search.isFetching && (
        <div className="search-loading" role="status">
          <p>Searching your knowledge…</p>
          <span />
          <span />
          <span />
        </div>
      )}
      {search.isError && (
        <p className="safe-error" role="alert">
          We could not search your knowledge right now. Please try again.
        </p>
      )}
      {search.isSuccess && results.length === 0 && (
        <div className="search-empty-state search-no-results">
          <p>{search.data.answer}</p>
          <span>Try a broader topic or add a resource to your knowledge base.</span>
        </div>
      )}
      {search.isSuccess && results.length > 0 && (
        <>
          <section
            className="search-answer"
            aria-live="polite"
            aria-label="Answer from trusted knowledge"
          >
            <p className="search-answer-label">Answer from reviewed knowledge</p>
            <ReactMarkdown>{search.data.answer}</ReactMarkdown>
          </section>
          <ol className="trusted-results" aria-label="Supporting reviewed resources">
            {results.map((result) => (
              <li key={result.document_id}>
                <article>
                  <div className="result-topline">
                    <span>Supporting resource</span>
                    <ArrowUpRight size={15} aria-hidden="true" />
                  </div>
                  <h3>{result.title}</h3>
                  <p>{result.snippet}</p>
                </article>
              </li>
            ))}
          </ol>
        </>
      )}
    </div>
  );
}
