import type { ChatMessage, ToolCall } from "../types/api";

interface MessageTimelineProps {
  messages: ChatMessage[];
  toolCalls: ToolCall[];
}

function formatMessageTime(value: string) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "";

  return new Intl.DateTimeFormat("zh-CN", {
    hour: "2-digit",
    minute: "2-digit",
  }).format(date);
}

function formatJson(value: unknown) {
  if (value === null || value === undefined) return "暂无返回结果";
  if (typeof value === "string") return value;

  try {
    return JSON.stringify(value, null, 2);
  } catch {
    return String(value);
  }
}

function ToolCallCard({ call }: { call: ToolCall }) {
  const status = {
    pending: {
      label: "正在调用工具",
      badge: "处理中",
      className: "border-amber-200 bg-amber-50 text-amber-800",
      dotClassName: "bg-amber-400 animate-pulse",
    },
    succeeded: {
      label: "工具调用完成",
      badge: "成功",
      className: "border-emerald-200 bg-emerald-50 text-emerald-800",
      dotClassName: "bg-emerald-500",
    },
    failed: {
      label: "工具调用失败",
      badge: "失败",
      className: "border-red-200 bg-red-50 text-red-800",
      dotClassName: "bg-red-500",
    },
  }[call.status];

  return (
    <article className={`ml-12 max-w-2xl overflow-hidden rounded-2xl border ${status.className}`}>
      <div className="flex items-center justify-between gap-3 border-b border-current/10 px-4 py-3">
        <div className="flex min-w-0 items-center gap-2.5">
          <span className={`size-2.5 shrink-0 rounded-full ${status.dotClassName}`} />
          <div className="min-w-0">
            <p className="text-xs font-medium opacity-75">{status.label}</p>
            <p className="truncate font-mono text-sm font-semibold">{call.tool_name}</p>
          </div>
        </div>
        <span className="rounded-full bg-white/70 px-2.5 py-1 text-xs font-semibold">{status.badge}</span>
      </div>

      <div className="space-y-3 p-4">
        <details>
          <summary className="cursor-pointer text-xs font-semibold">工具参数</summary>
          <pre className="mt-2 overflow-x-auto rounded-xl bg-white/70 p-3 text-xs leading-5 text-slate-700">{formatJson(call.arguments)}</pre>
        </details>

        {call.result !== null && (
          <details open>
            <summary className="cursor-pointer text-xs font-semibold">工具返回结果</summary>
            <pre className="mt-2 overflow-x-auto whitespace-pre-wrap break-words rounded-xl bg-white/70 p-3 text-xs leading-5 text-slate-700">{formatJson(call.result)}</pre>
          </details>
        )}

        {call.error_message && (
          <div className="rounded-xl bg-white/70 p-3">
            <p className="text-xs font-semibold">错误信息</p>
            <p className="mt-1 break-words text-xs leading-5">{call.error_message}</p>
            {call.error_code && <p className="mt-1 font-mono text-[11px] opacity-70">{call.error_code}</p>}
          </div>
        )}
      </div>
    </article>
  );
}

function MessageBubble({ message }: { message: ChatMessage }) {
  const isUser = message.role === "user";
  const isTool = message.role === "tool";
  const label = isUser ? "你" : isTool ? "工具" : "AI";

  return (
    <article className={`flex gap-3 ${isUser ? "flex-row-reverse" : ""}`}>
      <div className={`grid size-9 shrink-0 place-items-center rounded-xl text-xs font-bold ${
        isUser
          ? "bg-slate-900 text-white"
          : isTool
            ? "bg-amber-100 text-amber-700"
            : "bg-violet-100 text-violet-700"
      }`}>
        {isTool ? "⚙" : label}
      </div>
      <div className={`max-w-[min(80%,42rem)] rounded-3xl px-4 py-3 ${
        isUser
          ? "rounded-tr-md bg-brand text-white"
          : isTool
            ? "rounded-tl-md border border-amber-100 bg-amber-50 text-amber-950"
            : "rounded-tl-md border border-slate-100 bg-slate-50 text-slate-800"
      }`}>
        <p className="mb-1 text-[11px] font-semibold opacity-60">{label}</p>
        <p className="whitespace-pre-wrap break-words text-sm leading-7">{message.content}</p>
        <time className={`mt-1.5 block text-[11px] ${isUser ? "text-violet-200" : "text-slate-400"}`} dateTime={message.created_at}>
          {formatMessageTime(message.created_at)}
        </time>
      </div>
    </article>
  );
}

export function MessageTimeline({ messages, toolCalls }: MessageTimelineProps) {
  const renderedCallIds = new Set<string>();
  const visibleMessages = messages.filter((message) => message.role !== "tool");

  return (
    <>
      {visibleMessages.map((message) => {
        const relatedCalls = toolCalls.filter((call) => {
          const isRelated = call.assistant_message_id === message.id
            || (!call.assistant_message_id && call.tool_message_id === message.id);
          if (isRelated) renderedCallIds.add(call.id);
          return isRelated;
        });

        return (
          <div className="space-y-3" key={message.id}>
            <MessageBubble message={message} />
            {relatedCalls.map((call) => <ToolCallCard call={call} key={call.id} />)}
          </div>
        );
      })}

      {toolCalls
        .filter((call) => !renderedCallIds.has(call.id))
        .map((call) => <ToolCallCard call={call} key={call.id} />)}
    </>
  );
}