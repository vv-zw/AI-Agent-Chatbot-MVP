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

function summarizeValue(value: unknown) {
  if (value === null || value === undefined) return "空";
  if (typeof value === "string") return value;
  if (typeof value === "number" || typeof value === "boolean") return String(value);
  if (Array.isArray(value)) return `数组 · ${value.length} 项`;
  if (typeof value === "object") return `对象 · ${Object.keys(value as Record<string, unknown>).length} 项`;
  return String(value);
}

function RecordPreview({ title, value }: { title: string; value: unknown }) {
  const entries = value && typeof value === "object" && !Array.isArray(value)
    ? Object.entries(value as Record<string, unknown>).slice(0, 6)
    : [];

  return (
    <details className="rounded-2xl border border-line bg-[#fffbf3] p-3" open={title === "工具返回结果"}>
      <summary className="cursor-pointer select-none text-xs font-semibold text-ink marker:text-accent">{title}</summary>
      {entries.length > 0 && (
        <dl className="mt-3 grid gap-2 sm:grid-cols-2">
          {entries.map(([key, item]) => (
            <div className="rounded-xl border border-line/80 bg-panel px-3 py-2" key={key}>
              <dt className="truncate font-mono text-[11px] font-semibold text-brandDeep">{key}</dt>
              <dd className="mt-1 line-clamp-2 break-words text-xs leading-5 text-muted">{summarizeValue(item)}</dd>
            </div>
          ))}
        </dl>
      )}
      <pre className="mt-3 max-h-72 overflow-auto whitespace-pre-wrap break-words rounded-xl border border-line bg-[#2e293b] p-3 font-mono text-xs leading-5 text-[#fff7e8]">{formatJson(value)}</pre>
    </details>
  );
}

function ToolCallCard({ call, sequence, total }: { call: ToolCall; sequence: number; total: number }) {
  const status = {
    pending: {
      label: "正在施放工具",
      badge: "处理中",
      className: "border-warning/25 bg-[#fff8e6] text-warning",
      dotClassName: "bg-warning animate-pulse",
    },
    succeeded: {
      label: "工具施放完成",
      badge: "成功",
      className: "border-success/20 bg-[#eefaf5] text-success",
      dotClassName: "bg-success",
    },
    failed: {
      label: "工具施放失败",
      badge: "失败",
      className: "border-danger/20 bg-[#fff1f1] text-danger",
      dotClassName: "bg-danger",
    },
  }[call.status];

  return (
    <article className="ml-12 max-w-2xl overflow-hidden rounded-3xl border border-line bg-panel shadow-scroll">
      <div className="relative border-b border-line bg-[#fbf2df] px-4 py-3">
        <div className="absolute right-4 top-3 text-accent/70">✦</div>
        <div className="flex items-start justify-between gap-3 pr-8">
          <div className="flex min-w-0 items-start gap-3">
            <span className={`mt-2 size-2.5 shrink-0 rounded-full ${status.dotClassName}`} />
            <div className="min-w-0">
              <p className="text-xs font-medium text-muted">Agent 执行记录 · 第 {sequence}/{total} 步 · {status.label}</p>
              <p className="mt-0.5 truncate font-mono text-sm font-semibold text-ink">{call.tool_name}</p>
            </div>
          </div>
          <span className={`shrink-0 rounded-full border px-2.5 py-1 text-xs font-semibold ${status.className}`}>{status.badge}</span>
        </div>
      </div>
      <div className="space-y-3 p-4">
        <RecordPreview title="调用参数" value={call.arguments} />

        {call.result !== null && (
          <RecordPreview title="工具返回结果" value={call.result} />
        )}

        {call.error_message && (
          <div className="rounded-2xl border border-danger/20 bg-[#fff1f1] p-3 text-danger">
            <p className="text-xs font-semibold">错误信息</p>
            <p className="mt-1 break-words text-xs leading-5">{call.error_message}</p>
            {call.error_code && <p className="mt-1 font-mono text-[11px] opacity-70">{call.error_code}</p>}
          </div>
        )}
      </div>
    </article>
  );
}

function ToolCallGroup({ calls }: { calls: ToolCall[] }) {
  if (calls.length === 0) return null;
  return (
    <section aria-label={`工具调用编排，共 ${calls.length} 步`} className="space-y-3">
      {calls.length > 1 && (
        <div className="ml-12 flex max-w-2xl items-center gap-3 rounded-2xl border border-brand/15 bg-[#f3edff]/80 px-4 py-2.5 text-xs text-brandDeep">
          <span className="grid size-6 shrink-0 place-items-center rounded-full bg-brand text-[11px] font-bold text-white">{calls.length}</span>
          <span><strong>多工具编排</strong>：按顺序执行 {calls.length} 个独立步骤</span>
        </div>
      )}
      {calls.map((call, index) => (
        <ToolCallCard call={call} key={call.id} sequence={index + 1} total={calls.length} />
      ))}
    </section>
  );
}

function MessageBubble({ message }: { message: ChatMessage }) {
  const isUser = message.role === "user";
  const isTool = message.role === "tool";
  const label = isUser ? "用户指令" : isTool ? "工具" : "Agent 回信";

  return (
    <article className={`flex gap-3 ${isUser ? "flex-row-reverse" : ""}`}>
      <div className={`grid size-9 shrink-0 place-items-center rounded-2xl border text-xs font-semibold ${
        isUser
          ? "border-brand/25 bg-brand text-white"
          : isTool
            ? "border-warning/20 bg-[#fff8e6] text-warning"
            : "border-brand/20 bg-[#f3edff] text-brandDeep"
      }`}>
        {isTool ? "T" : isUser ? "令" : "回"}
      </div>
      <div className={`max-w-[min(82%,44rem)] rounded-3xl px-4 py-3 shadow-sm ${
        isUser
          ? "rounded-tr-md border border-brand/15 bg-brand text-white"
          : isTool
            ? "rounded-tl-md border border-warning/15 bg-[#fff8e6] text-ink"
            : "rounded-tl-md border border-line bg-panel text-ink"
      }`}>
        <div className="mb-1.5 flex items-center gap-2 text-[11px] font-semibold opacity-70">
          <span>{label}</span>
          <time dateTime={message.created_at}>{formatMessageTime(message.created_at)}</time>
          {message.delivery_status === "streaming" && <span className="text-brand">生成中</span>}
          {message.delivery_status === "failed" && <span className="text-danger">已中断</span>}
        </div>
        <p className="whitespace-pre-wrap break-words text-sm leading-7">{message.content}{message.delivery_status === "streaming" && <span className="ml-1 inline-block h-4 w-1 animate-pulse bg-brand align-middle" />}</p>
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
          <div className="relative space-y-3 before:absolute before:left-[18px] before:top-12 before:h-[calc(100%-3rem)] before:w-px before:bg-gradient-to-b before:from-accent/70 before:to-line last:before:hidden" key={message.id}>
            <MessageBubble message={message} />
            <ToolCallGroup calls={relatedCalls} />
          </div>
        );
      })}

      {toolCalls
        .filter((call) => !renderedCallIds.has(call.id))
        .map((call) => <ToolCallCard call={call} key={call.id} sequence={1} total={1} />)}
    </>
  );
}
