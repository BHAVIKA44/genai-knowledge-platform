import { useMutation } from "@tanstack/react-query";
import { useState, type FormEvent } from "react";
import { ArrowUpRight, Search } from "lucide-react";
import { searchKnowledge } from "../../api/search";

export function KnowledgeSearch() {
  const [query, setQuery] = useState("");
  const search = useMutation({ mutationFn: searchKnowledge });
  const results = search.data ?? [];

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (query.trim()) search.mutate(query.trim());
  }

  return (
    <div className="trusted-search">
      <div className="search-heading">
        <p className="section-kicker">Your knowledge library</p>
        <h2 id="search-heading">
          Search what <em>you trust.</em>
        </h2>
        <p>Explore resources that have already been reviewed and accepted.</p>
      </div>
      <form className="trusted-search-form" onSubmit={submit}>
        <label htmlFor="knowledge-search" className="sr-only">
          Search trusted knowledge
        </label>
        <Search size={21} aria-hidden="true" />
        <input
          id="knowledge-search"
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          placeholder="Search Generative AI topics, concepts, or techniques"
        />
        <button disabled={search.isPending || !query.trim()} className="button button-primary">
          {search.isPending ? "Searching…" : "Search"}
        </button>
      </form>

      {search.isIdle && (
        <div className="search-empty-state">
          <Search size={20} aria-hidden="true" />
          <p>Your reviewed resources will appear here when they are ready to search.</p>
        </div>
      )}
      {search.isPending && (
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
          <p>No approved knowledge found.</p>
          <span>Try a broader topic or add a resource to your knowledge base.</span>
        </div>
      )}
      {results.length > 0 && (
        <ol className="trusted-results" aria-label="Trusted knowledge search results">
          {results.map((result) => (
            <li key={result.document_id}>
              <article>
                <div className="result-topline">
                  <span>Reviewed resource</span>
                  <ArrowUpRight size={15} aria-hidden="true" />
                </div>
                <h3>{result.title}</h3>
                <p>{result.snippet}</p>
              </article>
            </li>
          ))}
        </ol>
      )}
    </div>
  );
}
