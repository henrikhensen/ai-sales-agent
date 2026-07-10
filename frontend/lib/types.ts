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
  data_retention_enabled: boolean;
  data_export_available: boolean;
  data_requests_enabled: boolean;
  legal_review_required: boolean;
  privacy_notice_available: boolean;
  data_processing_summary_available: boolean;
  retention_policies_count: number;
  last_retention_run: string | null;
  last_data_export_request: string | null;
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

// -- Outreach Campaign Queue -------------------------------------------------------
// Collects already-qualified leads into a prioritized, campaign-scoped
// queue for human review. Never sends an email, never contacts anyone, and
// never creates an external (Gmail/Outlook) draft by itself.

export type OutreachCampaignStatus =
  | "draft"
  | "ready"
  | "active"
  | "paused"
  | "completed"
  | "archived";

export type OutreachQueueStatus =
  | "queued"
  | "blocked"
  | "needs_review"
  | "ready_for_workflow"
  | "workflow_prepared"
  | "draft_created"
  | "review_pending"
  | "approved"
  | "rejected"
  | "external_draft_created"
  | "replied"
  | "archived"
  // Added for Controlled Outreach Dispatch — never set automatically; only
  // ever the outcome of a human-confirmed dispatch action.
  | "sent_manually_confirmed"
  | "failed"
  | "cancelled";

export interface OutreachCampaign {
  id: string;
  name: string;
  description: string | null;
  icp_profile_id: string | null;
  offer_profile_id: string | null;
  target_language: string | null;
  tone: string | null;
  min_qualification_score: number;
  allowed_qualification_levels: string[];
  excluded_statuses: string[];
  max_queue_items: number;
  status: OutreachCampaignStatus;
  created_by_user_id: string | null;
  created_at: string;
  updated_at: string;
}

export interface OutreachCampaignListResponse {
  items: OutreachCampaign[];
  limit: number;
  offset: number;
}

export interface CreateOutreachCampaignRequest {
  name: string;
  description?: string | null;
  icp_profile_id?: string | null;
  offer_profile_id?: string | null;
  target_language?: string | null;
  tone?: string | null;
  min_qualification_score?: number | null;
  allowed_qualification_levels?: string[];
  excluded_statuses?: string[];
  max_queue_items?: number | null;
}

export interface UpdateOutreachCampaignRequest {
  name?: string | null;
  description?: string | null;
  icp_profile_id?: string | null;
  offer_profile_id?: string | null;
  target_language?: string | null;
  tone?: string | null;
  min_qualification_score?: number | null;
  allowed_qualification_levels?: string[] | null;
  excluded_statuses?: string[] | null;
  max_queue_items?: number | null;
}

export interface UpdateOutreachCampaignStatusRequest {
  status: OutreachCampaignStatus;
}

export interface OutreachQueueItem {
  id: string | null;
  campaign_id: string;
  lead_id: string | null;
  company_id: string | null;
  lead_candidate_id: string | null;
  qualification_result_id: string | null;
  icp_profile_id: string | null;
  offer_profile_id: string | null;
  priority_rank: number | null;
  qualification_score: number;
  qualification_level: string;
  queue_status: OutreachQueueStatus;
  recommended_outreach_angle: string | null;
  personalization_notes: string | null;
  compliance_status: "clear" | "blocked";
  do_not_contact_status: "unknown" | "clear" | "blocked";
  duplicate_status: "unknown" | "new" | "duplicate";
  workflow_run_id: string | null;
  email_draft_id: string | null;
  review_id: string | null;
  external_draft_id: string | null;
  last_action: string | null;
  last_error: string | null;
  created_by_user_id: string | null;
  assigned_to_user_id: string | null;
  created_at: string | null;
  updated_at: string | null;
}

export interface OutreachQueueItemListResponse {
  items: OutreachQueueItem[];
  limit: number;
  offset: number;
}

