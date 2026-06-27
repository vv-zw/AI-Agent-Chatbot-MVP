export type MessageRole = "user" | "assistant" | "tool";
export type FeedbackRating = "like" | "dislike";
export type ToolCallStatus = "pending" | "succeeded" | "failed";
export type LLMProviderName = "mock" | "openai";

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

export interface LLMProviderStatus {
  provider: LLMProviderName;
  available_providers: LLMProviderName[];
  openai_configured: boolean;
}

export interface LLMProviderSwitchRequest {
  provider: LLMProviderName;
}

export interface LLMProviderSwitchResponse {
  provider: LLMProviderName;
  openai_configured: boolean;
}

export interface ChatbotRole {
  role_id: string;
  name: string;
  description: string;
  system_prompt: string;
  icon: string | null;
  color: string | null;
}

export interface ChatSession {
  id: string;
  title: string;
  role_id: string;
  role: ChatbotRole | null;
  created_at: string;
  updated_at: string;
}

export interface MessageFeedback {
  id: string;
  session_id: string;
  message_id: string;
  rating: FeedbackRating;
  reason: string;
  created_at: string;
  updated_at: string;
}

export interface FeedbackSubmitRequest {
  rating: FeedbackRating;
  reason?: string;
}

export interface ChatMessage {
  id: string;
  session_id: string;
  role: MessageRole;
  content: string;
  created_at: string;
  delivery_status?: "streaming" | "complete" | "failed";
  feedback?: MessageFeedback | null;
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

export interface KnowledgeFile {
  id: string;
  session_id: string;
  filename: string;
  content_type: string;
  size: number;
  chunk_count: number;
  created_at: string;
}
export interface SessionDetail extends ChatSession {
  messages: ChatMessage[];
  tool_calls: ToolCall[];
}

export interface SessionCreateRequest {
  title?: string;
  role_id?: string;
}

export type ChatStreamEvent =
  | {
      event: "user_message_saved";
      data: { user_message: ChatMessage };
    }
  | {
      event: "tool_call_start" | "tool_call_result";
      data: { sequence: number; tool_call: ToolCall };
    }
  | {
      event: "assistant_delta";
      data: { delta: string };
    }
  | {
      event: "assistant_done";
      data: ChatResponse;
    }
  | {
      event: "error";
      data: ApiErrorResponse;
    };

export type ChatStreamEventHandler = (event: ChatStreamEvent) => void;
export interface SessionRoleUpdateRequest {
  role_id: string;
}

export interface SessionDeleteResponse {
  id: string;
  status: "deleted";
}

export interface ChatRequest {
  content: string;
  provider?: LLMProviderName;
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
