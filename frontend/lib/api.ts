import type {
  Company,
  Contact,
  CreateDoNotContactRequest,
  CreateExternalEmailDraftResponse,
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
  Interaction,
  Lead,
  ListSalesWorkflowRunsParams,
  LLMProviderStatus,
  LLMProviderTestResponse,
  LoginRequest,
  PipelineBoardResponse,
  PipelineStatus,
  RegisterRequest,
  ReviewEventListResponse,
  SalesWorkflowRequest,
  SalesWorkflowResponse,
  StartEmailProviderConnectionResponse,
  TokenResponse,
  UpdateDoNotContactRequest,
  UpdateLeadPipelineStatusRequest,
  UpdateLeadPipelineStatusResponse,
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