export interface BuildOutreachQueueRequest {
  qualification_result_ids?: string[];
  lead_ids?: string[];
  min_score?: number | null;
  max_items?: number | null;
  dry_run?: boolean;
}

export interface BuildOutreachQueueResponse {
  campaign: OutreachCampaign;
  items: OutreachQueueItem[];
  skipped_count: number;
  blocked_count: number;
  dry_run: boolean;
  warnings: string[];
}

export interface PrepareQueueItemWorkflowRequest {
  notes?: string | null;
}

export interface PrepareQueueItemWorkflowResponse {
  item: OutreachQueueItem;
  workflow_id: string | null;
  email_draft_id: string | null;
  blocked: boolean;
  warnings: string[];
}

export interface PrepareQueueBatchRequest {
  queue_item_ids?: string[];
  max_items?: number | null;
}

export interface PrepareQueueBatchResponse {
  total_requested: number;
  prepared_count: number;
  skipped_count: number;
  blocked_count: number;
  failed_count: number;
  items: OutreachQueueItem[];
  warnings: string[];
}

export interface UpdateQueueItemStatusRequest {
  queue_status: OutreachQueueStatus;
  notes?: string | null;
  external_draft_id?: string | null;
}

export interface UpdateQueueItemStatusResponse {
  item: OutreachQueueItem;
}

export interface OutreachQueueDashboardResponse {
  total_queued: number;
  total_blocked: number;
  total_needs_review: number;
  total_ready_for_workflow: number;
  total_workflow_prepared: number;
  total_draft_created: number;
  total_review_pending: number;
  total_approved: number;
  total_rejected: number;
  total_external_draft_created: number;
  total_archived: number;
  campaigns: OutreachCampaign[];
  warnings: string[];
}

export interface OutreachQueueStatusInfo {
  enabled: boolean;
  default_min_score: number;
  default_batch_size: number;
  max_batch_size: number;
  require_qualification: boolean;
  require_human_review: boolean;
  allow_batch_workflow_prep: boolean;
  auto_create_external_drafts: boolean;
  warnings: string[];
}

// -- Controlled Outreach Dispatch --------------------------------------------------
// Processes a single, already-approved Outreach Queue item into either a
// controlled external draft, or — only when explicitly enabled and
// confirmed by a human — a manually confirmed send. Draft-only is the
// default and safe mode; real sending always requires explicit
// activation, human review approval, a do-not-contact check, a compliance
// acknowledgement, and a final confirmation. There is no batch send and
// no automatic send anywhere in this feature.

export type DispatchMode = "draft_only" | "manual_send";

export type DispatchStatus =
  | "pending"
  | "blocked"
  | "ready"
  | "external_draft_created"
  | "send_ready"
  | "sent_manually_confirmed"
  | "failed"
  | "cancelled"
  | "archived";

export interface DispatchCheck {
  do_not_contact_passed: boolean;
  human_review_approved: boolean;
  email_draft_exists: boolean;
  queue_item_allowed: boolean;
  rate_limit_ok: boolean;
  provider_config_ok: boolean;
  recipient_valid: boolean;
  compliance_ack_present: boolean;
}

export interface DispatchReadinessCheckRequest {
  dispatch_mode?: DispatchMode | null;
}

export interface DispatchReadinessCheckResponse {
  is_ready: boolean;
  blockers: string[];
  warnings: string[];
  checks: DispatchCheck;
  recommended_mode: DispatchMode;
  requires_final_confirmation: boolean;
  requires_compliance_ack: boolean;
  provider_status: string;
}

