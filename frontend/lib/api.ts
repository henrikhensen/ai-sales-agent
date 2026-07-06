import type {
  Company,
  Contact,
  EmailDraftRecord,
  EmailDraftReviewStatusResponse,
  EmailDraftReviewStatusUpdateRequest,
  HealthResponse,
  Interaction,
  Lead,
  ListSalesWorkflowRunsParams,
  ReviewEventListResponse,
  SalesWorkflowRequest,
  SalesWorkflowResponse,
  UpdateWorkflowReviewStatusRequest,
  UpdateWorkflowReviewStatusResponse,
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
  let response: Response;
  try {
    response = await fetch(`${API_BASE_URL}${path}`, {
      ...init,
      headers: {
        "Content-Type": "application/json",
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
