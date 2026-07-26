import { useMutation } from "@tanstack/react-query";
import { useState, type FormEvent } from "react";
import { searchKnowledge } from "../../api/search";

export function KnowledgeSearch() {
  const [query, setQuery] = useState("");
  const search = useMutation({ mutationFn: searchKnowledge });
  const results = [...(search.data ?? [])].sort(
    (left, right) => right.final_score - left.final_score,
  );

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (query.trim()) search.mutate(query.trim());
  }

  return (
    <section className="rounded-3xl border border-white/10 bg-white/[0.03] p-6">
      <p className="text-sm font-medium uppercase tracking-[0.2em] text-sky-200">
        Search knowledge
      </p>
      <h2 className="mt-2 text-2xl font-semibold">Find approved learning resources</h2>
      <form className="mt-5 flex flex-col gap-3 sm:flex-row" onSubmit={submit}>
        <input
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          className="min-w-0 flex-1 rounded-xl border border-white/10 bg-black/20 px-3 py-2 text-white outline-none focus:border-sky-300"
          placeholder="Search GenAI knowledge"
          aria-label="Search approved knowledge"
        />
        <button
          disabled={search.isPending || !query.trim()}
          className="rounded-xl bg-sky-300 px-5 py-2 font-semibold text-slate-950 transition hover:bg-sky-200 disabled:cursor-not-allowed disabled:opacity-50"
        >
          {search.isPending ? "Searching…" : "Search"}
        </button>
      </form>
      {search.isPending && (
        <p className="mt-4 text-sm text-slate-400" role="status">
          Searching approved knowledge…
        </p>
      )}
      {search.isError && (
        <p className="mt-4 rounded-xl border border-red-300/20 bg-red-300/10 p-4 text-sm text-red-100">
          {search.error.message}
        </p>
      )}
      {search.isSuccess && results.length === 0 && (
        <p className="mt-4 text-sm text-slate-400">No approved knowledge found.</p>
      )}
      {results.length > 0 && (
        <div className="mt-5 space-y-3">
          {results.map((result) => (
            <article
              key={result.document_id}
              className="rounded-xl border border-white/10 bg-black/20 p-4"
            >
              <div className="flex items-start justify-between gap-4">
                <h3 className="font-medium text-white">{result.title}</h3>
                <span className="shrink-0 text-sm text-sky-200">
                  {Math.round(result.final_score * 100)}%
                </span>
              </div>
              <p className="mt-2 text-sm leading-6 text-slate-400">{result.snippet}</p>
            </article>
          ))}
        </div>
      )}
    </section>
  );
}
