import type {
  ApiErrorResponse,
  ApiSuccessResponse,
  ChatRequest,
  ChatResponse,
  ChatStreamEvent,
  ChatStreamEventHandler,
  ChatSession,
  ChatbotRole,
  FeedbackSubmitRequest,
  HealthStatus,
  MessageFeedback,
  LLMProviderStatus,
  LLMProviderSwitchRequest,
  LLMProviderSwitchResponse,
  KnowledgeFile,
  SessionCreateRequest,
  SessionDeleteResponse,
  SessionDetail,
  SessionRoleUpdateRequest,
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

async function uploadRequest<T>(path: string, file: File): Promise<T> {
  const body = new FormData();
  body.append("file", file);
  let response: Response;
  try {
    response = await fetch(`${API_BASE_URL}${path}`, { method: "POST", body });
  } catch (cause) {
    throw createApiError("NETWORK_ERROR", "无法连接文件上传接口，请确认后端服务已启动。", cause);
  }
  let payload: unknown;
  try {
    payload = await response.json();
  } catch {
    throw createApiError("INVALID_RESPONSE", `上传失败（HTTP ${response.status}）。`);
  }
  if (!response.ok) {
    if (isApiErrorResponse(payload)) throw new ApiError(payload);
    throw createApiError("HTTP_ERROR", `上传失败（HTTP ${response.status}）。`, payload);
  }
  if (!isApiSuccessResponse<T>(payload)) {
    throw createApiError("INVALID_RESPONSE", "上传响应缺少 data 字段。", payload);
  }
  return payload.data;
}
async function streamRequest(
  path: string,
  payload: ChatRequest,
  onEvent: ChatStreamEventHandler,
): Promise<void> {
  let response: Response;
  try {
    response = await fetch(`${API_BASE_URL}${path}`, {
      method: "POST",
      headers: {
        Accept: "text/event-stream",
        "Content-Type": "application/json",
      },
      body: JSON.stringify(payload),
    });
  } catch (cause) {
    throw createApiError(
      "NETWORK_ERROR",
      "无法连接后端流式接口，请确认服务已启动。",
      cause instanceof Error ? cause.message : null,
    );
  }

  if (!response.ok) {
    let errorBody: unknown;
    try {
      errorBody = await response.json();
    } catch {
      errorBody = null;
    }
    if (isApiErrorResponse(errorBody)) throw new ApiError(errorBody);
    throw createApiError("HTTP_ERROR", `流式请求失败（HTTP ${response.status}）。`, errorBody);
  }
  if (!response.body) {
    throw createApiError("STREAM_UNAVAILABLE", "浏览器未提供可读取的流式响应。", null);
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  let terminated = false;

  function dispatch(block: string) {
    let eventName = "message";
    const dataLines: string[] = [];
    for (const line of block.split("\n")) {
      if (line.startsWith("event:")) eventName = line.slice(6).trim();
      if (line.startsWith("data:")) dataLines.push(line.slice(5).trimStart());
    }
    if (dataLines.length === 0) return;

    let data: unknown;
    try {
      data = JSON.parse(dataLines.join("\n"));
    } catch {
      throw createApiError("INVALID_STREAM_EVENT", "流式事件不是有效 JSON。", { event: eventName });
    }
    const streamEvent = { event: eventName, data } as ChatStreamEvent;
    onEvent(streamEvent);
    if (eventName === "assistant_done") terminated = true;
    if (eventName === "error") {
      terminated = true;
      const payloadError = data as ApiErrorResponse;
      if (isApiErrorResponse(payloadError)) throw new ApiError(payloadError);
      throw createApiError("STREAM_FAILED", "流式回复失败，请稍后重试。", data);
    }
  }

  while (true) {
    const { done, value } = await reader.read();
    buffer += decoder.decode(value, { stream: !done }).replace(/\r\n/g, "\n");
    let boundary = buffer.indexOf("\n\n");
    while (boundary >= 0) {
      const block = buffer.slice(0, boundary);
      buffer = buffer.slice(boundary + 2);
      if (block.trim()) dispatch(block);
      boundary = buffer.indexOf("\n\n");
    }
    if (done) break;
  }
  if (buffer.trim()) dispatch(buffer);
  if (!terminated) {
    throw createApiError("STREAM_INTERRUPTED", "流式回复失败，请稍后重试。", null);
  }
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

  listRoles: () => request<ChatbotRole[]>("/roles"),

  listSessions: () => request<ChatSession[]>("/sessions"),

  createSession: (payload: SessionCreateRequest = {}) =>
    request<ChatSession>("/sessions", {
      method: "POST",
      body: JSON.stringify(payload),
    }),

  getSession: (sessionId: string) =>
    request<SessionDetail>(sessionPath(sessionId)),

  submitFeedback: (sessionId: string, messageId: string, payload: FeedbackSubmitRequest) =>
    request<MessageFeedback>(`${sessionPath(sessionId)}/messages/${encodeURIComponent(messageId)}/feedback`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),

  updateSessionRole: (sessionId: string, payload: SessionRoleUpdateRequest) =>
    request<ChatSession>(`${sessionPath(sessionId)}/role`, {
      method: "PATCH",
      body: JSON.stringify(payload),
    }),

  deleteSession: (sessionId: string) =>
    request<SessionDeleteResponse>(sessionPath(sessionId), {
      method: "DELETE",
    }),

  listKnowledgeFiles: (sessionId: string) =>
    request<KnowledgeFile[]>(`${sessionPath(sessionId)}/knowledge/files`),

  uploadKnowledgeFile: (sessionId: string, file: File) =>
    uploadRequest<KnowledgeFile>(`${sessionPath(sessionId)}/knowledge/files`, file),
  sendMessage: (sessionId: string, payload: ChatRequest) =>
    request<ChatResponse>(`${sessionPath(sessionId)}/messages`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  sendMessageStream: (sessionId: string, payload: ChatRequest, onEvent: ChatStreamEventHandler) =>
    streamRequest(`${sessionPath(sessionId)}/messages/stream`, payload, onEvent),
};
