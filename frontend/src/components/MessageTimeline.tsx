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
      className: "border-warning/25 bg-[#fff8eb] text-warning",
      dotClassName: "bg-warning animate-pulse",
    },
    succeeded: {
      label: "工具调用完成",
      badge: "成功",
      className: "border-success/20 bg-[#f3faf4] text-success",
      dotClassName: "bg-success",
    },
    failed: {
      label: "工具调用失败",
      badge: "失败",
      className: "border-danger/20 bg-[#fff5f4] text-danger",
      dotClassName: "bg-danger",
    },
  }[call.status];

  return (
    <article className="ml-12 max-w-2xl overflow-hidden rounded-xl border border-line bg-panel shadow-sm">
      <div className="flex items-center justify-between gap-3 border-b border-line bg-[#f7f7f2] px-4 py-3">
        <div className="flex min-w-0 items-center gap-3">
          <span className={`size-2.5 shrink-0 rounded-full ${status.dotClassName}`} />
          <div className="min-w-0">
            <p className="text-xs font-medium text-muted">{status.label}</p>
            <p className="truncate font-mono text-sm font-semibold text-ink">{call.tool_name}</p>
          </div>
        </div>
        <span className={`rounded-full border px-2.5 py-1 text-xs font-semibold ${status.className}`}>{status.badge}</span>
      </div>

      <div className="space-y-3 p-4">
        <details>
          <summary className="cursor-pointer text-xs font-semibold text-ink marker:text-muted">工具参数</summary>
          <pre className="mt-2 max-h-60 overflow-auto rounded-lg border border-line bg-white p-3 font-mono text-xs leading-5 text-ink/80">{formatJson(call.arguments)}</pre>
        </details>

        {call.result !== null && (
          <details open>
            <summary className="cursor-pointer text-xs font-semibold text-ink marker:text-muted">工具返回结果</summary>
            <pre className="mt-2 max-h-72 overflow-auto whitespace-pre-wrap break-words rounded-lg border border-line bg-white p-3 font-mono text-xs leading-5 text-ink/80">{formatJson(call.result)}</pre>
          </details>
        )}

        {call.error_message && (
          <div className="rounded-lg border border-danger/20 bg-[#fff5f4] p-3 text-danger">
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
  const label = isUser ? "你" : isTool ? "工具" : "助手";

  return (
    <article className={`flex gap-3 ${isUser ? "flex-row-reverse" : ""}`}>
      <div className={`grid size-9 shrink-0 place-items-center rounded-xl border text-xs font-semibold ${
        isUser
          ? "border-ink bg-ink text-white"
          : isTool
            ? "border-warning/20 bg-[#fff8eb] text-warning"
            : "border-brand/15 bg-[#eef5f1] text-brand"
      }`}>
        {isTool ? "T" : isUser ? "你" : "助"}
      </div>
      <div className={`max-w-[min(82%,44rem)] rounded-2xl px-4 py-3 shadow-sm ${
        isUser
          ? "rounded-tr-md bg-brand text-white"
          : isTool
            ? "rounded-tl-md border border-warning/15 bg-[#fff8eb] text-ink"
            : "rounded-tl-md border border-line bg-panel text-ink"
      }`}>
        <div className="mb-1.5 flex items-center gap-2 text-[11px] font-semibold opacity-65">
          <span>{label}</span>
          <time dateTime={message.created_at}>{formatMessageTime(message.created_at)}</time>
        </div>
        <p className="whitespace-pre-wrap break-words text-sm leading-7">{message.content}</p>
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
          <div className="relative space-y-3 before:absolute before:left-[18px] before:top-12 before:h-[calc(100%-3rem)] before:w-px before:bg-line last:before:hidden" key={message.id}>
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
