import type {
  HealthResponse,
  SalesWorkflowRequest,
  SalesWorkflowResponse,
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
