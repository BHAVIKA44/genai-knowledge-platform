const apiUrl = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

type ApiError = {
  error: { message: string; action: string | null };
};

export type SearchResult = {
  document_id: string;
  title: string;
  snippet: string;
  final_score: number;
};

export async function searchKnowledge(query: string): Promise<SearchResult[]> {
  const parameters = new URLSearchParams({ q: query });
  const response = await fetch(`${apiUrl}/search?${parameters}`);
  if (!response.ok) {
    const payload = (await response.json()) as ApiError;
    throw new Error(
      payload.error.action
        ? `${payload.error.message} ${payload.error.action}`
        : payload.error.message,
    );
  }
  return (await response.json()) as SearchResult[];
}
