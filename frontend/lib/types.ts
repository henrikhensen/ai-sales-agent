// Types mirror the backend Pydantic schemas exactly. Keep in sync with
// backend/agents/*/schemas.py and backend/api/v1/schemas/*.py.

export interface HealthComponent {
  status: "up" | "down";
}

export interface HealthResponse {
  status: "ok" | "degraded";
  service: string;
  environment: string;
  components: Record<string, HealthComponent>;
}

// -- Lead Research Agent ----------------------------------------------------

export interface LeadResearchRequest {
  company_name: string;
  website_url?: string | null;
  industry?: string | null;
  location?: string | null;
  notes?: string | null;
}

export interface LeadResearchResponse {
  company_name: string;
  website_url: string | null;
  industry: string | null;
  location: string | null;
  short_summary: string;
  target_customers: string[];
  likely_pain_points: string[];
  possible_sales_angles: string[];
  confidence_score: number;
  missing_information: string[];
  sources_used: string[];
}

// -- Company Intelligence Agent ----------------------------------------------

export interface CompanyIntelligenceRequest {
  company_name: string;
  website_url?: string | null;
  industry?: string | null;
  location?: string | null;
  company_description?: string | null;
  website_text?: string | null;
  known_products?: string[] | null;
  known_customers?: string[] | null;
  notes?: string | null;
}

export interface CompanyIntelligenceResponse {
  company_name: string;
  website_url: string | null;
  industry: string | null;
  location: string | null;
  business_summary: string;
  products_and_services: string[];
  target_segments: string[];
  likely_buyer_personas: string[];
  value_proposition: string[];
  positioning_summary: string;
  possible_competitive_context: string[];
  sales_relevance: string[];
  potential_business_challenges: string[];
  personalization_hooks: string[];
  missing_information: string[];
  sources_used: string[];
  confidence_score: number;
}

// -- Personalization Engine ---------------------------------------------------

export interface PersonalizationRequest {
  company_name: string;
  website_url?: string | null;
  industry?: string | null;
  location?: string | null;
  lead_summary?: string | null;
  company_intelligence_summary?: string | null;
  target_persona?: string | null;
  product_or_service_offered: string;
  value_proposition?: string | null;
  known_pain_points?: string[] | null;
  known_triggers?: string[] | null;
  notes?: string | null;
}

export interface PersonalizationResponse {
  company_name: string;
  website_url: string | null;
  industry: string | null;
  personalization_summary: string;
  relevant_observations: string[];
  possible_conversation_starters: string[];
  pain_point_angles: string[];
  value_arguments: string[];
  credibility_points: string[];
  objection_risks: string[];
  suggested_ctas: string[];
  do_not_use_claims: string[];
  missing_information: string[];
  sources_used: string[];
  confidence_score: number;
}

// -- Email Draft Agent --------------------------------------------------------

export type EmailTone = "professional" | "friendly" | "concise" | "consultative";

export interface EmailDraftRequest {
  company_name: string;
  website_url?: string | null;
  industry?: string | null;
  recipient_role?: string | null;
  recipient_name?: string | null;
  sender_name?: string | null;
  sender_company?: string | null;
  product_or_service_offered: string;
  personalization_summary?: string | null;
  relevant_observations?: string[] | null;
  pain_point_angles?: string[] | null;
  value_arguments?: string[] | null;
  credibility_points?: string[] | null;
  suggested_ctas?: string[] | null;
  tone?: EmailTone | null;
  language?: string | null;
  notes?: string | null;
}

export interface EmailDraftResponse {
  company_name: string;
  subject_lines: string[];
  email_body: string;
  alternative_openings: string[];
  alternative_ctas: string[];
  personalization_used: string[];
  claims_to_verify: string[];
  do_not_send_if: string[];
  compliance_notes: string[];
  missing_information: string[];
  confidence_score: number;
}

// -- Reply Analysis Agent ------------------------------------------------------

export type ReplyClassification =
  | "interested"
  | "meeting_request"
  | "question"
  | "objection"
  | "not_interested"
  | "out_of_office"
  | "unclear";

export type ReplySentiment = "positive" | "neutral" | "negative" | "unclear";
export type ReplyUrgency = "low" | "medium" | "high" | "unclear";

export interface ReplyAnalysisRequest {
  company_name: string;
  lead_name?: string | null;
  lead_role?: string | null;
  original_email_subject?: string | null;
  original_email_body?: string | null;
  reply_text: string;
  previous_context?: string | null;
  product_or_service_offered?: string | null;
  notes?: string | null;
}

