import type {
  Architecture,
  ChatResponse,
  IndexJob,
  Repository,
} from "./types";

const BASE =
  process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000/api/v1";

async function req<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...(init?.headers ?? {}) },
    cache: "no-store",
  });
  if (!res.ok) {
    let detail = res.statusText;
    try {
      detail = (await res.json()).detail ?? detail;
    } catch {
      /* ignore */
    }
    throw new Error(detail);
  }
  if (res.status === 204) return undefined as T;
  return res.json() as Promise<T>;
}

export const api = {
  listRepos: () => req<Repository[]>("/repositories"),
  addRepo: (repo: string) =>
    req<Repository>("/repositories", {
      method: "POST",
      body: JSON.stringify({ repo }),
    }),
  getRepo: (id: string) => req<Repository>(`/repositories/${id}`),
  getStatus: (id: string) => req<IndexJob>(`/repositories/${id}/status`),
  getArchitecture: (id: string) =>
    req<Architecture>(`/repositories/${id}/architecture`),
  deleteRepo: (id: string) =>
    req<void>(`/repositories/${id}`, { method: "DELETE" }),
  chat: (id: string, question: string) =>
    req<ChatResponse>(`/repositories/${id}/chat`, {
      method: "POST",
      body: JSON.stringify({ question, top_k: 8 }),
    }),
};
