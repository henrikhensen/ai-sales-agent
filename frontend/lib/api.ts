import type {
  ApproveLeadCandidateRequest,
  ApproveLeadCandidateResponse,
  AuditLogDetailResponse,
  AuditLogFilters,
  AuditLogListResponse,
  BackupStatus,
  BuildOutreachQueueRequest,
  BuildOutreachQueueResponse,
  Company,
  ComplianceStatus,
  Contact,
  CreateDoNotContactRequest,
  CreateExternalEmailDraftResponse,
  CreateICPProfileRequest,
  CreateLeadSourcingCampaignRequest,
  CreateOfferProfileRequest,
  CreateOutreachCampaignRequest,
  DoNotContactCheckRequest,
  DoNotContactCheckResponse,
  DoNotContactEntry,
  DoNotContactListResponse,
  EmailDraftRecord,
  EmailDraftReviewStatusResponse,
  EmailDraftReviewStatusUpdateRequest,
  EmailIntegrationProvider,
  EmailIntegrationProvidersResponse,
  EmailIntegrationStatus,
  ExternalEmailDraftStatusResponse,
  HealthResponse,
  ICPFitCheckRequest,
  ICPFitCheckResponse,
  ICPProfile,
  ICPProfileListResponse,
  ImportLeadCandidatesRequest,
  ImportLeadCandidatesResponse,
  Interaction,
  Lead,
  LeadCandidate,
  LeadCandidateListResponse,
  LeadQualificationResult,
  LeadQualificationResultListResponse,
  LeadQualificationRun,
  LeadQualificationRunListResponse,
  LeadQualificationStatus,
  LeadSourcingCampaign,
  LeadSourcingCampaignListResponse,
  LeadSourcingProviderStatus,
  LeadSourcingRun,
  LeadSourcingRunListResponse,
  ListSalesWorkflowRunsParams,
  LLMProviderStatus,
  LLMProviderTestResponse,
  LoginRequest,
  Metrics,
  OfferPreviewRequest,
  OfferPreviewResponse,
  OfferProfile,
  OfferProfileListResponse,
  OutreachCampaign,
  OutreachCampaignListResponse,
  OutreachQueueDashboardResponse,
  OutreachQueueItem,
  OutreachQueueItemListResponse,
  OutreachQueueStatusInfo,
  PipelineBoardResponse,
  PipelineStatus,
  PrepareQueueBatchRequest,
  PrepareQueueBatchResponse,
  PrepareQueueItemWorkflowRequest,
  PrepareQueueItemWorkflowResponse,
  QualificationDashboardResponse,
  QualificationReviewRequest,
  QualificationReviewResponse,
  QualifyCRMLeadRequest,
  QualifyLeadCandidateRequest,
  RegisterRequest,
  RejectLeadCandidateRequest,
  RejectLeadCandidateResponse,
  ReplyDetailResponse,
  ReplyIntegrationStatus,
  ReplyListResponse,
  ReviewEventListResponse,
  SalesWorkflowRequest,
  SalesWorkflowResponse,
  StartEmailProviderConnectionResponse,
  StartLeadQualificationRequest,
  StartLeadQualificationResponse,
  StartLeadSourcingRunRequest,
  StartLeadSourcingRunResponse,
  SyncRepliesResponse,
  SystemStatus,
  TokenResponse,
  UpdateDoNotContactRequest,
  UpdateICPProfileRequest,
  UpdateLeadPipelineStatusRequest,
  UpdateLeadPipelineStatusResponse,
  UpdateLeadSourcingCampaignRequest,
  UpdateOfferProfileRequest,
  UpdateOutreachCampaignRequest,
  UpdateOutreachCampaignStatusRequest,
  UpdateQueueItemStatusRequest,
  UpdateQueueItemStatusResponse,
  UpdateWorkflowReviewStatusRequest,
  UpdateWorkflowReviewStatusResponse,
  User,
  UserListResponse,
  WebsiteResearchRequest,
  WebsiteResearchResponse,
  WorkflowCommentRequest,
  WorkflowCommentResponse,
  WorkflowCrmLinks,
  WorkflowReviewStatus,
  WorkflowRunDetail,
  WorkflowRunListResponse,
} from "./types";

// Client-side requests run in the user's browser, not inside the Docker
// network, so this must be a URL the browser can reach (e.g. the backend's
// published host port), not an internal container hostname.
export const API_BASE_URL = (
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000"
).replace(/\/+$/, "");

export class ApiError extends Error {
  readonly status: number;
  readonly detail: unknown;

  constructor(message: string, status: number, detail?: unknown) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.detail = detail;
  }
}

// -- Auth token storage -------------------------------------------------------
// Local MVP only: the JWT access token is kept in localStorage, never
// logged, and never sent anywhere except as the Authorization header on
// requests to this backend. No external auth provider, no OAuth.

const AUTH_TOKEN_STORAGE_KEY = "ai_sales_agent_auth_token";

