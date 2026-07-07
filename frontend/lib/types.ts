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
  recipient_name?: string | null;
  // Checked against the do-not-contact list before an email draft is
  // created — a matching entry blocks draft creation for this run.
  recipient_email?: string | null;
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
  // Optional — the workflow runs identically without either. Selecting an
  // ICP only adds a fit assessment; selecting an Offer only steers
  // Personalization/Email Draft content and wording.
  icp_profile_id?: string | null;
  offer_profile_id?: string | null;
}

export interface SalesWorkflowResponse {
  workflow_id: string;
  // "completed" once every step has succeeded, or "blocked" if a
  // do-not-contact match stopped outreach preparation.
  status: string;
  company_name: string;
  lead_research: LeadResearchResponse;
  company_intelligence: CompanyIntelligenceResponse;
  // Null when do_not_contact_block.is_blocked is true — Personalization is
  // skipped in that case.
  personalization: PersonalizationResponse | null;
  // Null when do_not_contact_block.is_blocked is true — no draft is
  // created in that case.
  email_draft: EmailDraftResponse | null;
  do_not_contact_block?: DoNotContactCheckResponse | null;
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
  icp_profile_id?: string | null;
  icp_fit_score?: number | null;
  icp_fit_level?: ICPFitLevel | null;
  icp_fit_summary?: string | null;
  icp_warnings: string[];
  offer_profile_id?: string | null;
  offer_summary?: string | null;
  offer_warnings: string[];
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

// -- Do-not-contact (opt-out) compliance ---------------------------------------
// Blocking a lead/email/domain/company here never sends an email or
// contacts anyone by itself — it only ever stops the Sales Workflow from
// creating an Email Draft and stops Review Approval from succeeding.
// Inactive entries never block anything.

export interface DoNotContactEntry {
  id: string;
  email: string | null;
  domain: string | null;
  company_name: string | null;
  reason: string;
  source: string;
  is_active: boolean;
  created_by_user_id: string | null;
  created_at: string;
  updated_at: string;
}

export interface CreateDoNotContactRequest {
  email?: string | null;
  domain?: string | null;
  company_name?: string | null;
  reason: string;
  source?: string;
}

export interface UpdateDoNotContactRequest {
  email?: string | null;
  domain?: string | null;
  company_name?: string | null;
  reason?: string | null;
  is_active?: boolean | null;
}

export interface DoNotContactListResponse {
  items: DoNotContactEntry[];
  limit: number;
  offset: number;
}

export interface DoNotContactCheckRequest {
  email?: string | null;
  domain?: string | null;
  company_name?: string | null;
}

export interface DoNotContactCheckResponse {
  is_blocked: boolean;
  matched_by: "email" | "domain" | "company_name" | null;
  matched_entry_id: string | null;
  reason: string | null;
  warning_message: string | null;
}

// -- Gmail/Outlook Draft Integration --------------------------------------------
// Every capability here only ever creates a *draft* at Gmail/Outlook/Mock —
// there is no send capability anywhere in this integration. External draft
// creation is a conscious, one-draft-at-a-time user action; it is never
// triggered automatically by the Sales Workflow. Do-not-contact and Human
// Review approval are both checked before any provider is called.

export type EmailIntegrationProvider = "mock" | "gmail" | "outlook";

export interface EmailIntegrationStatus {
  active_provider: EmailIntegrationProvider;
  real_drafts_enabled: boolean;
  safe_mode: boolean;
  connected: boolean;
  external_account_email: string | null;
  message: string;
}

export interface EmailProviderInfo {
  provider: EmailIntegrationProvider;
  display_name: string;
  is_active_provider: boolean;
  requires_oauth: boolean;
  configured: boolean;
  connected: boolean;
  external_account_email: string | null;
}

export interface EmailIntegrationProvidersResponse {
  items: EmailProviderInfo[];
}

export interface StartEmailProviderConnectionResponse {
  provider: EmailIntegrationProvider;
  authorization_url: string;
  message: string;
}

export interface ExternalEmailDraft {
  id: string;
  email_draft_id: string;
  provider: EmailIntegrationProvider;
  // Never "sent" — this only ever reflects that a draft was created (or
  // blocked, or failed) at the provider.
  provider_status: "mock_created" | "created" | "blocked" | "failed";
  provider_draft_id: string | null;
  provider_draft_url: string | null;
  created_by_user_id: string | null;
  last_error: string | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface CreateExternalEmailDraftResponse {
  blocked: boolean;
  block_reason:
    | "do_not_contact"
    | "review_not_approved"
    | "provider_not_configured"
    | "provider_error"
    | null;
  external_draft: ExternalEmailDraft | null;
  message: string;
}

export interface ExternalEmailDraftStatusResponse {
  exists: boolean;
  external_draft: ExternalEmailDraft | null;
  message: string;
}

// -- Reply Inbox / Reply Tracking -----------------------------------------------
// Every capability here only ever reads messages that already exist in a
// connected mailbox (Mock by default) — there is no reply/send capability
// anywhere in this integration. Do-not-contact and Human Review both
// continue to apply exactly as before; syncing a reply never sends
// anything and never creates a draft automatically.

export type ReplyTrackingProvider = "mock" | "gmail" | "outlook";

export interface ReplyIntegrationStatus {
  active_provider: ReplyTrackingProvider;
  real_reads_enabled: boolean;
  safe_mode: boolean;
  connected: boolean;
  external_account_email: string | null;
  message: string;
}

// Raw classification from the Reply Analysis Agent — same vocabulary as
// ReplyClassification/ReplySentiment above, reused here for the stored
// Reply's detected_intent/sentiment fields.
export type ReplyIntent = ReplyClassification;

// Project taxonomy used for do-not-contact and pipeline recommendations.
export type ReplyCategory =
  | "interested"
  | "not_interested"
  | "needs_more_info"
  | "meeting_request"
  | "out_of_office"
  | "unsubscribe"
  | "unknown";

export interface Reply {
  id: string;
  lead_id: string | null;
  company_id: string | null;
  email_draft_id: string | null;
  external_draft_id: string | null;
  provider: ReplyTrackingProvider;
  provider_message_id: string;
  provider_thread_id: string | null;
  provider_message_url: string | null;
  from_email: string;
  from_name: string | null;
  to_email: string | null;
  subject: string | null;
  body_preview: string | null;
  body_text: string | null;
  received_at: string;
  detected_intent: ReplyIntent | null;
  sentiment: ReplySentiment | null;
  reply_category: ReplyCategory | null;
  confidence_score: number | null;
  is_read: boolean;
  is_archived: boolean;
  last_error: string | null;
  created_at: string;
  updated_at: string;
  // Computed, never applied automatically — a human acts on this via the
  // existing pipeline-status endpoint if they choose to.
  recommended_pipeline_status: PipelineStatus | null;
  compliance_warning: string | null;
}

export interface ReplyListResponse {
  items: Reply[];
  limit: number;
  offset: number;
}

// Same shape as Reply — kept as a distinct alias for the single-reply
// detail view, matching the naming used elsewhere in this project.
export type ReplyDetailResponse = Reply;

export interface SyncRepliesResponse {
  status: "mock_synced" | "synced" | "blocked" | "failed";
  provider: ReplyTrackingProvider;
  synced_count: number;
  new_count: number;
  duplicate_count: number;
  do_not_contact_signals: number;
  message: string;
  error: string | null;
  replies: Reply[];
}

// -- Deployment / Monitoring / Backups --------------------------------------
// Admin-only. Never includes a secret, API key, or token — only which mode
// each integration is running in.

export interface SystemStatus {
  app_name: string;
  app_version: string;
  app_env: string;
  database_status: "up" | "down";
  redis_status: "up" | "down";
  llm_provider: string;
  llm_real_calls_enabled: boolean;
  email_integration_provider: string;
  email_real_drafts_enabled: boolean;
  reply_tracking_provider: string;
  reply_real_reads_enabled: boolean;
  metrics_enabled: boolean;
  backups_enabled: boolean;
  request_logging_enabled: boolean;
  production_warnings: string[];
}

export interface BackupStatus {
  backups_enabled: boolean;
  backup_dir: string;
  retention_days: number;
  latest_backup_time: string | null;
  latest_backup_file_name: string | null;
}

export interface Metrics {
  request_count: number;
  request_error_count: number;
  average_response_time_ms: number;
  workflow_run_count: number;
  email_draft_count: number;
  reply_count: number;
  do_not_contact_block_count: number;
  external_draft_created_count: number;
  llm_test_count: number;
}

// -- Compliance Hardening / Rate Limits / Audit Logs -----------------------------
// Never includes a secret, API key, or token. email_sending_enabled and
// automatic_contact_enabled are always false — there is no send/auto-
// contact capability anywhere in this system.

export interface ComplianceStatus {
  do_not_contact_enabled: boolean;
  human_review_enabled: boolean;
  email_sending_enabled: boolean;
  automatic_contact_enabled: boolean;
  llm_provider: string;
  llm_real_calls_enabled: boolean;
  email_integration_provider: string;
  email_real_drafts_enabled: boolean;
  reply_tracking_provider: string;
  reply_real_reads_enabled: boolean;
  rate_limits_enabled: boolean;
  audit_logs_enabled: boolean;
  last_do_not_contact_block_count: number;
  last_review_block_count: number;
  safe_mode: boolean;
  warnings: string[];
  message: string;
}

export interface AuditLog {
  id: string;
  actor_user_id: string | null;
  actor_role: string | null;
  action: string;
  entity_type: string | null;
  entity_id: string | null;
  result: string;
  reason: string | null;
  request_id: string | null;
  ip_hash: string | null;
  user_agent: string | null;
  metadata: Record<string, unknown> | null;
  created_at: string;
}

export interface AuditLogListResponse {
  items: AuditLog[];
  limit: number;
  offset: number;
}

// Same shape as AuditLog — kept as a distinct alias for the single-entry
// detail view, matching the naming used elsewhere in this project.
export type AuditLogDetailResponse = AuditLog;

export interface AuditLogFilters {
  actor_user_id?: string;
  action?: string;
  entity_type?: string;
  entity_id?: string;
  result?: string;
  date_from?: string;
  date_to?: string;
  limit?: number;
  offset?: number;
}

// -- ICP (Ideal Customer Profile) --------------------------------------------
// Used only to score existing data against — never to scrape or fetch new
// external data (no LinkedIn scraping, no automatic lookups).

export type ICPFitLevel = "excellent" | "good" | "medium" | "weak" | "not_fit";

export interface ICPProfile {
  id: string;
  name: string;
  description: string | null;
  target_industries: string[];
  excluded_industries: string[];
  target_company_sizes: string[];
  target_locations: string[];
  target_languages: string[];
  target_keywords: string[];
  negative_keywords: string[];
  target_pain_points: string[];
  buying_triggers: string[];
  required_signals: string[];
  excluded_signals: string[];
  buyer_personas: string[];
  preferred_titles: string[];
  excluded_titles: string[];
  minimum_fit_score: number;
  scoring_weights: Record<string, unknown> | null;
  is_active: boolean;
  created_by_user_id: string | null;
  created_at: string;
  updated_at: string;
}

export interface CreateICPProfileRequest {
  name: string;
  description?: string | null;
  target_industries?: string[];
  excluded_industries?: string[];
  target_company_sizes?: string[];
  target_locations?: string[];
  target_languages?: string[];
  target_keywords?: string[];
  negative_keywords?: string[];
  target_pain_points?: string[];
  buying_triggers?: string[];
  required_signals?: string[];
  excluded_signals?: string[];
  buyer_personas?: string[];
  preferred_titles?: string[];
  excluded_titles?: string[];
  minimum_fit_score?: number;
  scoring_weights?: Record<string, unknown> | null;
  is_active?: boolean;
}

export type UpdateICPProfileRequest = Partial<CreateICPProfileRequest>;

export interface ICPProfileListResponse {
  items: ICPProfile[];
  limit: number;
  offset: number;
}

export interface ICPFitCheckRequest {
  icp_profile_id: string;
  company_name?: string | null;
  industry?: string | null;
  location?: string | null;
  company_size?: string | null;
  website_text?: string | null;
  notes?: string | null;
  keywords?: string[];
}

export interface ICPFitCheckResponse {
  icp_profile_id: string;
  fit_score: number;
  fit_level: ICPFitLevel;
  matched_signals: string[];
  missing_signals: string[];
  negative_signals: string[];
  recommendation: string;
  warnings: string[];
}

// -- Offer profiles -----------------------------------------------------------
// Defines what is being sold and the guardrails (forbidden_claims,
// required_disclaimers) around how it may be described. Never used to
// generate a false promise or a fabricated case study.

export interface OfferProfile {
  id: string;
  name: string;
  main_value_proposition: string;
  description: string | null;
  target_outcome: string | null;
  pain_points_solved: string[];
  key_benefits: string[];
  differentiators: string[];
  proof_points: string[];
  case_study_notes: string | null;
  pricing_notes: string | null;
  call_to_action: string | null;
  tone: string;
  language: string;
  forbidden_claims: string[];
  required_disclaimers: string[];
  is_active: boolean;
  created_by_user_id: string | null;
  created_at: string;
  updated_at: string;
}

export interface CreateOfferProfileRequest {
  name: string;
  main_value_proposition: string;
  description?: string | null;
  target_outcome?: string | null;
  pain_points_solved?: string[];
  key_benefits?: string[];
  differentiators?: string[];
  proof_points?: string[];
  case_study_notes?: string | null;
  pricing_notes?: string | null;
  call_to_action?: string | null;
  tone?: string;
  language?: string;
  forbidden_claims?: string[];
  required_disclaimers?: string[];
  is_active?: boolean;
}

export type UpdateOfferProfileRequest = Partial<CreateOfferProfileRequest>;

export interface OfferProfileListResponse {
  items: OfferProfile[];
  limit: number;
  offset: number;
}

export interface OfferPreviewRequest {
  offer_profile_id: string;
}

export interface OfferPreviewResponse {
  offer_profile_id: string;
  summary: string;
  positioning: string;
  suggested_cta: string | null;
  warnings: string[];
}

// -- Lead Sourcing --------------------------------------------------------------
// Finds and scores potential customers. Never sends an email, never
// contacts anyone, never scrapes LinkedIn or anything behind a login. A
// candidate only ever becomes a CRM Company/Lead through an explicit
// approve action.

export type LeadSourcingCampaignStatus =
  | "draft"
  | "ready"
  | "running"
  | "completed"
  | "failed"
  | "archived";

export type LeadSourcingRunStatus = "running" | "completed" | "failed" | "cancelled";

export type LeadCandidateDoNotContactStatus = "unknown" | "clear" | "blocked";

export type LeadCandidateDuplicateStatus = "unknown" | "new" | "duplicate";

export type LeadCandidateReviewStatus = "pending" | "approved" | "rejected";

export interface LeadSourcingProviderStatus {
  provider: string;
  real_search_enabled: boolean;
  status: string;
  max_results_per_run: number;
  max_website_pages_per_company: number;
  allow_public_website_email_extraction: boolean;
  allow_personal_emails: boolean;
  require_review_before_crm: boolean;
  warnings: string[];
}

export interface LeadSourcingCampaign {
  id: string;
  name: string;
  description: string | null;
  icp_profile_id: string | null;
  offer_profile_id: string | null;
  source_type: string;
  search_query: string | null;
  target_industry: string | null;
  target_location: string | null;
  target_keywords: string[];
  excluded_keywords: string[];
  max_results: number;
  status: LeadSourcingCampaignStatus;
  created_by_user_id: string | null;
  created_at: string;
  updated_at: string;
}

export interface CreateLeadSourcingCampaignRequest {
  name: string;
  description?: string | null;
  icp_profile_id?: string | null;
  offer_profile_id?: string | null;
  search_query?: string | null;
  target_industry?: string | null;
  target_location?: string | null;
  target_keywords?: string[];
  excluded_keywords?: string[];
  max_results?: number;
}

export interface UpdateLeadSourcingCampaignRequest {
  name?: string;
  description?: string | null;
  icp_profile_id?: string | null;
  offer_profile_id?: string | null;
  search_query?: string | null;
  target_industry?: string | null;
  target_location?: string | null;
  target_keywords?: string[];
  excluded_keywords?: string[];
  max_results?: number;
  status?: "draft" | "ready";
}

export interface LeadSourcingCampaignListResponse {
  items: LeadSourcingCampaign[];
  limit: number;
  offset: number;
}

export interface LeadSourcingRun {
  id: string;
  campaign_id: string;
  status: LeadSourcingRunStatus;
  provider: string;
  started_by_user_id: string | null;
  started_at: string | null;
  completed_at: string | null;
  total_candidates_found: number;
  total_candidates_saved: number;
  total_duplicates: number;
  total_blocked_by_do_not_contact: number;
  total_errors: number;
  warnings: string[];
  created_at: string;
  updated_at: string;
}

export interface LeadSourcingRunListResponse {
  items: LeadSourcingRun[];
  limit: number;
  offset: number;
}

export interface LeadCandidate {
  // null only for an ephemeral dry-run candidate that was never persisted.
  id: string | null;
  sourcing_run_id: string;
  campaign_id: string;
  company_name: string | null;
  company_domain: string | null;
  company_website_url: string | null;
  industry: string | null;
  location: string | null;
  description: string | null;
  source_url: string | null;
  source_name: string | null;
  source_type: string;
  public_contact_email: string | null;
  contact_page_url: string | null;
  confidence_score: number | null;
  icp_fit_score: number | null;
  icp_fit_level: ICPFitLevel | null;
  matched_signals: string[];
  negative_signals: string[];
  do_not_contact_status: LeadCandidateDoNotContactStatus;
  duplicate_status: LeadCandidateDuplicateStatus;
  review_status: LeadCandidateReviewStatus;
  crm_company_id: string | null;
  crm_lead_id: string | null;
  notes: string[];
  warnings: string[];
}

export interface LeadCandidateListResponse {
  items: LeadCandidate[];
  limit: number;
  offset: number;
}

export interface StartLeadSourcingRunRequest {
  campaign_id: string;
  max_results?: number;
  dry_run?: boolean;
}

export interface StartLeadSourcingRunResponse {
  run: LeadSourcingRun;
  candidates: LeadCandidate[];
  dry_run: boolean;
}

export interface ApproveLeadCandidateRequest {
  notes?: string | null;
}

export interface ApproveLeadCandidateResponse {
  candidate: LeadCandidate;
  crm_company_id: string | null;
  crm_lead_id: string | null;
  warnings: string[];
}

export interface RejectLeadCandidateRequest {
  reason?: string | null;
}

export interface RejectLeadCandidateResponse {
  candidate: LeadCandidate;
}

export interface ImportLeadCandidatesRequest {
  campaign_id: string;
  raw_text: string;
}

export interface ImportLeadCandidatesResponse {
  run: LeadSourcingRun;
  candidates: LeadCandidate[];
  total_imported: number;
  total_duplicates: number;
  total_blocked_by_do_not_contact: number;
  warnings: string[];
}

// -- Lead Qualification & Scoring -----------------------------------------------
// Scores and prioritizes Lead Candidates/CRM Leads. Never sends an email,
// never contacts anyone, never starts a Sales Workflow by itself. A
// result is a recommendation only.

export type QualificationSourceType = "lead_candidate" | "crm_lead" | "crm_company" | "mixed";

export type QualificationRunStatus = "running" | "completed" | "failed" | "cancelled";

export type QualificationLevel = "excellent" | "good" | "medium" | "weak" | "not_fit";

export type QualificationStatus =
  | "qualified"
  | "priority"
  | "needs_review"
  | "disqualified"
  | "blocked"
  | "duplicate";

export type RecommendedNextAction =
  | "start_sales_workflow"
  | "enrich_more"
  | "review_manually"
  | "skip"
  | "blocked_do_not_contact"
  | "merge_duplicate";

export interface QualificationScoreBreakdown {
  base_score: number;
  icp_fit_contribution: number;
  industry_match: number;
  company_size_match: number;
  location_match: number;
  website_signal_quality: number;
  buying_triggers: number;
  pain_points_match: number;
  keyword_match: number;
  negative_keywords_penalty: number;
  excluded_signals_penalty: number;
  data_completeness_penalty: number;
  source_confidence_contribution: number;
  total: number;
}

export interface LeadQualificationRun {
  id: string;
  name: string | null;
  source_type: QualificationSourceType;
  icp_profile_id: string | null;
  offer_profile_id: string | null;
  status: QualificationRunStatus;
  started_by_user_id: string | null;
  started_at: string | null;
  completed_at: string | null;
  total_items: number;
  qualified_count: number;
  priority_count: number;
  disqualified_count: number;
  needs_review_count: number;
  average_score: number | null;
  warnings: string[];
  created_at: string;
  updated_at: string;
}

export interface LeadQualificationRunListResponse {
  items: LeadQualificationRun[];
  limit: number;
  offset: number;
}

export interface LeadQualificationResult {
  id: string;
  qualification_run_id: string;
  lead_candidate_id: string | null;
  lead_id: string | null;
  company_id: string | null;
  icp_profile_id: string | null;
  offer_profile_id: string | null;
  qualification_score: number;
  qualification_level: QualificationLevel;
  qualification_status: QualificationStatus;
  priority_rank: number | null;
  fit_summary: string | null;
  score_breakdown: QualificationScoreBreakdown;
  positive_signals: string[];
  negative_signals: string[];
  missing_data: string[];
  recommended_next_action: RecommendedNextAction;
  recommended_outreach_angle: string | null;
  disqualification_reason: string | null;
  compliance_status: "clear" | "blocked";
  do_not_contact_status: "unknown" | "clear" | "blocked";
  duplicate_status: "unknown" | "new" | "duplicate";
  pipeline_status: string | null;
  confidence_score: number | null;
  reviewed_by_user_id: string | null;
  reviewed_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface LeadQualificationResultListResponse {
  items: LeadQualificationResult[];
  limit: number;
  offset: number;
}

export interface StartLeadQualificationRequest {
  name?: string | null;
  source_type: QualificationSourceType;
  lead_candidate_ids?: string[];
  lead_ids?: string[];
  company_ids?: string[];
  icp_profile_id?: string | null;
  offer_profile_id?: string | null;
  min_score?: number | null;
  dry_run?: boolean;
}

export interface StartLeadQualificationResponse {
  run: LeadQualificationRun;
  results: LeadQualificationResult[];
  dry_run: boolean;
}

export interface QualifyLeadCandidateRequest {
  icp_profile_id?: string | null;
  offer_profile_id?: string | null;
}

export interface QualifyCRMLeadRequest {
  icp_profile_id?: string | null;
  offer_profile_id?: string | null;
}

export interface QualificationReviewRequest {
  qualification_status: "qualified" | "priority" | "needs_review" | "disqualified";
  notes?: string | null;
}

export interface QualificationReviewResponse {
  result: LeadQualificationResult;
}

export interface QualificationDashboardResponse {
  total_qualified: number;
  total_priority: number;
  total_needs_review: number;
  total_disqualified: number;
  total_blocked: number;
  average_score: number | null;
  top_recommended_leads: LeadQualificationResult[];
  warnings: string[];
}

export interface LeadQualificationStatus {
  enabled: boolean;
  use_llm: boolean;
  llm_provider: string;
  llm_real_calls_enabled: boolean;
  use_website_research: boolean;
  require_icp: boolean;
  default_min_score: number;
  priority_score: number;
  disqualify_score: number;
  warnings: string[];
}