export interface ReplyAnalysisResponse {
  company_name: string;
  classification: ReplyClassification;
  sentiment: ReplySentiment;
  urgency: ReplyUrgency;
  summary: string;
  detected_intent: string[];
  recommended_next_action: string;
  suggested_reply: string | null;
  suggested_reply_subject: string | null;
  questions_to_answer: string[];
  objections_detected: string[];
  buying_signals: string[];
  do_not_continue_if: string[];
  compliance_notes: string[];
  missing_information: string[];
  confidence_score: number;
}

// -- Sales Workflow (chains Lead Research -> Company Intelligence ->
// Personalization -> Email Draft) --------------------------------------------

export interface SalesWorkflowRequest {
  company_name: string;
  website_url?: string | null;
  industry?: string | null;
  location?: string | null;
  company_description?: string | null;
  website_text?: string | null;
  target_persona?: string | null;
  product_or_service_offered: string;
  sender_name?: string | null;
  sender_company?: string | null;
  tone?: EmailTone | null;
  language?: string | null;
  notes?: string | null;
  // Reserved fields wired into the workflow: fetches website_url via the
  // same SSRF-guarded Website Research backend used by
  // POST /api/v1/research/website. No LLM call happens in that fetch step.
  use_website_research?: boolean;
  website_research_max_pages?: number | null;
}

export interface SalesWorkflowResponse {
  workflow_id: string;
  status: string;
  company_name: string;
  lead_research: LeadResearchResponse;
  company_intelligence: CompanyIntelligenceResponse;
  personalization: PersonalizationResponse;
  email_draft: EmailDraftResponse;
  human_review_required: boolean;
  review_checklist: string[];
  compliance_notes: string[];
  missing_information: string[];
  confidence_score: number;
  crm_company_id?: string | null;
  crm_lead_id?: string | null;
  crm_email_draft_id?: string | null;
  website_research_used: boolean;
  website_research: WebsiteResearchResponse | null;
  website_research_warnings: string[];
}

// -- Workflow History (persisted workflow runs) ------------------------------

export type WorkflowReviewStatus =
  | "needs_review"
  | "reviewed"
  | "approved"
  | "rejected"
  | "archived";

export interface WorkflowRunSummary {
  id: string;
  company_name: string;
  workflow_type: string;
  status: string;
  review_status: WorkflowReviewStatus;
  confidence_score: number | null;
  company_id?: string | null;
  lead_id?: string | null;
  contact_id?: string | null;
  email_draft_id?: string | null;
  created_at: string;
  updated_at: string;
}

export interface WorkflowRunDetail extends WorkflowRunSummary {
  input_payload: Record<string, unknown>;
  result_payload: Record<string, unknown>;
  missing_information: string[];
  compliance_notes: string[];
}

export interface WorkflowRunListResponse {
  items: WorkflowRunSummary[];
  limit: number;
  offset: number;
}

export interface ListSalesWorkflowRunsParams {
  limit?: number;
  offset?: number;
  company_name?: string;
  review_status?: WorkflowReviewStatus;
}

export interface UpdateWorkflowReviewStatusRequest {
  review_status: WorkflowReviewStatus;
}

export type UpdateWorkflowReviewStatusResponse = WorkflowRunDetail;

// -- CRM ------------------------------------------------------------------

export type LeadStatus = "new" | "contacted" | "qualified" | "won" | "lost";
export type LeadSource = "website" | "referral" | "outbound" | "event" | "other";

export interface Company {
  id: string;
  name: string;
  domain: string | null;
  industry: string | null;
  created_at: string;
  updated_at: string;
}

export interface Lead {
  id: string;
  company_id: string;
  source: LeadSource;
  status: LeadStatus;
  score: number;
  created_at: string;
  updated_at: string;
}

export interface Contact {
  id: string;
  company_id: string;
  first_name: string;
  last_name: string;
  email: string | null;
  phone: string | null;
  created_at: string;
  updated_at: string;
}

export type InteractionType = "email" | "call" | "meeting" | "note" | "workflow_run";

export interface Interaction {
  id: string;
  lead_id: string;
  type: InteractionType;
  status: string | null;
  notes: string | null;
  occurred_at: string;
  created_at: string;
  updated_at: string;
}

export type EmailDraftReviewStatus =
  | "needs_review"
  | "in_review"
  | "approved"
  | "rejected"
  | "changes_requested"
  | "archived";