export interface OutreachDispatch {
  id: string;
  queue_item_id: string;
  outreach_campaign_id: string | null;
  lead_id: string | null;
  company_id: string | null;
  email_draft_id: string | null;
  external_draft_id: string | null;
  review_id: string | null;
  provider: string;
  dispatch_mode: DispatchMode;
  dispatch_status: DispatchStatus;
  recipient_email: string | null;
  subject_snapshot: string | null;
  body_preview_snapshot: string | null;
  final_confirmation_by_user_id: string | null;
  final_confirmation_at: string | null;
  compliance_acknowledged_by_user_id: string | null;
  compliance_acknowledged_at: string | null;
  do_not_contact_checked_at: string | null;
  human_review_checked_at: string | null;
  provider_message_id: string | null;
  provider_draft_id: string | null;
  provider_url: string | null;
  last_error: string | null;
  created_by_user_id: string | null;
  created_at: string;
  updated_at: string;
}

export interface OutreachDispatchListResponse {
  items: OutreachDispatch[];
  limit: number;
  offset: number;
}

export interface CreateDispatchRequest {
  dispatch_mode?: DispatchMode | null;
}

export interface CreateDispatchResponse {
  dispatch: OutreachDispatch;
  readiness: DispatchReadinessCheckResponse;
}

export interface DispatchComplianceAckRequest {
  contact_permission_confirmed: boolean;
  do_not_contact_confirmed: boolean;
  human_review_confirmed: boolean;
  draft_or_controlled_send_confirmed: boolean;
  legal_responsibility_confirmed: boolean;
}

export interface DispatchComplianceAckResponse {
  dispatch: OutreachDispatch;
}

export interface ConfirmDispatchRequest {
  confirmed?: boolean;
}

export interface ConfirmDispatchResponse {
  dispatch: OutreachDispatch;
  warnings: string[];
}

export interface CancelDispatchRequest {
  reason?: string | null;
}

export interface CancelDispatchResponse {
  dispatch: OutreachDispatch;
}

export interface DispatchDashboardResponse {
  enabled: boolean;
  dispatch_mode: DispatchMode;
  provider: string;
  real_send_enabled: boolean;
  require_final_confirmation: boolean;
  require_compliance_ack: boolean;
  require_approved_review: boolean;
  require_do_not_contact_check: boolean;
  max_per_day: number;
  max_per_hour: number;
  total_pending: number;
  total_blocked: number;
  total_ready: number;
  total_external_draft_created: number;
  total_send_ready: number;
  total_sent_manually_confirmed: number;
  total_failed: number;
  total_cancelled: number;
  warnings: string[];
}

// -- Customer Onboarding -----------------------------------------------------------
// A pure progress tracker over a fixed sequence of setup steps, plus a
// system-wide readiness check. Never enables a real provider, sends an
// email, or makes contact by itself.

export type OnboardingStep =
  | "welcome"
  | "profile_setup"
  | "company_setup"
  | "offer_setup"
  | "icp_setup"
  | "safe_mode_review"
  | "provider_settings_review"
  | "compliance_review"
  | "do_not_contact_review"
  | "first_lead_sourcing"
  | "first_qualification"
  | "first_outreach_queue"
  | "first_draft_review"
  | "first_real_world_test"
  | "feedback_quality_review"
  | "completion";

export type ReadinessLevel =
  | "not_ready"
  | "demo_ready"
  | "internal_ready"
  | "beta_ready";

export interface OnboardingStatus {
  id: string;
  user_id: string;
  current_step: OnboardingStep;
  completed_steps: string[];
  skipped_steps: string[];
  is_completed: boolean;
  completed_at: string | null;
  progress_percent: number;
  next_step: OnboardingStep | null;
  created_at: string;
  updated_at: string;
}

export interface OnboardingStepUpdateRequest {
  // Deliberately empty — the step name is always addressed via the URL path.
}

export interface OnboardingStepUpdateResponse {
  status: OnboardingStatus;
}

