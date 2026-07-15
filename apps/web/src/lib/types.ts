export interface User {
  id: string;
  login: string;
  name: string | null;
  email: string | null;
  avatar_url: string | null;
  llm_provider: string;
  embedding_provider: string;
}

export interface AuthConfig {
  github_enabled: boolean;
  dev_login_enabled: boolean;
}

export interface ProviderStatus {
  llm_provider: string;
  embedding_provider: string;
  configured_keys: Record<string, string>;
}

export interface Repository {
  id: string;
  full_name: string;
  clone_url: string;
  default_branch: string;
  status: string;
  file_count: number;
  chunk_count: number;
  readme_summary: string | null;
  error: string | null;
  created_at: string;
}

export interface IndexJob {
  id: string;
  repository_id: string;
  status: string;
  stage: string | null;
  progress: number;
  error: string | null;
}

export interface Citation {
  path: string;
  start_line: number;
  end_line: number;
  kind: string;
  score: number;
}

export interface ChatResponse {
  answer: string;
  citations: Citation[];
  provider: string;
}

export interface Issue {
  id: string;
  github_number: number;
  title: string;
  state: string;
  labels: string[];
  author: string | null;
  comments_count: number;
  html_url: string;
  github_updated_at: string | null;
  analysis_status: string;
  complexity_score: number | null;
  complexity_level: string | null;
  estimated_hours: string | null;
  suitability_score: number | null;
}

export interface IssueDetail extends Issue {
  body: string | null;
  affected_files: Citation[];
  required_knowledge: string[];
  strategy: string | null;
  risks: string[];
  analysis_provider: string | null;
}

export interface ArchModule {
  name: string;
  file_count: number;
  roles: string[];
  top_extensions: string[];
}

export interface Architecture {
  summary: string;
  modules: ArchModule[];
  layers: { role: string; file_count: number }[];
  entry_points: string[];
  languages: { extension: string; file_count: number }[];
}