export function getAuthToken(): string | null {
  if (typeof window === "undefined") {
    return null;
  }
  try {
    return window.localStorage.getItem(AUTH_TOKEN_STORAGE_KEY);
  } catch {
    return null;
  }
}

export function setAuthToken(token: string): void {
  if (typeof window === "undefined") {
    return;
  }
  try {
    window.localStorage.setItem(AUTH_TOKEN_STORAGE_KEY, token);
  } catch {
    // Ignore storage errors (e.g. private browsing quota) — the session
    // simply won't persist across reloads in that case.
  }
}

export function clearAuthToken(): void {
  if (typeof window === "undefined") {
    return;
  }
  try {
    window.localStorage.removeItem(AUTH_TOKEN_STORAGE_KEY);
  } catch {
    // Ignore.
  }
}

// Fired whenever any request comes back 401 (missing/invalid/expired
// token). AuthProvider listens for this to clear the in-memory user, which
// makes RequireAuth/RequireRole redirect to /login on their next render —
// without this, a token that expires mid-session would otherwise only be
// noticed the next time /auth/me happens to be called.
export const AUTH_UNAUTHORIZED_EVENT = "ai-sales-agent:unauthorized";

function notifyUnauthorized(): void {
  if (typeof window === "undefined") {
    return;
  }
  window.dispatchEvent(new Event(AUTH_UNAUTHORIZED_EVENT));
}

function extractDetailMessage(detail: unknown): string | null {
  if (typeof detail === "string") {
    return detail;
  }
  if (Array.isArray(detail)) {
    // FastAPI validation errors: [{ loc, msg, type }, ...]
    const messages = detail
      .map((item) =>
        item && typeof item === "object" && "msg" in item
          ? String((item as { msg: unknown }).msg)
          : null
      )
      .filter((msg): msg is string => Boolean(msg));
    return messages.length > 0 ? messages.join("; ") : null;
  }
  return null;
}

async function request<TResponse>(
  path: string,
  init?: RequestInit
): Promise<TResponse> {
  const token = getAuthToken();

  let response: Response;
  try {
    response = await fetch(`${API_BASE_URL}${path}`, {
      ...init,
      headers: {
        "Content-Type": "application/json",
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
        ...(init?.headers ?? {}),
      },
      cache: "no-store",
    });
  } catch {
    throw new ApiError(
      `Backend unter ${API_BASE_URL} ist nicht erreichbar. Läuft das Backend?`,
      0
    );
  }

  const contentType = response.headers.get("content-type") ?? "";
  const body = contentType.includes("application/json")
    ? await response.json().catch(() => null)
    : null;

  if (!response.ok) {
    const detail =
      body && typeof body === "object" && "detail" in body
        ? (body as { detail: unknown }).detail
        : null;
    const message =
      extractDetailMessage(detail) ??
      `Anfrage fehlgeschlagen (Status ${response.status})`;

    if (response.status === 401) {
      // Missing/invalid/expired token, or the account no longer exists:
      // drop it and let AuthProvider notice so the app redirects to
      // /login. A 403 (wrong role, valid token) never logs the user out.
      clearAuthToken();
      notifyUnauthorized();
    }

    throw new ApiError(message, response.status, detail ?? body);
  }

  return body as TResponse;
}

export function getJson<TResponse>(path: string): Promise<TResponse> {
  return request<TResponse>(path, { method: "GET" });
}

