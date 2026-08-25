// Types mirror the actual Pydantic schemas in
// src/contextflow/api/schemas/requests.py and the core models in
// src/contextflow/core/ — kept in sync by hand for now. If these drift
// from the Python side, that's a real bug to report/fix, not a design
// choice (see CONTRIBUTING.md).

export interface ContextObjectResponse {
  id: string;
  type: string;
  content: string;
  source: string;
  entities: string[];
  relationships: string[];
  metadata: Record<string, unknown>;
  permissions: string[];
  allowed_roles: string[];
  tenant_id: string | null;
  created_at: string;
  updated_at: string | null;
  freshness: number;
  confidence: number;
  trust: number;
}

export interface ConflictingClaim {
  claim_a: string;
  claim_b: string;
  source_a: string;
  source_b: string;
  resolution: string | null;
}

export interface ContextPackResponse {
  task: string;
  entity: string | null;
  facts: Record<string, unknown>[];
  people: Record<string, unknown>[];
  projects: Record<string, unknown>[];
  conversations: Record<string, unknown>[];
  documents: Record<string, unknown>[];
  decisions: Record<string, unknown>[];
  risks: Record<string, unknown>[];
  relationships: Record<string, unknown>[];
  sources: string[];
  conflicts: ConflictingClaim[];
  token_budget: number | null;
  tokens_used: number | null;
  confidence: number;
}

export interface TraceStage {
  name: string;
  count_in: number;
  count_out: number;
  duration_ms: number;
  details: Record<string, unknown>;
}

export interface ContextTraceResponse {
  id: string;
  query: string;
  stages: TraceStage[];
  total_duration_ms: number;
  final_confidence: number | null;
  final_tokens: number | null;
  created_at: number;
}

export interface MemoryEntryResponse {
  id: string;
  content: string;
  metadata: Record<string, unknown>;
  created_at: number;
}

export type MemoryScope = "session" | "user" | "agent" | "org";

export interface SearchOptions {
  limit?: number;
}

export interface ContextPackOptions {
  entity?: string;
  maxTokens?: number;
}

export interface TraceOptions {
  limit?: number;
}

export interface RecallOptions {
  query?: string;
  limit?: number;
}
