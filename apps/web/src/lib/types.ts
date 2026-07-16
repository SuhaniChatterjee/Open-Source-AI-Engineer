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

export interface GitHubAppInfo {
  configured: boolean;
  install_url: string | null;
  app_slug: string | null;
}

export interface GitHubInstallation {
  installation_id: number;
  account_login: string;
  account_type: string | null;
  repository_selection: string | null;
  suspended: boolean;
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

export interface ProposedChange {
  path: string;
  action: string;
  original_content: string;
  new_content: string;
  diff: string;
  note: string | null;
}

export interface Contribution {
  id: string;
  repository_id: string;
  issue_id: string;
  issue_number: number | null;
  status: string;
  stage: string | null;
  category: string | null;
  is_safe_category: boolean;
  summary: string | null;
  plan: string[];
  proposed_changes: ProposedChange[];
  test_plan: string | null;
  risks: string[];
  confidence_score: number | null;
  confidence_rationale: string | null;
  guidance: string | null;
  commit_message: string | null;
  pr_title: string | null;
  pr_body: string | null;
  provider: string | null;
  reviewer_note: string | null;
  error: string | null;
  publish_status: string;
  branch_name: string | null;
  pr_number: number | null;
  pr_url: string | null;
  pr_head_repo: string | null;
  publish_error: string | null;
}

export interface PublishPreview {
  branch_name: string;
  base: string;
  head: string;
  files: string[];
  commit_message: string;
  pr_title: string;
  pr_body: string;
  head_repo: string;
  token_configured: boolean;
}

export interface Preferences {
  languages: string[];
  topics: string[];
  experience_level: string;
  labels: string[];
}

export interface Affinity {
  name: string;
  weight: number;
}

export interface Insights {
  languages: Affinity[];
  labels: Affinity[];
  topics: Affinity[];
  stats: Record<string, number>;
  suggestions: { languages: string[]; labels: string[] };
  has_history: boolean;
}

export interface Opportunity {
  repo_full_name: string;
  repo_url: string;
  number: number;
  title: string;
  html_url: string;
  labels: string[];
  comments: number;
  body_preview: string;
  created_at: string | null;
  updated_at: string | null;
  fit_score: number;
  reasons: string[];
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
