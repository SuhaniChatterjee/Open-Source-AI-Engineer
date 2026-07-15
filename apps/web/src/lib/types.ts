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
