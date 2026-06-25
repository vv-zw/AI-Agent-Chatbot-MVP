import { useCallback, useEffect, useRef, useState } from "react";

import { LogoMark, SessionSidebar } from "./components/SessionSidebar";
import { api } from "./lib/api";
import type { ChatMessage, ChatSession, ToolCall } from "./types/api";

function getErrorMessage(error: unknown, fallback: string) {
  return error instanceof Error && error.message ? error.message : fallback;
}

function formatMessageTime(value: string) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "";

  return new Intl.DateTimeFormat("zh-CN", {
    hour: "2-digit",
    minute: "2-digit",
  }).format(date);
}

export default function App() {
  const [sessions, setSessions] = useState<ChatSession[]>([]);
  const [activeSessionId, setActiveSessionId] = useState<string | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [, setToolCalls] = useState<ToolCall[]>([]);
  const [isLoadingSessions, setIsLoadingSessions] = useState(true);
  const [isLoadingSession, setIsLoadingSession] = useState(false);
  const [isCreating, setIsCreating] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const detailRequestId = useRef(0);

  const activeSession = sessions.find((session) => session.id === activeSessionId) ?? null;

  const loadSession = useCallback(async (sessionId: string) => {
    const requestId = ++detailRequestId.current;
    setActiveSessionId(sessionId);
    setIsLoadingSession(true);
    setError(null);

    try {
      const detail = await api.getSession(sessionId);
      if (requestId !== detailRequestId.current) return;
      setMessages(detail.messages);
      setToolCalls(detail.tool_calls);
    } catch (caught) {
      if (requestId !== detailRequestId.current) return;
      setMessages([]);
      setToolCalls([]);
      setError(getErrorMessage(caught, "加载会话失败，请稍后重试。"));
    } finally {
      if (requestId === detailRequestId.current) setIsLoadingSession(false);
    }
  }, []);

  useEffect(() => {
    let isCancelled = false;

    void (async () => {
      try {
        const items = await api.listSessions();
        if (isCancelled) return;
        setSessions(items);
        if (items[0]) await loadSession(items[0].id);
      } catch (caught) {
        if (!isCancelled) {
          setError(getErrorMessage(caught, "加载会话列表失败，请确认后端服务已启动。"));
        }
      } finally {
        if (!isCancelled) setIsLoadingSessions(false);
      }
    })();

    return () => {
      isCancelled = true;
    };
  }, [loadSession]);

  async function createSession() {
    if (isCreating) return;
    setIsCreating(true);
    setError(null);

    try {
      const created = await api.createSession();
      setSessions((current) => [created, ...current.filter((item) => item.id !== created.id)]);
      setActiveSessionId(created.id);
      setMessages([]);
      setToolCalls([]);
    } catch (caught) {
      setError(getErrorMessage(caught, "新建会话失败，请稍后重试。"));
    } finally {
      setIsCreating(false);
    }
  }

  return (
    <main className="min-h-screen bg-canvas p-0 text-ink md:p-4">
      <div className="mx-auto grid min-h-screen max-w-[1440px] overflow-hidden bg-white shadow-2xl shadow-slate-300/40 md:min-h-[calc(100vh-2rem)] md:grid-cols-[300px_minmax(0,1fr)] md:rounded-[28px]">
        <SessionSidebar
          activeSessionId={activeSessionId}
          isCreating={isCreating}
          isLoading={isLoadingSessions}
          onCreateSession={() => void createSession()}
          onSelectSession={(sessionId) => void loadSession(sessionId)}
          sessions={sessions}
        />

        <section className="flex min-h-screen min-w-0 flex-col bg-white md:min-h-0">
          <header className="flex min-h-20 items-center gap-3 border-b border-slate-100 px-4 sm:px-7">
            <div className="md:hidden">
              <LogoMark />
            </div>
            <div className="min-w-0 flex-1">
              <h1 className="truncate font-semibold text-slate-900">
                {activeSession?.title ?? "开始新对话"}
              </h1>
              <p className="mt-0.5 text-xs text-slate-500">
                {activeSession ? "会话消息已同步至服务端" : "新建一个会话，开始与 AI 助手交流"}
              </p>
            </div>
            <div className="flex items-center gap-2 md:hidden">
              {sessions.length > 0 && (
                <select
                  aria-label="选择会话"
                  className="max-w-32 rounded-xl border border-slate-200 bg-white px-2 py-2 text-xs outline-none"
                  onChange={(event) => void loadSession(event.target.value)}
                  value={activeSessionId ?? ""}
                >
                  {sessions.map((session) => (
                    <option key={session.id} value={session.id}>
                      {session.title}
                    </option>
                  ))}
                </select>
              )}
              <button
                aria-label="新建会话"
                className="grid size-10 place-items-center rounded-xl bg-slate-950 text-lg text-white disabled:opacity-50"
                disabled={isCreating}
                onClick={() => void createSession()}
                type="button"
              >
                ＋
              </button>
            </div>
          </header>

          {error && (
            <div className="mx-4 mt-4 flex items-start justify-between gap-3 rounded-2xl border border-red-100 bg-red-50 px-4 py-3 text-sm text-red-700 sm:mx-7" role="alert">
              <span>{error}</span>
              <button className="shrink-0 text-red-400 hover:text-red-700" onClick={() => setError(null)} type="button">
                关闭
              </button>
            </div>
          )}

          <div className="min-h-0 flex-1 overflow-y-auto px-4 py-6 sm:px-7">
            {isLoadingSession && (
              <div className="mx-auto max-w-4xl space-y-5" aria-label="正在加载消息">
                <div className="h-24 w-2/3 animate-pulse rounded-3xl bg-slate-100" />
                <div className="ml-auto h-20 w-1/2 animate-pulse rounded-3xl bg-violet-100" />
              </div>
            )}

            {!isLoadingSession && !activeSessionId && (
              <div className="flex min-h-full items-center justify-center py-12">
                <div className="max-w-md text-center">
                  <div className="mx-auto grid size-20 place-items-center rounded-[28px] bg-violet-50 text-3xl shadow-inner shadow-violet-100">✦</div>
                  <h2 className="mt-6 text-2xl font-semibold tracking-tight text-slate-900">有什么可以帮你？</h2>
                  <p className="mt-3 text-sm leading-7 text-slate-500">新建会话后，你可以连续提问，并在这里查看助手回复和工具调用过程。</p>
                  <button className="mt-7 rounded-2xl bg-brand px-5 py-3 text-sm font-semibold text-white shadow-lg shadow-violet-200 transition hover:bg-violet-700" disabled={isCreating} onClick={() => void createSession()} type="button">
                    {isCreating ? "正在新建…" : "新建会话"}
                  </button>
                </div>
              </div>
            )}

            {!isLoadingSession && activeSessionId && messages.length === 0 && (
              <div className="flex min-h-full items-center justify-center py-12">
                <div className="max-w-sm text-center">
                  <div className="mx-auto grid size-16 place-items-center rounded-3xl bg-slate-100 text-2xl">💬</div>
                  <h2 className="mt-5 text-xl font-semibold text-slate-900">会话已经准备好了</h2>
                  <p className="mt-2 text-sm leading-6 text-slate-500">在下方输入第一条消息，开始这段对话。</p>
                </div>
              </div>
            )}

            {!isLoadingSession && messages.length > 0 && (
              <div className="mx-auto max-w-4xl space-y-5">
                {messages.map((message) => {
                  const isUser = message.role === "user";
                  return (
                    <article className={`flex gap-3 ${isUser ? "flex-row-reverse" : ""}`} key={message.id}>
                      <div className={`grid size-9 shrink-0 place-items-center rounded-xl text-xs font-bold ${isUser ? "bg-slate-900 text-white" : "bg-violet-100 text-violet-700"}`}>
                        {isUser ? "你" : "AI"}
                      </div>
                      <div className={`max-w-[min(80%,42rem)] rounded-3xl px-4 py-3 ${isUser ? "rounded-tr-md bg-brand text-white" : "rounded-tl-md border border-slate-100 bg-slate-50 text-slate-800"}`}>
                        <p className="whitespace-pre-wrap text-sm leading-7">{message.content}</p>
                        <time className={`mt-1.5 block text-[11px] ${isUser ? "text-violet-200" : "text-slate-400"}`} dateTime={message.created_at}>
                          {formatMessageTime(message.created_at)}
                        </time>
                      </div>
                    </article>
                  );
                })}
              </div>
            )}
          </div>

          <footer className="border-t border-slate-100 bg-white px-4 py-4 sm:px-7">
            <div className="mx-auto flex max-w-4xl items-end gap-3 rounded-2xl border border-slate-200 bg-slate-50 p-2 shadow-sm">
              <textarea className="min-h-12 flex-1 resize-none bg-transparent px-3 py-3 text-sm outline-none placeholder:text-slate-400" disabled placeholder={activeSessionId ? "消息发送将在下一阶段启用" : "请先新建会话"} rows={1} />
              <button className="grid size-11 shrink-0 place-items-center rounded-xl bg-slate-200 text-slate-400" disabled type="button">↑</button>
            </div>
            <p className="mt-2 text-center text-[11px] text-slate-400">AI 生成内容可能存在误差，请核对重要信息</p>
          </footer>
        </section>
      </div>
    </main>
  );
}