export interface OnboardingReadinessChecks {
  has_offer_profile: boolean;
  has_icp_profile: boolean;
  has_do_not_contact_enabled: boolean;
  has_human_review_enabled: boolean;
  safe_mode_active: boolean;
  real_llm_configured: boolean;
  email_integration_configured: boolean;
  reply_tracking_configured: boolean;
  dispatch_safe: boolean;
  audit_logs_enabled: boolean;
  rate_limits_enabled: boolean;
  compliance_documents_available: boolean;
  data_retention_config_present: boolean;
  data_export_available: boolean;
  data_subject_request_flow_available: boolean;
  legal_review_required_acknowledged: boolean;
  ready_for_demo: boolean;
  ready_for_internal_use: boolean;
  ready_for_customer_beta: boolean;
  quality_feedback_enabled: boolean;
  quality_scoring_enabled: boolean;
  beta_feedback_loop_available: boolean;
  blocking_feedback_respected: boolean;
  quality_beta_readiness_level: string;
}

export interface OnboardingReadinessResponse {
  readiness_level: ReadinessLevel;
  blockers: string[];
  warnings: string[];
  recommendations: string[];
  checks: OnboardingReadinessChecks;
  message: string;
}

// -- Admin Controls -----------------------------------------------------------------
// Two surfaces over the same workspace settings singleton: plain
// branding/defaults, and safety-relevant toggles. Neither ever returns a
// secret, API key, or token.

export interface WorkspaceSettings {
  id: string;
  workspace_name: string;
  company_name: string | null;
  company_website: string | null;
  default_language: string;
  default_tone: string;
  default_icp_profile_id: string | null;
  default_offer_profile_id: string | null;
  created_at: string;
  updated_at: string;
}

export interface UpdateWorkspaceSettingsRequest {
  workspace_name?: string | null;
  company_name?: string | null;
  company_website?: string | null;
  default_language?: string | null;
  default_tone?: string | null;
  default_icp_profile_id?: string | null;
  default_offer_profile_id?: string | null;
}

export interface AdminControlsStatus {
  require_human_review: boolean;
  require_do_not_contact_check: boolean;
  allow_real_llm_calls: boolean;
  allow_real_email_drafts: boolean;
  allow_real_reply_reads: boolean;
  allow_real_dispatch: boolean;
  dispatch_mode: DispatchMode;
  real_llm_configured: boolean;
  email_integration_configured: boolean;
  reply_tracking_configured: boolean;
  real_send_env_enabled: boolean;
  data_retention_enabled: boolean;
  anonymize_instead_of_delete: boolean;
  data_export_enabled: boolean;
  data_subject_requests_enabled: boolean;
  legal_review_required: boolean;
  warnings: string[];
  blockers: string[];
}

export interface UpdateAdminControlsRequest {
  require_human_review?: boolean | null;
  require_do_not_contact_check?: boolean | null;
  allow_real_llm_calls?: boolean | null;
  allow_real_email_drafts?: boolean | null;
  allow_real_reply_reads?: boolean | null;
  allow_real_dispatch?: boolean | null;
  dispatch_mode?: DispatchMode | null;
  data_retention_enabled?: boolean | null;
  anonymize_instead_of_delete?: boolean | null;
  data_export_enabled?: boolean | null;
  data_subject_requests_enabled?: boolean | null;
}

export type ChecklistItemStatus = "passed" | "warning" | "blocker" | "not_checked";

export interface ChecklistItem {
  key: string;
  label: string;
  status: ChecklistItemStatus;
  detail: string | null;
}

export interface CustomerSetupChecklistResponse {
  items: ChecklistItem[];
  overall_status: ChecklistItemStatus;
}

// -- Legal/Compliance Pack -----------------------------------------------------------

export interface ComplianceDocument {
  key: string;
  title: string;
  body: string;
}

export interface ComplianceDocumentsResponse {
  documents: ComplianceDocument[];
  disclaimer: string;
}

export type RetentionEntityType =
  | "lead"
  | "company"
  | "email_draft"
  | "reply"
  | "workflow_run"
  | "audit_log"
  | "do_not_contact"
  | "external_draft"
  | "outreach"
  | "qualification"
  | "sourcing_candidate";

