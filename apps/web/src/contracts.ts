export type RecordData = Record<string, unknown>;
export interface Session {
  user: { id: string; name: string };
  workspace: { id: string; name: string };
  role: string;
  csrf_token: string;
  mode: string;
  providers: Record<string, boolean>;
}
export interface Claim {
  id?: string;
  text: string;
  subject: string;
  geography: string;
  period: string;
  stage: string;
  measure: string;
  value?: string | number;
  unit?: string;
  currency?: "INR" | "USD" | "EUR" | "GBP";
  denominator?: string;
  attribution?: string;
}
export interface Source {
  id: string;
  url: string;
  title: string;
  status: string;
  text?: string;
  metadata?: RecordData;
  metadata_json?: RecordData;
  content_hash?: string;
}
export interface Evidence {
  id: string;
  claim_id: string;
  source_id: string;
  relation: string;
  quote: string;
  anchor: { start: number; end: number; page?: number };
  comparison: RecordData;
  rationale: string;
  metadata?: RecordData;
  override?: RecordData;
}
export interface Payload {
  claims: Claim[];
  projects: RecordData[];
  evidence: Evidence[];
  sources: Source[];
  ledger: {
    stages: RecordData[];
    funding: RecordData[];
    metrics: RecordData[];
    derived: RecordData[];
    gaps: RecordData[];
  };
  notes: RecordData[];
  conclusion: string;
  lineage: RecordData[];
}
export interface Run {
  costs?: {
    total_usd: number;
    uncertain_reserved_usd: number;
    providers: Record<
      string,
      {
        attempts: number;
        usd: number;
        prompt_tokens: number;
        completion_tokens: number;
        reported_usage_calls: number;
      }
    >;
  };
  id: string;
  case_id: string;
  base_revision: number;
  state: string;
  mode: string;
  plan: RecordData;
  budget: Record<string, number>;
  usage: Record<string, number | boolean>;
  results: Payload;
  error?: string;
  checkpoint?: RecordData;
  events?: {
    seq: number;
    type: string;
    payload: RecordData;
    created_at: string;
  }[];
}
export interface CaseItem {
  id: string;
  title: string;
  original_claim: string;
  revision: number;
  state: string;
  tags: string[];
  archived: boolean;
  created_at: string;
  updated_at: string;
  assignee_id?: string;
}
export interface CaseDetail extends CaseItem {
  payload: Payload;
  latest_run: Run | null;
  review_requests: RecordData[];
}
export interface Plan {
  id: string;
  scope_hash: string;
  queries: (string | RecordData)[];
  budget: Record<string, number>;
}
export interface Review {
  id: string;
  case_id: string;
  revision: number;
  status: string;
  conclusion: string;
  submitted_by?: string;
  payload?: Payload;
  case?: CaseDetail;
  created_at?: string;
}
export interface Member {
  id?: string;
  user_id: string;
  name?: string;
  role: string;
}
