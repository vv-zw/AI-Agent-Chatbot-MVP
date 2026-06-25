import { useCallback, useEffect, useRef, useState } from "react";

import { ChatComposer } from "./components/ChatComposer";
import { MessageTimeline } from "./components/MessageTimeline";
import { LogoMark, SessionSidebar } from "./components/SessionSidebar";
import { api } from "./lib/api";
import type { ChatMessage, ChatSession, ToolCall } from "./types/api";

function getErrorMessage(error: unknown, fallback: string) {
  return error instanceof Error && error.message ? error.message : fallback;
}

export default function App() {
  const [sessions, setSessions] = useState<ChatSession[]>([]);
  const [activeSessionId, setActiveSessionId] = useState<string | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [toolCalls, setToolCalls] = useState<ToolCall[]>([]);
  const [input, setInput] = useState("");
  const [isLoadingSessions, setIsLoadingSessions] = useState(true);
  const [isLoadingSession, setIsLoadingSession] = useState(false);
  const [isCreating, setIsCreating] = useState(false);
  const [isSending, setIsSending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const detailRequestId = useRef(0);
  const messageEndRef = useRef<HTMLDivElement>(null);

  const activeSession = sessions.find((session) => session.id === activeSessionId) ?? null;

  useEffect(() => {
    messageEndRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [messages, isSending]);

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
    if (isCreating || isSending) return;
    setIsCreating(true);
    setError(null);

    try {
      const created = await api.createSession();
      detailRequestId.current += 1;
      setSessions((current) => [created, ...current.filter((item) => item.id !== created.id)]);
      setActiveSessionId(created.id);
      setMessages([]);
      setToolCalls([]);
      setInput("");
    } catch (caught) {
      setError(getErrorMessage(caught, "新建会话失败，请稍后重试。"));
    } finally {
      setIsCreating(false);
    }
  }

  async function sendMessage(content: string) {
    if (!activeSessionId || isSending) return;
    const sessionId = activeSessionId;
    setIsSending(true);
    setError(null);

    try {
      const result = await api.sendMessage(sessionId, { content });
      if (activeSessionId !== sessionId) return;

      setInput("");
      setMessages((current) => [
        ...current,
        result.user_message,
        result.assistant_message,
      ]);
      setToolCalls((current) => [...current, ...result.tool_calls]);

      const refreshedSessions = await api.listSessions();
      setSessions(refreshedSessions);
    } catch (caught) {
      setError(getErrorMessage(caught, "消息发送失败，请稍后重试。"));
    } finally {
      setIsSending(false);
    }
  }

  return (
    <main className="min-h-screen bg-canvas p-0 text-ink md:p-4">
      <div className="mx-auto grid min-h-screen max-w-[1440px] overflow-hidden bg-white shadow-2xl shadow-slate-300/40 md:min-h-[calc(100vh-2rem)] md:grid-cols-[300px_minmax(0,1fr)] md:rounded-[28px]">
        <SessionSidebar
          activeSessionId={activeSessionId}
          isCreating={isCreating}
          isLoading={isLoadingSessions}
          interactionDisabled={isSending}
          onCreateSession={() => void createSession()}
          onSelectSession={(sessionId) => void loadSession(sessionId)}
          sessions={sessions}
        />

        <section className="flex min-h-screen min-w-0 flex-col bg-white md:min-h-0">
          <header className="flex min-h-20 items-center gap-3 border-b border-slate-100 px-4 sm:px-7">
            <div className="md:hidden"><LogoMark /></div>
            <div className="min-w-0 flex-1">
              <h1 className="truncate font-semibold text-slate-900">{activeSession?.title ?? "开始新对话"}</h1>
              <p className="mt-0.5 text-xs text-slate-500">
                {activeSession ? "会话消息已同步至服务端" : "新建一个会话，开始与 AI 助手交流"}
              </p>
            </div>
            <div className="flex items-center gap-2 md:hidden">
              {sessions.length > 0 && (
                <select aria-label="选择会话" className="max-w-32 rounded-xl border border-slate-200 bg-white px-2 py-2 text-xs outline-none" disabled={isSending} onChange={(event) => void loadSession(event.target.value)} value={activeSessionId ?? ""}>
                  {sessions.map((session) => <option key={session.id} value={session.id}>{session.title}</option>)}
                </select>
              )}
              <button aria-label="新建会话" className="grid size-10 place-items-center rounded-xl bg-slate-950 text-lg text-white disabled:opacity-50" disabled={isCreating || isSending} onClick={() => void createSession()} type="button">＋</button>
            </div>
          </header>

          {error && (
            <div className="mx-4 mt-4 flex items-start justify-between gap-3 rounded-2xl border border-red-100 bg-red-50 px-4 py-3 text-sm text-red-700 sm:mx-7" role="alert">
              <span>{error}</span>
              <button className="shrink-0 text-red-400 hover:text-red-700" onClick={() => setError(null)} type="button">关闭</button>
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
                  <button className="mt-7 rounded-2xl bg-brand px-5 py-3 text-sm font-semibold text-white shadow-lg shadow-violet-200 transition hover:bg-violet-700" disabled={isCreating} onClick={() => void createSession()} type="button">{isCreating ? "正在新建…" : "新建会话"}</button>
                </div>
              </div>
            )}

            {!isLoadingSession && activeSessionId && messages.length === 0 && !isSending && (
              <div className="flex min-h-full items-center justify-center py-12">
                <div className="max-w-sm text-center">
                  <div className="mx-auto grid size-16 place-items-center rounded-3xl bg-slate-100 text-2xl">💬</div>
                  <h2 className="mt-5 text-xl font-semibold text-slate-900">会话已经准备好了</h2>
                  <p className="mt-2 text-sm leading-6 text-slate-500">在下方输入第一条消息，开始这段对话。</p>
                </div>
              </div>
            )}

            {!isLoadingSession && (messages.length > 0 || isSending) && (
              <div className="mx-auto max-w-4xl space-y-5">
                <MessageTimeline messages={messages} toolCalls={toolCalls} />

                {isSending && (
                  <div className="flex gap-3" aria-live="polite">
                    <div className="grid size-9 shrink-0 place-items-center rounded-xl bg-violet-100 text-xs font-bold text-violet-700">AI</div>
                    <div className="flex items-center gap-1.5 rounded-3xl rounded-tl-md border border-slate-100 bg-slate-50 px-5 py-4">
                      {[0, 1, 2].map((item) => <span className="size-2 animate-pulse rounded-full bg-violet-400" key={item} style={{ animationDelay: `${item * 150}ms` }} />)}
                      <span className="ml-2 text-xs text-slate-400">助手正在思考</span>
                    </div>
                  </div>
                )}
                <div ref={messageEndRef} />
              </div>
            )}
          </div>

          <ChatComposer
            disabled={!activeSessionId || isLoadingSession}
            isSending={isSending}
            onChange={(value) => {
              setInput(value);
              if (error === "请输入消息内容后再发送。") setError(null);
            }}
            onEmptySubmit={() => setError("请输入消息内容后再发送。")}
            onSubmit={(content) => void sendMessage(content)}
            value={input}
          />
        </section>
      </div>
    </main>
  );
}