export type RetentionAction = "delete" | "anonymize" | "archive";

export type RetentionRunStatus = "running" | "completed" | "failed" | "cancelled";

export interface DataRetentionPolicy {
  id: string;
  name: string;
  entity_type: RetentionEntityType;
  retention_days: number;
  action: RetentionAction;
  is_active: boolean;
  dry_run_default: boolean;
  created_by_user_id: string | null;
  created_at: string;
  updated_at: string;
}

export interface DataRetentionPolicyListResponse {
  items: DataRetentionPolicy[];
  limit: number;
  offset: number;
}

export interface CreateDataRetentionPolicyRequest {
  name: string;
  entity_type: RetentionEntityType;
  retention_days: number;
  action?: RetentionAction;
  dry_run_default?: boolean;
}

export interface UpdateDataRetentionPolicyRequest {
  name?: string | null;
  retention_days?: number | null;
  action?: RetentionAction | null;
  dry_run_default?: boolean | null;
}

export interface DataRetentionRun {
  id: string;
  policy_id: string;
  entity_type: RetentionEntityType;
  action: RetentionAction;
  dry_run: boolean;
  status: RetentionRunStatus;
  started_by_user_id: string | null;
  started_at: string | null;
  completed_at: string | null;
  total_scanned: number;
  total_eligible: number;
  total_processed: number;
  total_failed: number;
  warnings: string[];
  errors: string[];
  created_at: string;
  updated_at: string;
}

export interface DataRetentionRunListResponse {
  items: DataRetentionRun[];
  limit: number;
  offset: number;
}

export type DataRetentionRunDetailResponse = DataRetentionRun;

export interface RunDataRetentionPolicyRequest {
  confirm: boolean;
}

export interface DataExportRequest {
  email?: string | null;
  domain?: string | null;
  name?: string | null;
}

export interface DataExportResponse {
  query: DataExportRequest;
  generated_at: string;
  leads: Record<string, unknown>[];
  companies: Record<string, unknown>[];
  email_drafts: Record<string, unknown>[];
  replies: Record<string, unknown>[];
  workflow_runs: Record<string, unknown>[];
  outreach_queue_items: Record<string, unknown>[];
  dispatches: Record<string, unknown>[];
  do_not_contact_entries: Record<string, unknown>[];
  audit_log_references: Record<string, unknown>[];
  message: string;
}

export type DataRequestType =
  | "export"
  | "delete"
  | "anonymize"
  | "do_not_contact"
  | "correction";

export type DataRequestStatus =
  | "open"
  | "in_progress"
  | "completed"
  | "rejected"
  | "cancelled";

export interface DataSubjectRequest {
  id: string;
  request_type: DataRequestType;
  subject_email: string | null;
  subject_domain: string | null;
  subject_name: string | null;
  status: DataRequestStatus;
  requested_by_user_id: string | null;
  handled_by_user_id: string | null;
  notes: string | null;
  result_summary: string | null;
  created_at: string;
  updated_at: string;
  completed_at: string | null;
}

export interface DataSubjectRequestListResponse {
  items: DataSubjectRequest[];
  limit: number;
  offset: number;
}

export interface DataSubjectRequestDetailResponse {
  request: DataSubjectRequest;
  export: DataExportResponse | null;
}

export interface CreateDataSubjectRequestRequest {
  request_type: DataRequestType;
  subject_email?: string | null;
  subject_domain?: string | null;
  subject_name?: string | null;
  notes?: string | null;
}

export interface UpdateDataSubjectRequestRequest {
  status?: DataRequestStatus | null;
  notes?: string | null;
  result_summary?: string | null;
}

export interface PrepareAnonymizeDataRequestResponse {
  request: DataSubjectRequest;
  message: string;
  matched_lead_candidate_ids: string[];
  matched_contact_ids: string[];
}