export function postJson<TResponse, TBody = unknown>(
  path: string,
  payload: TBody
): Promise<TResponse> {
  return request<TResponse>(path, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function patchJson<TResponse, TBody = unknown>(
  path: string,
  payload: TBody
): Promise<TResponse> {
  return request<TResponse>(path, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
}

export function checkHealth(): Promise<HealthResponse> {
  return getJson<HealthResponse>("/api/v1/health");
}

export function runSalesWorkflow(
  payload: SalesWorkflowRequest
): Promise<SalesWorkflowResponse> {
  return postJson<SalesWorkflowResponse, SalesWorkflowRequest>(
    "/api/v1/workflows/sales",
    payload
  );
}

export function listSalesWorkflowRuns(
  params?: ListSalesWorkflowRunsParams
): Promise<WorkflowRunListResponse> {
  const query = new URLSearchParams();
  if (params?.limit !== undefined) query.set("limit", String(params.limit));
  if (params?.offset !== undefined) query.set("offset", String(params.offset));
  if (params?.company_name) query.set("company_name", params.company_name);
  if (params?.review_status) query.set("review_status", params.review_status);

  const queryString = query.toString();
  return getJson<WorkflowRunListResponse>(
    `/api/v1/workflows/sales/runs${queryString ? `?${queryString}` : ""}`
  );
}

export function getSalesWorkflowRun(
  workflowId: string
): Promise<WorkflowRunDetail> {
  return getJson<WorkflowRunDetail>(
    `/api/v1/workflows/sales/runs/${encodeURIComponent(workflowId)}`
  );
}

export function updateSalesWorkflowReviewStatus(
  workflowId: string,
  reviewStatus: WorkflowReviewStatus
): Promise<UpdateWorkflowReviewStatusResponse> {
  return patchJson<UpdateWorkflowReviewStatusResponse, UpdateWorkflowReviewStatusRequest>(
    `/api/v1/workflows/sales/runs/${encodeURIComponent(workflowId)}/review-status`,
    { review_status: reviewStatus }
  );
}

export function getWorkflowCrmLinks(workflowId: string): Promise<WorkflowCrmLinks> {
  return getJson<WorkflowCrmLinks>(
    `/api/v1/workflows/sales/runs/${encodeURIComponent(workflowId)}/crm-links`
  );
}

// -- CRM (Companies, Leads, Contacts, Interactions, Email Drafts) -----------
// Read-only: these endpoints only ever list data the sales workflow (or the
// existing Companies/Leads create endpoints) already stored. Nothing here
// sends an email, contacts anyone, or books a meeting.

export function listCrmCompanies(): Promise<Company[]> {
  return getJson<Company[]>("/api/v1/companies");
}

export function listCrmLeads(): Promise<Lead[]> {
  return getJson<Lead[]>("/api/v1/leads");
}

export function listCrmContacts(): Promise<Contact[]> {
  return getJson<Contact[]>("/api/v1/contacts");
}

export function listCrmInteractions(): Promise<Interaction[]> {
  return getJson<Interaction[]>("/api/v1/interactions");
}

export function listCrmEmailDrafts(): Promise<EmailDraftRecord[]> {
  return getJson<EmailDraftRecord[]>("/api/v1/email-drafts");
}

// -- Human Review & Approval --------------------------------------------
// Read/write endpoints for internal review only: no function here ever
// sends an email, contacts anyone, or books a meeting. "Approved" means a
// human has internally reviewed the item, nothing more.

export function updateEmailDraftReviewStatus(
  emailDraftId: string,
  payload: EmailDraftReviewStatusUpdateRequest
): Promise<EmailDraftReviewStatusResponse> {
  return postJson<EmailDraftReviewStatusResponse, EmailDraftReviewStatusUpdateRequest>(
    `/api/v1/reviews/email-drafts/${encodeURIComponent(emailDraftId)}/status`,
    payload
  );
}

export function listEmailDraftReviewEvents(
  emailDraftId: string
): Promise<ReviewEventListResponse> {
  return getJson<ReviewEventListResponse>(
    `/api/v1/reviews/email-drafts/${encodeURIComponent(emailDraftId)}/events`
  );
}

export function addWorkflowReviewComment(
  workflowId: string,
  payload: WorkflowCommentRequest
): Promise<WorkflowCommentResponse> {
  return postJson<WorkflowCommentResponse, WorkflowCommentRequest>(
    `/api/v1/reviews/workflows/${encodeURIComponent(workflowId)}/comment`,
    payload
  );
}

export function listWorkflowReviewEvents(
  workflowId: string
): Promise<ReviewEventListResponse> {
  return getJson<ReviewEventListResponse>(
    `/api/v1/reviews/workflows/${encodeURIComponent(workflowId)}/events`
  );
}

// -- Auth (local JWT — no external provider, no OAuth) -----------------------
// No email is ever sent by these endpoints, including registration.

export function registerUser(payload: RegisterRequest): Promise<User> {
  return postJson<User, RegisterRequest>("/api/v1/auth/register", payload);
}

export function loginUser(payload: LoginRequest): Promise<TokenResponse> {
  return postJson<TokenResponse, LoginRequest>("/api/v1/auth/login", payload);
}

export function getCurrentUser(): Promise<User> {
  return getJson<User>("/api/v1/auth/me");
}

export function getUsers(): Promise<UserListResponse> {
  return getJson<UserListResponse>("/api/v1/users");
}

// -- LLM Provider Settings ----------------------------------------------------
// Read-only status plus an admin-only, backend-guarded test call. Neither
// function ever sends, stores, or displays an API key — the backend itself
// never returns one (see backend/api/v1/schemas/settings.py).

export function getLlmProviderStatus(): Promise<LLMProviderStatus> {
  return getJson<LLMProviderStatus>("/api/v1/settings/llm/status");
}

export function testLlmProvider(): Promise<LLMProviderTestResponse> {
  return postJson<LLMProviderTestResponse, undefined>(
    "/api/v1/settings/llm/test",
    undefined
  );
}

// -- Website Research ---------------------------------------------------------
// Fetches only the exact public URL supplied in payload.url. No LLM call, no
// automatic mass research, no LinkedIn scraping, no automatic contact.

export function researchWebsite(
  payload: WebsiteResearchRequest
): Promise<WebsiteResearchResponse> {
  return postJson<WebsiteResearchResponse, WebsiteResearchRequest>(
    "/api/v1/research/website",
    payload
  );
}

// -- CRM Pipeline ---------------------------------------------------------
// Changing a lead's pipeline status is bookkeeping only: it never sends an
// email or makes contact. "approved" means only that a human has internally
// reviewed the lead's workflow run, never that anything was sent.

export function getCrmPipeline(): Promise<PipelineBoardResponse> {
  return getJson<PipelineBoardResponse>("/api/v1/crm/pipeline");
}

export function updateLeadPipelineStatus(
  leadId: string,
  pipelineStatus: PipelineStatus
): Promise<UpdateLeadPipelineStatusResponse> {
  return patchJson<UpdateLeadPipelineStatusResponse, UpdateLeadPipelineStatusRequest>(
    `/api/v1/crm/leads/${encodeURIComponent(leadId)}/pipeline-status`,
    { pipeline_status: pipelineStatus }
  );
}

// -- Do-not-contact (opt-out) compliance ---------------------------------------
// Blocking an email/domain/company here never sends an email or contacts
// anyone by itself — it only ever stops the Sales Workflow from creating an
// Email Draft and stops Review Approval from succeeding.

export function getDoNotContactEntries(
  limit = 100,
  offset = 0
): Promise<DoNotContactListResponse> {
  return getJson<DoNotContactListResponse>(
    `/api/v1/compliance/do-not-contact?limit=${limit}&offset=${offset}`
  );
}

export function createDoNotContactEntry(
  payload: CreateDoNotContactRequest
): Promise<DoNotContactEntry> {
  return postJson<DoNotContactEntry, CreateDoNotContactRequest>(
    "/api/v1/compliance/do-not-contact",
    payload
  );
}

export function updateDoNotContactEntry(
  entryId: string,
  payload: UpdateDoNotContactRequest
): Promise<DoNotContactEntry> {
  return patchJson<DoNotContactEntry, UpdateDoNotContactRequest>(
    `/api/v1/compliance/do-not-contact/${encodeURIComponent(entryId)}`,
    payload
  );
}

export function deactivateDoNotContactEntry(entryId: string): Promise<DoNotContactEntry> {
  return patchJson<DoNotContactEntry, undefined>(
    `/api/v1/compliance/do-not-contact/${encodeURIComponent(entryId)}/deactivate`,
    undefined
  );
}

export function checkDoNotContact(
  payload: DoNotContactCheckRequest
): Promise<DoNotContactCheckResponse> {
  return postJson<DoNotContactCheckResponse, DoNotContactCheckRequest>(
    "/api/v1/compliance/do-not-contact/check",
    payload
  );
}

// -- Gmail/Outlook Draft Integration --------------------------------------------
// Every function here only ever creates a *draft* at Gmail/Outlook/Mock —
// there is no send capability anywhere in this integration.

export function getEmailIntegrationStatus(): Promise<EmailIntegrationStatus> {
  return getJson<EmailIntegrationStatus>("/api/v1/integrations/email/status");
}

export function getEmailIntegrationProviders(): Promise<EmailIntegrationProvidersResponse> {
  return getJson<EmailIntegrationProvidersResponse>(
    "/api/v1/integrations/email/providers"
  );
}

export function startEmailProviderConnection(
  provider: EmailIntegrationProvider
): Promise<StartEmailProviderConnectionResponse> {
  return postJson<StartEmailProviderConnectionResponse, undefined>(
    `/api/v1/integrations/email/${encodeURIComponent(provider)}/connect/start`,
    undefined
  );
}

export function disconnectEmailProvider(
  provider: EmailIntegrationProvider
): Promise<{ provider: string; status: string }> {
  return postJson<{ provider: string; status: string }, undefined>(
    `/api/v1/integrations/email/disconnect?provider=${encodeURIComponent(provider)}`,
    undefined
  );
}

export function createExternalEmailDraft(
  draftId: string
): Promise<CreateExternalEmailDraftResponse> {
  return postJson<CreateExternalEmailDraftResponse, undefined>(
    `/api/v1/email-drafts/${encodeURIComponent(draftId)}/external-draft`,
    undefined
  );
}

export function getExternalEmailDraftStatus(
  draftId: string
): Promise<ExternalEmailDraftStatusResponse> {
  return getJson<ExternalEmailDraftStatusResponse>(
    `/api/v1/email-drafts/${encodeURIComponent(draftId)}/external-draft`
  );
}

// -- Reply Inbox / Reply Tracking -----------------------------------------------
// Every function here only ever reads messages that already exist in a
// connected mailbox (Mock by default) — there is no reply/send capability
// anywhere in this integration.

export interface ReplyFilters {
  category?: string;
  sentiment?: string;
  is_read?: boolean;
  is_archived?: boolean;
  limit?: number;
  offset?: number;
}

export function getReplies(filters: ReplyFilters = {}): Promise<ReplyListResponse> {
  const params = new URLSearchParams();
  if (filters.category) params.set("category", filters.category);
  if (filters.sentiment) params.set("sentiment", filters.sentiment);
  if (filters.is_read !== undefined) params.set("is_read", String(filters.is_read));
  if (filters.is_archived !== undefined) {
    params.set("is_archived", String(filters.is_archived));
  }
  params.set("limit", String(filters.limit ?? 100));
  params.set("offset", String(filters.offset ?? 0));
  return getJson<ReplyListResponse>(`/api/v1/replies?${params.toString()}`);
}

export function getReply(replyId: string): Promise<ReplyDetailResponse> {
  return getJson<ReplyDetailResponse>(`/api/v1/replies/${encodeURIComponent(replyId)}`);
}

export function markReplyRead(
  replyId: string,
  isRead = true
): Promise<ReplyDetailResponse> {
  return patchJson<ReplyDetailResponse, undefined>(
    `/api/v1/replies/${encodeURIComponent(replyId)}/read?is_read=${isRead}`,
    undefined
  );
}

export function archiveReply(
  replyId: string,
  isArchived = true
): Promise<ReplyDetailResponse> {
  return patchJson<ReplyDetailResponse, undefined>(
    `/api/v1/replies/${encodeURIComponent(replyId)}/archive?is_archived=${isArchived}`,
    undefined
  );
}

export function getLeadReplies(
  leadId: string,
  limit = 100,
  offset = 0
): Promise<ReplyListResponse> {
  return getJson<ReplyListResponse>(
    `/api/v1/leads/${encodeURIComponent(leadId)}/replies?limit=${limit}&offset=${offset}`
  );
}

export function syncLeadReplies(leadId: string): Promise<SyncRepliesResponse> {
  return postJson<SyncRepliesResponse, undefined>(
    `/api/v1/leads/${encodeURIComponent(leadId)}/replies/sync`,
    undefined
  );
}

export function syncDraftReplies(draftId: string): Promise<SyncRepliesResponse> {
  return postJson<SyncRepliesResponse, undefined>(
    `/api/v1/email-drafts/${encodeURIComponent(draftId)}/replies/sync`,
    undefined
  );
}

export function syncRecentReplies(): Promise<SyncRepliesResponse> {
  return postJson<SyncRepliesResponse, undefined>(
    "/api/v1/replies/sync-recent",
    undefined
  );
}

export function getReplyIntegrationStatus(): Promise<ReplyIntegrationStatus> {
  return getJson<ReplyIntegrationStatus>("/api/v1/integrations/replies/status");
}

// -- Deployment / Monitoring / Backups --------------------------------------
// Admin-only. Never includes a secret, API key, or token.

export function getSystemStatus(): Promise<SystemStatus> {
  return getJson<SystemStatus>("/api/v1/system/status");
}

export function getBackupStatus(): Promise<BackupStatus> {
  return getJson<BackupStatus>("/api/v1/system/backups/status");
}

export function getMetrics(): Promise<Metrics> {
  return getJson<Metrics>("/api/v1/metrics");
}

// -- Compliance Hardening / Audit Logs --------------------------------------
// Never includes a secret, API key, or token.

export function getComplianceStatus(): Promise<ComplianceStatus> {
  return getJson<ComplianceStatus>("/api/v1/compliance/status");
}

export function getAuditLogs(
  filters: AuditLogFilters = {}
): Promise<AuditLogListResponse> {
  const params = new URLSearchParams();
  if (filters.actor_user_id) params.set("actor_user_id", filters.actor_user_id);
  if (filters.action) params.set("action", filters.action);
  if (filters.entity_type) params.set("entity_type", filters.entity_type);
  if (filters.entity_id) params.set("entity_id", filters.entity_id);
  if (filters.result) params.set("result", filters.result);
  if (filters.date_from) params.set("date_from", filters.date_from);
  if (filters.date_to) params.set("date_to", filters.date_to);
  params.set("limit", String(filters.limit ?? 100));
  params.set("offset", String(filters.offset ?? 0));
  return getJson<AuditLogListResponse>(`/api/v1/audit-logs?${params.toString()}`);
}

export function getAuditLog(auditLogId: string): Promise<AuditLogDetailResponse> {
  return getJson<AuditLogDetailResponse>(
    `/api/v1/audit-logs/${encodeURIComponent(auditLogId)}`
  );
}

// -- ICP (Ideal Customer Profile) --------------------------------------------
// Never scrapes or fetches new external data — only scores data already
// supplied in the request.

export function getICPProfiles(activeOnly = false): Promise<ICPProfileListResponse> {
  return getJson<ICPProfileListResponse>(
    `/api/v1/sales-strategy/icp?active_only=${activeOnly}`
  );
}

export function getICPProfile(icpId: string): Promise<ICPProfile> {
  return getJson<ICPProfile>(`/api/v1/sales-strategy/icp/${encodeURIComponent(icpId)}`);
}

export function createICPProfile(
  payload: CreateICPProfileRequest
): Promise<ICPProfile> {
  return postJson<ICPProfile, CreateICPProfileRequest>(
    "/api/v1/sales-strategy/icp",
    payload
  );
}

export function updateICPProfile(
  icpId: string,
  payload: UpdateICPProfileRequest
): Promise<ICPProfile> {
  return patchJson<ICPProfile, UpdateICPProfileRequest>(
    `/api/v1/sales-strategy/icp/${encodeURIComponent(icpId)}`,
    payload
  );
}

export function deactivateICPProfile(icpId: string): Promise<ICPProfile> {
  return patchJson<ICPProfile, undefined>(
    `/api/v1/sales-strategy/icp/${encodeURIComponent(icpId)}/deactivate`,
    undefined
  );
}

export function checkICPFit(
  payload: ICPFitCheckRequest
): Promise<ICPFitCheckResponse> {
  return postJson<ICPFitCheckResponse, ICPFitCheckRequest>(
    "/api/v1/sales-strategy/icp/check-fit",
    payload
  );
}

// -- Offer profiles -----------------------------------------------------------
// Never generates a false promise or a fabricated case study.

export function getOfferProfiles(activeOnly = false): Promise<OfferProfileListResponse> {
  return getJson<OfferProfileListResponse>(
    `/api/v1/sales-strategy/offers?active_only=${activeOnly}`
  );
}

export function getOfferProfile(offerId: string): Promise<OfferProfile> {
  return getJson<OfferProfile>(
    `/api/v1/sales-strategy/offers/${encodeURIComponent(offerId)}`
  );
}

export function createOfferProfile(
  payload: CreateOfferProfileRequest
): Promise<OfferProfile> {
  return postJson<OfferProfile, CreateOfferProfileRequest>(
    "/api/v1/sales-strategy/offers",
    payload
  );
}

export function updateOfferProfile(
  offerId: string,
  payload: UpdateOfferProfileRequest
): Promise<OfferProfile> {
  return patchJson<OfferProfile, UpdateOfferProfileRequest>(
    `/api/v1/sales-strategy/offers/${encodeURIComponent(offerId)}`,
    payload
  );
}

export function deactivateOfferProfile(offerId: string): Promise<OfferProfile> {
  return patchJson<OfferProfile, undefined>(
    `/api/v1/sales-strategy/offers/${encodeURIComponent(offerId)}/deactivate`,
    undefined
  );
}

export function previewOffer(
  payload: OfferPreviewRequest
): Promise<OfferPreviewResponse> {
  return postJson<OfferPreviewResponse, OfferPreviewRequest>(
    "/api/v1/sales-strategy/offers/preview",
    payload
  );
}

// -- Lead Sourcing --------------------------------------------------------------
// Never sends an email, never contacts anyone. A candidate only ever
// becomes a CRM Company/Lead through an explicit approve() call.

export function getLeadSourcingStatus(): Promise<LeadSourcingProviderStatus> {
  return getJson<LeadSourcingProviderStatus>("/api/v1/lead-sourcing/status");
}

export function getLeadSourcingCampaigns(
  status?: string
): Promise<LeadSourcingCampaignListResponse> {
  const query = status ? `?status=${encodeURIComponent(status)}` : "";
  return getJson<LeadSourcingCampaignListResponse>(
    `/api/v1/lead-sourcing/campaigns${query}`
  );
}

export function getLeadSourcingCampaign(
  campaignId: string
): Promise<LeadSourcingCampaign> {
  return getJson<LeadSourcingCampaign>(
    `/api/v1/lead-sourcing/campaigns/${encodeURIComponent(campaignId)}`
  );
}

export function createLeadSourcingCampaign(
  payload: CreateLeadSourcingCampaignRequest
): Promise<LeadSourcingCampaign> {
  return postJson<LeadSourcingCampaign, CreateLeadSourcingCampaignRequest>(
    "/api/v1/lead-sourcing/campaigns",
    payload
  );
}

export function updateLeadSourcingCampaign(
  campaignId: string,
  payload: UpdateLeadSourcingCampaignRequest
): Promise<LeadSourcingCampaign> {
  return patchJson<LeadSourcingCampaign, UpdateLeadSourcingCampaignRequest>(
    `/api/v1/lead-sourcing/campaigns/${encodeURIComponent(campaignId)}`,
    payload
  );
}

export function archiveLeadSourcingCampaign(
  campaignId: string
): Promise<LeadSourcingCampaign> {
  return patchJson<LeadSourcingCampaign, undefined>(
    `/api/v1/lead-sourcing/campaigns/${encodeURIComponent(campaignId)}/archive`,
    undefined
  );
}

export function startLeadSourcingRun(
  campaignId: string,
  payload: StartLeadSourcingRunRequest
): Promise<StartLeadSourcingRunResponse> {
  return postJson<StartLeadSourcingRunResponse, StartLeadSourcingRunRequest>(
    `/api/v1/lead-sourcing/campaigns/${encodeURIComponent(campaignId)}/runs`,
    payload
  );
}

export function getLeadSourcingRuns(
  campaignId?: string
): Promise<LeadSourcingRunListResponse> {
  const query = campaignId ? `?campaign_id=${encodeURIComponent(campaignId)}` : "";
  return getJson<LeadSourcingRunListResponse>(`/api/v1/lead-sourcing/runs${query}`);
}

export function getLeadSourcingRun(runId: string): Promise<LeadSourcingRun> {
  return getJson<LeadSourcingRun>(
    `/api/v1/lead-sourcing/runs/${encodeURIComponent(runId)}`
  );
}

export function getLeadCandidates(params?: {
  campaignId?: string;
  sourcingRunId?: string;
  reviewStatus?: string;
}): Promise<LeadCandidateListResponse> {
  const search = new URLSearchParams();
  if (params?.campaignId) search.set("campaign_id", params.campaignId);
  if (params?.sourcingRunId) search.set("sourcing_run_id", params.sourcingRunId);
  if (params?.reviewStatus) search.set("review_status", params.reviewStatus);
  const query = search.toString() ? `?${search.toString()}` : "";
  return getJson<LeadCandidateListResponse>(`/api/v1/lead-sourcing/candidates${query}`);
}

export function getLeadCandidate(candidateId: string): Promise<LeadCandidate> {
  return getJson<LeadCandidate>(
    `/api/v1/lead-sourcing/candidates/${encodeURIComponent(candidateId)}`
  );
}

export function importLeadCandidates(
  payload: ImportLeadCandidatesRequest
): Promise<ImportLeadCandidatesResponse> {
  return postJson<ImportLeadCandidatesResponse, ImportLeadCandidatesRequest>(
    "/api/v1/lead-sourcing/candidates/import",
    payload
  );
}

export function approveLeadCandidate(
  candidateId: string,
  payload: ApproveLeadCandidateRequest = {}
): Promise<ApproveLeadCandidateResponse> {
  return postJson<ApproveLeadCandidateResponse, ApproveLeadCandidateRequest>(
    `/api/v1/lead-sourcing/candidates/${encodeURIComponent(candidateId)}/approve`,
    payload
  );
}

export function rejectLeadCandidate(
  candidateId: string,
  payload: RejectLeadCandidateRequest = {}
): Promise<RejectLeadCandidateResponse> {
  return postJson<RejectLeadCandidateResponse, RejectLeadCandidateRequest>(
    `/api/v1/lead-sourcing/candidates/${encodeURIComponent(candidateId)}/reject`,
    payload
  );
}

// -- Lead Qualification & Scoring -----------------------------------------------
// Never sends an email, never contacts anyone, never starts a Sales
// Workflow by itself. A result is a recommendation only.

export function getLeadQualificationStatus(): Promise<LeadQualificationStatus> {
  return getJson<LeadQualificationStatus>("/api/v1/lead-qualification/status");
}

export function getLeadQualificationDashboard(): Promise<QualificationDashboardResponse> {
  return getJson<QualificationDashboardResponse>("/api/v1/lead-qualification/dashboard");
}

export function startLeadQualificationRun(
  payload: StartLeadQualificationRequest
): Promise<StartLeadQualificationResponse> {
  return postJson<StartLeadQualificationResponse, StartLeadQualificationRequest>(
    "/api/v1/lead-qualification/runs",
    payload
  );
}

export function getLeadQualificationRuns(): Promise<LeadQualificationRunListResponse> {
  return getJson<LeadQualificationRunListResponse>("/api/v1/lead-qualification/runs");
}

export function getLeadQualificationRun(runId: string): Promise<LeadQualificationRun> {
  return getJson<LeadQualificationRun>(
    `/api/v1/lead-qualification/runs/${encodeURIComponent(runId)}`
  );
}

export function getLeadQualificationResults(params?: {
  qualificationRunId?: string;
  qualificationStatus?: string;
}): Promise<LeadQualificationResultListResponse> {
  const search = new URLSearchParams();
  if (params?.qualificationRunId) {
    search.set("qualification_run_id", params.qualificationRunId);
  }
  if (params?.qualificationStatus) {
    search.set("qualification_status", params.qualificationStatus);
  }
  const query = search.toString() ? `?${search.toString()}` : "";
  return getJson<LeadQualificationResultListResponse>(
    `/api/v1/lead-qualification/results${query}`
  );
}

export function getLeadQualificationResult(
  resultId: string
): Promise<LeadQualificationResult> {
  return getJson<LeadQualificationResult>(
    `/api/v1/lead-qualification/results/${encodeURIComponent(resultId)}`
  );
}

export function qualifyLeadCandidate(
  candidateId: string,
  payload: QualifyLeadCandidateRequest = {}
): Promise<LeadQualificationResult> {
  return postJson<LeadQualificationResult, QualifyLeadCandidateRequest>(
    `/api/v1/lead-qualification/candidates/${encodeURIComponent(candidateId)}/qualify`,
    payload
  );
}

export function qualifyCRMLead(
  leadId: string,
  payload: QualifyCRMLeadRequest = {}
): Promise<LeadQualificationResult> {
  return postJson<LeadQualificationResult, QualifyCRMLeadRequest>(
    `/api/v1/lead-qualification/leads/${encodeURIComponent(leadId)}/qualify`,
    payload
  );
}

export function reviewQualificationResult(
  resultId: string,
  payload: QualificationReviewRequest
): Promise<QualificationReviewResponse> {
  return patchJson<QualificationReviewResponse, QualificationReviewRequest>(
    `/api/v1/lead-qualification/results/${encodeURIComponent(resultId)}/review`,
    payload
  );
}

// -- Outreach Campaign Queue -------------------------------------------------------
// Collects already-qualified leads into a prioritized queue for human
// review. Never sends an email, never contacts anyone, and never creates
// an external (Gmail/Outlook) draft by itself.

export function getOutreachQueueStatus(): Promise<OutreachQueueStatusInfo> {
  return getJson<OutreachQueueStatusInfo>("/api/v1/outreach/status");
}

export function getOutreachDashboard(): Promise<OutreachQueueDashboardResponse> {
  return getJson<OutreachQueueDashboardResponse>("/api/v1/outreach/dashboard");
}

export function getOutreachCampaigns(): Promise<OutreachCampaignListResponse> {
  return getJson<OutreachCampaignListResponse>("/api/v1/outreach/campaigns");
}

export function getOutreachCampaign(campaignId: string): Promise<OutreachCampaign> {
  return getJson<OutreachCampaign>(
    `/api/v1/outreach/campaigns/${encodeURIComponent(campaignId)}`
  );
}

export function createOutreachCampaign(
  payload: CreateOutreachCampaignRequest
): Promise<OutreachCampaign> {
  return postJson<OutreachCampaign, CreateOutreachCampaignRequest>(
    "/api/v1/outreach/campaigns",
    payload
  );
}

export function updateOutreachCampaign(
  campaignId: string,
  payload: UpdateOutreachCampaignRequest
): Promise<OutreachCampaign> {
  return patchJson<OutreachCampaign, UpdateOutreachCampaignRequest>(
    `/api/v1/outreach/campaigns/${encodeURIComponent(campaignId)}`,
    payload
  );
}

export function archiveOutreachCampaign(campaignId: string): Promise<OutreachCampaign> {
  return patchJson<OutreachCampaign, Record<string, never>>(
    `/api/v1/outreach/campaigns/${encodeURIComponent(campaignId)}/archive`,
    {}
  );
}

export function updateOutreachCampaignStatus(
  campaignId: string,
  payload: UpdateOutreachCampaignStatusRequest
): Promise<OutreachCampaign> {
  return patchJson<OutreachCampaign, UpdateOutreachCampaignStatusRequest>(
    `/api/v1/outreach/campaigns/${encodeURIComponent(campaignId)}/status`,
    payload
  );
}

export function buildOutreachQueue(
  campaignId: string,
  payload: BuildOutreachQueueRequest
): Promise<BuildOutreachQueueResponse> {
  return postJson<BuildOutreachQueueResponse, BuildOutreachQueueRequest>(
    `/api/v1/outreach/campaigns/${encodeURIComponent(campaignId)}/build-queue`,
    payload
  );
}

export function prepareOutreachBatch(
  campaignId: string,
  payload: PrepareQueueBatchRequest = {}
): Promise<PrepareQueueBatchResponse> {
  return postJson<PrepareQueueBatchResponse, PrepareQueueBatchRequest>(
    `/api/v1/outreach/campaigns/${encodeURIComponent(campaignId)}/prepare-batch`,
    payload
  );
}

export function getOutreachQueue(params?: {
  campaignId?: string;
  queueStatus?: string;
}): Promise<OutreachQueueItemListResponse> {
  const search = new URLSearchParams();
  if (params?.campaignId) {
    search.set("campaign_id", params.campaignId);
  }
  if (params?.queueStatus) {
    search.set("queue_status", params.queueStatus);
  }
  const query = search.toString() ? `?${search.toString()}` : "";
  return getJson<OutreachQueueItemListResponse>(`/api/v1/outreach/queue${query}`);
}

export function getOutreachQueueItem(queueItemId: string): Promise<OutreachQueueItem> {
  return getJson<OutreachQueueItem>(
    `/api/v1/outreach/queue/${encodeURIComponent(queueItemId)}`
  );
}

export function updateOutreachQueueItemStatus(
  queueItemId: string,
  payload: UpdateQueueItemStatusRequest
): Promise<UpdateQueueItemStatusResponse> {
  return patchJson<UpdateQueueItemStatusResponse, UpdateQueueItemStatusRequest>(
    `/api/v1/outreach/queue/${encodeURIComponent(queueItemId)}/status`,
    payload
  );
}

export function prepareQueueItemWorkflow(
  queueItemId: string,
  payload: PrepareQueueItemWorkflowRequest = {}
): Promise<PrepareQueueItemWorkflowResponse> {
  return postJson<PrepareQueueItemWorkflowResponse, PrepareQueueItemWorkflowRequest>(
    `/api/v1/outreach/queue/${encodeURIComponent(queueItemId)}/prepare-workflow`,
    payload
  );
}
