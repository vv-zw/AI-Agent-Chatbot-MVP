import type {
  ApiErrorResponse,
  ApiSuccessResponse,
  ChatRequest,
  ChatResponse,
  ChatSession,
  HealthStatus,
  LLMProviderStatus,
  LLMProviderSwitchRequest,
  LLMProviderSwitchResponse,
  SessionCreateRequest,
  SessionDetail,
} from "../types/api";

const configuredBaseUrl = import.meta.env.VITE_API_BASE_URL?.trim();
const API_BASE_URL = (configuredBaseUrl || "http://localhost:8000/api/v1").replace(/\/$/, "");

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

function createApiError(code: string, message: string, details: unknown = null) {
  return new ApiError({ error: { code, message, details } });
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

function isApiErrorResponse(value: unknown): value is ApiErrorResponse {
  if (!isRecord(value) || !isRecord(value.error)) return false;
  return typeof value.error.code === "string" && typeof value.error.message === "string";
}

function isApiSuccessResponse<T>(value: unknown): value is ApiSuccessResponse<T> {
  return isRecord(value) && Object.hasOwn(value, "data");
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response;

  try {
    response = await fetch(`${API_BASE_URL}${path}`, {
      ...init,
      headers: {
        "Content-Type": "application/json",
        ...init?.headers,
      },
    });
  } catch (cause) {
    throw createApiError(
      "NETWORK_ERROR",
      "无法连接后端服务，请确认服务已启动且 API 地址配置正确。",
      cause instanceof Error ? cause.message : null,
    );
  }

  let payload: unknown;
  try {
    payload = await response.json();
  } catch {
    throw createApiError(
      "INVALID_RESPONSE",
      response.ok ? "后端返回了无法解析的数据。" : `请求失败（HTTP ${response.status}）。`,
      { status: response.status },
    );
  }

  if (!response.ok) {
    if (isApiErrorResponse(payload)) throw new ApiError(payload);
    throw createApiError("HTTP_ERROR", `请求失败（HTTP ${response.status}）。`, {
      status: response.status,
      payload,
    });
  }

  if (!isApiSuccessResponse<T>(payload)) {
    throw createApiError("INVALID_RESPONSE", "后端响应缺少 data 字段。", payload);
  }

  return payload.data;
}

function sessionPath(sessionId: string) {
  return `/sessions/${encodeURIComponent(sessionId)}`;
}

export const api = {
  getHealth: () => request<HealthStatus>("/health"),

  getLLMProvider: () => request<LLMProviderStatus>("/llm/provider"),

  switchLLMProvider: (payload: LLMProviderSwitchRequest) =>
    request<LLMProviderSwitchResponse>("/llm/provider", {
      method: "POST",
      body: JSON.stringify(payload),
    }),

  listSessions: () => request<ChatSession[]>("/sessions"),

  createSession: (payload: SessionCreateRequest = {}) =>
    request<ChatSession>("/sessions", {
      method: "POST",
      body: JSON.stringify(payload),
    }),

  getSession: (sessionId: string) =>
    request<SessionDetail>(sessionPath(sessionId)),

  sendMessage: (sessionId: string, payload: ChatRequest) =>
    request<ChatResponse>(`${sessionPath(sessionId)}/messages`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),
};