export interface CompleteDataRequestRequest {
  result_summary?: string | null;
}

// -- quality scoring / feedback / beta test -----------------------------------------
// Quality scores and feedback are decision support only — never a
// guarantee, and never a substitute for Human Review or Do-not-contact.
// 'beta_ready' is a technical signal only, never a legal clearance.

export type QualityEntityType =
  | "lead_candidate"
  | "crm_lead"
  | "company"
  | "email_draft"
  | "workflow_run"
  | "outreach_queue_item"
  | "dispatch"
  | "reply"
  | "qualification_result";

export type QualityScoreLevel =
  | "excellent"
  | "good"
  | "acceptable"
  | "weak"
  | "poor"
  | "blocked";

export type QualityEvaluatedBy = "system" | "user" | "mock" | "llm";

export interface QualityScore {
  id: string;
  entity_type: QualityEntityType;
  entity_id: string;
  workflow_run_id?: string | null;
  email_draft_id?: string | null;
  lead_id?: string | null;
  company_id?: string | null;
  lead_candidate_id?: string | null;
  qualification_result_id?: string | null;
  outreach_queue_item_id?: string | null;
  reply_id?: string | null;
  score_total: number;
  score_level: QualityScoreLevel;
  score_breakdown: Record<string, unknown>;
  strengths: string[];
  weaknesses: string[];
  warnings: string[];
  recommended_improvements: string[];
  compliance_flags: string[];
  evaluated_by: QualityEvaluatedBy;
  evaluated_by_user_id?: string | null;
  provider: string;
  created_at: string;
  updated_at: string;
}

export interface QualityScoreListResponse {
  items: QualityScore[];
  limit: number;
  offset: number;
}

export interface CreateQualityScoreRequest {
  entity_type: QualityEntityType;
  entity_id: string;
}

export type QualityFeedbackType =
  | "positive"
  | "negative"
  | "correction"
  | "bug"
  | "quality_issue"
  | "compliance_issue"
  | "missing_context"
  | "wrong_target"
  | "bad_copy"
  | "good_result";

export type QualityFeedbackReviewStatus =
  | "open"
  | "reviewed"
  | "accepted"
  | "rejected"
  | "archived";

export type QualityFeedbackPriority = "low" | "medium" | "high";

// Feedback may be given about anything Quality Scoring can score, plus a
// Real-World Test Run, plus general/UI feedback not tied to a single
// record (entity_id is null in that case).
export type FeedbackEntityType = QualityEntityType | "real_world_test_run" | "general";

export interface QualityFeedback {
  id: string;
  entity_type: FeedbackEntityType;
  entity_id?: string | null;
  workflow_run_id?: string | null;
  email_draft_id?: string | null;
  lead_id?: string | null;
  company_id?: string | null;
  lead_candidate_id?: string | null;
  qualification_result_id?: string | null;
  outreach_queue_item_id?: string | null;
  reply_id?: string | null;
  real_world_test_run_id?: string | null;
  rating: number;
  feedback_type: QualityFeedbackType;
  priority: QualityFeedbackPriority;
  feedback_text?: string | null;
  issue_tags: string[];
  improvement_tags: string[];
  is_blocking: boolean;
  submitted_by_user_id?: string | null;
  reviewed_by_user_id?: string | null;
  review_status: QualityFeedbackReviewStatus;
  created_at: string;
  updated_at: string;
}

export interface QualityFeedbackListResponse {
  items: QualityFeedback[];
  limit: number;
  offset: number;
}

export interface QualityFeedbackDetailResponse {
  feedback: QualityFeedback;
}