export interface EmailDraftRecord {
  id: string;
  company_id: string;
  lead_id: string | null;
  workflow_run_id: string | null;
  subject_lines: string[];
  email_body: string;
  status: string;
  review_status: EmailDraftReviewStatus;
  reviewer_name: string | null;
  review_comment: string | null;
  reviewed_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface WorkflowCrmLinks {
  workflow_id: string;
  company_id: string | null;
  lead_id: string | null;
  contact_id: string | null;
  email_draft_id: string | null;
}

// -- Human Review & Approval --------------------------------------------

export interface EmailDraftReviewStatusUpdateRequest {
  review_status: EmailDraftReviewStatus;
  reviewer_name?: string | null;
  comment?: string | null;
}

export interface EmailDraftReviewStatusResponse {
  email_draft_id: string;
  review_status: EmailDraftReviewStatus;
  reviewer_name: string | null;
  review_comment: string | null;
  reviewed_at: string | null;
  message: string;
}

export type ReviewEventType =
  | "review_started"
  | "comment_added"
  | "approved"
  | "rejected"
  | "changes_requested"
  | "archived";

export interface ReviewEvent {
  id: string;
  workflow_run_id: string | null;
  email_draft_id: string | null;
  event_type: ReviewEventType;
  previous_status: string | null;
  new_status: string | null;
  comment: string | null;
  reviewer_name: string | null;
  metadata: Record<string, unknown> | null;
  created_at: string;
}

export interface ReviewEventListResponse {
  items: ReviewEvent[];
}

export interface WorkflowCommentRequest {
  reviewer_name?: string | null;
  comment: string;
}

export interface WorkflowCommentResponse {
  workflow_id: string;
  event_id: string;
  message: string;
}

// -- Auth (local JWT — no external provider, no OAuth) -----------------------

export type UserRole = "admin" | "reviewer" | "sales";

export interface User {
  id: string;
  email: string;
  full_name: string | null;
  role: UserRole;
  is_active: boolean;
  is_superuser: boolean;
  created_at: string;
  updated_at: string;
}

export interface RegisterRequest {
  email: string;
  password: string;
  full_name?: string | null;
  role?: UserRole;
}

export interface LoginRequest {
  email: string;
  password: string;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
}

export type CurrentUserResponse = User;

export interface UserListResponse {
  items: User[];
}

// -- LLM Provider Settings ----------------------------------------------------
// Read-only: these never carry ANTHROPIC_API_KEY or any other secret — only
// whether one is configured (anthropic_configured).

export interface LLMProviderStatus {
  active_provider: string;
  real_calls_enabled: boolean;
  anthropic_configured: boolean;
  anthropic_model: string | null;
  safe_mode: boolean;
  mock_mode: boolean;
  message: string;
}

export interface LLMProviderTestResponse {
  provider: string;
  ok: boolean;
  message: string;
}

// -- Website Research ---------------------------------------------------------
// Fetches only the exact public URL the caller supplies. No LLM call, no
// automatic mass research, no LinkedIn scraping, no automatic contact.

export interface WebsiteResearchRequest {
  url: string;
  max_pages?: number;
  include_same_domain_links: boolean;
}

export interface WebsiteResearchResponse {
  url: string;
  final_url: string;
  domain: string;
  title: string | null;
  meta_description: string | null;
  extracted_text: string;
  text_length: number;
  pages_fetched: number;
  sources_used: string[];
  warnings: string[];
}

// -- CRM Pipeline -------------------------------------------------------------
// Changing a lead's pipeline status is bookkeeping only: it never sends an
// email or makes contact, and "approved" means only that a human has
// internally reviewed the lead's workflow run, never that anything was sent.

export type PipelineStatus =
  | "new"
  | "research_completed"
  | "draft_created"
  | "in_review"
  | "approved"
  | "rejected"
  | "archived";

export interface LeadPipelineSummary {
  id: string;
  company_id: string;
  pipeline_status: PipelineStatus;
  pipeline_updated_at: string | null;
  score: number;
  created_at: string;
  updated_at: string;
}

export interface PipelineColumn {
  pipeline_status: PipelineStatus;
  leads: LeadPipelineSummary[];
}

export interface PipelineBoardResponse {
  columns: PipelineColumn[];
}

export interface UpdateLeadPipelineStatusRequest {
  pipeline_status: PipelineStatus;
}

export interface UpdateLeadPipelineStatusResponse {
  id: string;
  company_id: string;
  pipeline_status: PipelineStatus;
  pipeline_updated_at: string | null;
}
