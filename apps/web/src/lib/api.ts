import type {
  Architecture,
  AuthConfig,
  ChatResponse,
  Contribution,
  GitHubAppInfo,
  GitHubInstallation,
  IndexJob,
  Insights,
  Issue,
  IssueDetail,
  Opportunity,
  Preferences,
  ProviderStatus,
  PublishPreview,
  Repository,
  User,
} from "./types";

const BASE =
  process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000/api/v1";

export const GITHUB_LOGIN_URL = `${BASE}/auth/github/login`;

export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
  }
}

async function req<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...(init?.headers ?? {}) },
    cache: "no-store",
    credentials: "include", // send/receive the session cookie
  });
  if (!res.ok) {
    let detail = res.statusText;
    try {
      detail = (await res.json()).detail ?? detail;
    } catch {
      /* ignore */
    }
    throw new ApiError(res.status, detail);
  }
  if (res.status === 204) return undefined as T;
  return res.json() as Promise<T>;
}

export const api = {
  // --- auth ---
  authConfig: () => req<AuthConfig>("/auth/config"),
  me: () => req<User>("/auth/me"),
  devLogin: (login: string) =>
    req<User>("/auth/dev-login", {
      method: "POST",
      body: JSON.stringify({ login }),
    }),
  githubCallback: (code: string, state: string) =>
    req<User>("/auth/github/callback", {
      method: "POST",
      body: JSON.stringify({ code, state }),
    }),
  logout: () => req<{ ok: boolean }>("/auth/logout", { method: "POST" }),

  // --- discovery ---
  getPreferences: () => req<Preferences>("/discovery/preferences"),
  updatePreferences: (prefs: Preferences) =>
    req<Preferences>("/discovery/preferences", {
      method: "PUT",
      body: JSON.stringify(prefs),
    }),
  getOpportunities: () => req<Opportunity[]>("/discovery/opportunities"),
  getInsights: () => req<Insights>("/discovery/insights"),

  // --- github app ---
  githubApp: () => req<GitHubAppInfo>("/github/app"),
  githubInstallations: () => req<GitHubInstallation[]>("/github/installations"),

  // --- providers ---
  getProviders: () => req<ProviderStatus>("/providers"),
  updateProviderSettings: (llm_provider: string, embedding_provider: string) =>
    req<ProviderStatus>("/providers/settings", {
      method: "PUT",
      body: JSON.stringify({ llm_provider, embedding_provider }),
    }),
  setProviderKey: (provider: string, api_key: string) =>
    req<ProviderStatus>("/providers/keys", {
      method: "PUT",
      body: JSON.stringify({ provider, api_key }),
    }),
  deleteProviderKey: (provider: string) =>
    req<ProviderStatus>(`/providers/keys/${provider}`, { method: "DELETE" }),

  // --- repos ---
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
  // --- issues ---
  syncIssues: (repoId: string) =>
    req<{ synced: number }>(`/repositories/${repoId}/issues/sync`, {
      method: "POST",
    }),
  listIssues: (repoId: string) => req<Issue[]>(`/repositories/${repoId}/issues`),
  getIssue: (repoId: string, number: number) =>
    req<IssueDetail>(`/repositories/${repoId}/issues/${number}`),
  analyzeIssue: (repoId: string, number: number) =>
    req<IssueDetail>(`/repositories/${repoId}/issues/${number}/analyze`, {
      method: "POST",
    }),

  // --- contributions ---
  startContribution: (repoId: string, number: number) =>
    req<Contribution>(`/repositories/${repoId}/issues/${number}/contribute`, {
      method: "POST",
    }),
  getContribution: (repoId: string, taskId: string) =>
    req<Contribution>(`/repositories/${repoId}/contributions/${taskId}`),
  reviewContribution: (
    repoId: string,
    taskId: string,
    approve: boolean,
    note?: string
  ) =>
    req<Contribution>(`/repositories/${repoId}/contributions/${taskId}/review`, {
      method: "POST",
      body: JSON.stringify({ approve, note: note ?? null }),
    }),
  publishPreview: (repoId: string, taskId: string, headRepo?: string) =>
    req<PublishPreview>(
      `/repositories/${repoId}/contributions/${taskId}/publish-preview` +
        (headRepo ? `?head_repo=${encodeURIComponent(headRepo)}` : "")
    ),
  publishContribution: (
    repoId: string,
    taskId: string,
    headRepo?: string
  ) =>
    req<Contribution>(`/repositories/${repoId}/contributions/${taskId}/publish`, {
      method: "POST",
      body: JSON.stringify({ confirm: true, head_repo: headRepo ?? null }),
    }),

  chat: (id: string, question: string) =>
    req<ChatResponse>(`/repositories/${id}/chat`, {
      method: "POST",
      body: JSON.stringify({ question, top_k: 8 }),
    }),
};