export interface CreateQualityFeedbackRequest {
  entity_type: FeedbackEntityType;
  // Required unless entity_type is "general".
  entity_id?: string | null;
  rating: number;
  feedback_type: QualityFeedbackType;
  priority?: QualityFeedbackPriority;
  feedback_text?: string | null;
  issue_tags?: string[];
  improvement_tags?: string[];
  is_blocking?: boolean;
  workflow_run_id?: string | null;
  email_draft_id?: string | null;
  lead_id?: string | null;
  company_id?: string | null;
  lead_candidate_id?: string | null;
  qualification_result_id?: string | null;
  outreach_queue_item_id?: string | null;
  reply_id?: string | null;
  real_world_test_run_id?: string | null;
}

export interface ReviewQualityFeedbackRequest {
  review_status: "reviewed" | "accepted" | "rejected";
}

export type BetaReadinessLevel =
  | "not_ready"
  | "needs_improvement"
  | "beta_testable"
  | "beta_ready";

export interface QualityStatusResponse {
  quality_feedback_enabled: boolean;
  quality_scoring_enabled: boolean;
  quality_scoring_provider: string;
  quality_scoring_use_llm: boolean;
  min_draft_score: number;
  min_lead_score: number;
  min_workflow_score: number;
  auto_score_drafts: boolean;
  auto_score_workflows: boolean;
  require_human_feedback_for_beta: boolean;
  message: string;
}

export interface QualityIssueSummary {
  tag: string;
  count: number;
}

export interface EntityScoreSummary {
  entity_type: QualityEntityType;
  entity_id: string;
  score_total: number;
  score_level: QualityScoreLevel;
}

export interface QualityDashboardResponse {
  average_draft_quality_score?: number | null;
  average_lead_quality_score?: number | null;
  average_workflow_quality_score?: number | null;
  total_feedback_items: number;
  open_feedback_items: number;
  blocking_feedback_items: number;
  top_quality_issues: QualityIssueSummary[];
  top_improvement_suggestions: QualityIssueSummary[];
  best_performing_drafts: EntityScoreSummary[];
  weakest_drafts: EntityScoreSummary[];
  best_leads: EntityScoreSummary[];
  weakest_leads: EntityScoreSummary[];
  beta_readiness_level: BetaReadinessLevel;
  warnings: string[];
  message: string;
}

export type BetaSessionStatus = "planned" | "running" | "completed" | "cancelled";

export interface BetaTestSession {
  id: string;
  name: string;
  description?: string | null;
  tester_user_id?: string | null;
  status: BetaSessionStatus;
  started_at?: string | null;
  completed_at?: string | null;
  target_goal?: string | null;
  total_workflows_tested: number;
  total_drafts_reviewed: number;
  total_feedback_items: number;
  average_quality_score?: number | null;
  blockers_count: number;
  bugs_count: number;
  notes?: string | null;
  created_at: string;
  updated_at: string;
}

export interface BetaTestSessionListResponse {
  items: BetaTestSession[];
  limit: number;
  offset: number;
}

export interface CreateBetaTestSessionRequest {
  name: string;
  description?: string | null;
  target_goal?: string | null;
}

export interface BetaTestDashboardResponse {
  sessions_count: number;
  running_sessions_count: number;
  completed_sessions_count: number;
  average_quality_score?: number | null;
  total_feedback_items: number;
  open_feedback_items: number;
  blocking_feedback_items: number;
  total_bugs: number;
  readiness_level: BetaReadinessLevel;
  recommendations: string[];
  warnings: string[];
  message: string;
}

// -- real-world test mode (Phase 34) -------------------------------------------------
// Controlled test runs against real leads/websites and, optionally, real
// LLM output. Never sends an email, never creates an external draft
// automatically, and never bypasses Do-not-contact or Human Review.

export type RealWorldTestRunMode = "safe" | "mock" | "real_llm";

export type RealWorldTestRunStatus =
  | "pending"
  | "running"
  | "completed"
  | "blocked"
  | "failed"
  | "aborted";

