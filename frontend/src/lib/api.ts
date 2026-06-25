import type {
  ApiErrorResponse,
  ApiResponse,
  ChatRequest,
  ChatResponse,
  ChatSession,
  SessionCreateRequest,
  SessionDetail,
} from "../types/api";

const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000/api/v1";

export class ApiError extends Error {
  readonly code: string;
  readonly details: unknown;

  constructor(payload: ApiErrorResponse) {
    super(payload.error.message);
    this.name = "ApiError";
    this.code = payload.error.code;
    this.details = payload.error.details;
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...init?.headers,
    },
  });

  const payload = (await response.json()) as ApiResponse<T> | ApiErrorResponse;
  if (!response.ok) {
    throw new ApiError(payload as ApiErrorResponse);
  }
  return (payload as ApiResponse<T>).data;
}

export const api = {
  listSessions: () => request<ChatSession[]>("/sessions"),

  createSession: (payload: SessionCreateRequest = {}) =>
    request<ChatSession>("/sessions", {
      method: "POST",
      body: JSON.stringify(payload),
    }),

  getSession: (sessionId: string) =>
    request<SessionDetail>(`/sessions/${sessionId}`),

  sendMessage: (sessionId: string, payload: ChatRequest) =>
    request<ChatResponse>(`/sessions/${sessionId}/messages`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),
};

