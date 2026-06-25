export type MessageRole = "user" | "assistant" | "tool";
export type ToolCallStatus = "pending" | "succeeded" | "failed";

export interface ApiSuccessResponse<T> {
  data: T;
}

export type ApiResponse<T> = ApiSuccessResponse<T>;

export interface ApiErrorDetail {
  code: string;
  message: string;
  details: unknown | null;
}

export interface ApiErrorResponse {
  error: ApiErrorDetail;
}

export interface HealthStatus {
  status: string;
  provider: string;
}

export interface ChatSession {
  id: string;
  title: string;
  created_at: string;
  updated_at: string;
}

export interface ChatMessage {
  id: string;
  session_id: string;
  role: MessageRole;
  content: string;
  created_at: string;
}

export interface ToolCall {
  id: string;
  session_id: string;
  assistant_message_id: string | null;
  tool_message_id: string | null;
  tool_name: string;
  arguments: Record<string, unknown>;
  result: Record<string, unknown> | null;
  status: ToolCallStatus;
  error_code: string | null;
  error_message: string | null;
  created_at: string;
  completed_at: string | null;
}

export interface SessionDetail extends ChatSession {
  messages: ChatMessage[];
  tool_calls: ToolCall[];
}

export interface SessionCreateRequest {
  title?: string;
}

export interface ChatRequest {
  content: string;
}

export interface ChatResponse {
  user_message: ChatMessage;
  assistant_message: ChatMessage;
  tool_calls: ToolCall[];
}

export type Session = ChatSession;
export type Message = ChatMessage;
export type SendMessageRequest = ChatRequest;
export type SendMessageResponse = ChatResponse;