export interface RealWorldTestRun {
  id: string;
  name: string;
  status: RealWorldTestRunStatus;
  mode: RealWorldTestRunMode;
  lead_candidate_id?: string | null;
  lead_id?: string | null;
  icp_profile_id?: string | null;
  offer_profile_id?: string | null;
  workflow_run_id?: string | null;
  quality_score_id?: string | null;
  input_snapshot: Record<string, unknown>;
  result_snapshot: Record<string, unknown>;
  warnings: string[];
  errors: string[];
  created_by_user_id?: string | null;
  aborted_at?: string | null;
  created_at: string;
  updated_at: string;
}

export interface RealWorldTestRunListResponse {
  items: RealWorldTestRun[];
  limit: number;
  offset: number;
}

export interface CreateRealWorldTestRunRequest {
  name: string;
  mode?: RealWorldTestRunMode;
  lead_candidate_id?: string | null;
  lead_id?: string | null;
  icp_profile_id?: string | null;
  offer_profile_id?: string | null;
  company_name?: string | null;
  website_url?: string | null;
  industry?: string | null;
  product_or_service_offered?: string | null;
  notes?: string | null;
}

// -- Lead Finder / Lead Discovery Run ------------------------------------------------
// A guided pipeline: given a target customer, region, and offer, finds
// candidate companies, analyzes their public websites, and scores fit —
// reusing Lead Sourcing, Lead Qualification, and Outreach Queue rather
// than duplicating any of their logic. Draft creation is a separate,
// explicit follow-up action. Never sends anything, never contacts anyone
// automatically, and never bypasses Do-not-contact or Human Review.

export type LeadDiscoveryMode = "safe" | "mock" | "real_llm";

export type LeadDiscoveryRunStatus = "pending" | "running" | "completed" | "failed";

export interface LeadDiscoveryRun {
  id: string;
  name: string;
  target_customer: string;
  region: string | null;
  offer_profile_id: string | null;
  icp_profile_id: string | null;
  requested_count: number;
  min_score: number;
  mode: LeadDiscoveryMode;
  status: LeadDiscoveryRunStatus;
  lead_sourcing_campaign_id: string | null;
  lead_sourcing_run_id: string | null;
  outreach_campaign_id: string | null;
  found_candidates: number;
  analyzed_websites: number;
  qualified_leads: number;
  rejected_leads: number;
  created_drafts: number;
  warnings: string[];
  errors: string[];
  created_by_user_id: string | null;
  started_at: string | null;
  completed_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface CreateLeadDiscoveryRunRequest {
  name?: string | null;
  target_customer: string;
  region?: string | null;
  offer_profile_id: string;
  icp_profile_id?: string | null;
  requested_count?: number;
  min_score?: number;
  mode?: LeadDiscoveryMode;
}

export interface LeadDiscoveryRunListResponse {
  items: LeadDiscoveryRun[];
  limit: number;
  offset: number;
}

export type LeadDiscoveryDraftStatus = "none" | "prepared" | "review_pending";

export interface LeadDiscoveryCandidateSummary {
  candidate_id: string;
  company_name: string | null;
  company_domain: string | null;
  company_website_url: string | null;
  industry: string | null;
  location: string | null;
  website_quality_level: string | null;
  website_quality_reasons: string[];
  icp_fit_score: number | null;
  icp_fit_level: string | null;
  qualification_score: number | null;
  qualification_level: string | null;
  qualification_status: string | null;
  fit_summary: string | null;
  positive_signals: string[];
  negative_signals: string[];
  do_not_contact_status: string;
  duplicate_status: string;
  review_status: string;
  in_outreach_queue: boolean;
  draft_status: LeadDiscoveryDraftStatus;
  email_draft_id: string | null;
  warnings: string[];
}

export interface LeadDiscoveryRunDetail extends LeadDiscoveryRun {
  candidates: LeadDiscoveryCandidateSummary[];
}

export interface AddCandidateToQueueResponse {
  run: LeadDiscoveryRunDetail;
  added: boolean;
  warnings: string[];
}
