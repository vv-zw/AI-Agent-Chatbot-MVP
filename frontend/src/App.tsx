import { useCallback, useEffect, useRef, useState } from "react";

import { ChatComposer } from "./components/ChatComposer";
import { MessageTimeline } from "./components/MessageTimeline";
import { ProviderSwitcher } from "./components/ProviderSwitcher";
import { LogoMark, SessionSidebar } from "./components/SessionSidebar";
import { api } from "./lib/api";
import type { ChatMessage, ChatSession, LLMProviderName, LLMProviderStatus, ToolCall } from "./types/api";

const MAX_USER_MESSAGE_LENGTH = 10_000;

function getErrorMessage(error: unknown, fallback: string) {
  return error instanceof Error && error.message ? error.message : fallback;
}

export default function App() {
  const [sessions, setSessions] = useState<ChatSession[]>([]);
  const [activeSessionId, setActiveSessionId] = useState<string | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [toolCalls, setToolCalls] = useState<ToolCall[]>([]);
  const [providerStatus, setProviderStatus] = useState<LLMProviderStatus | null>(null);
  const [providerMessage, setProviderMessage] = useState<string | null>(null);
  const [input, setInput] = useState("");
  const [isLoadingSessions, setIsLoadingSessions] = useState(true);
  const [isLoadingSession, setIsLoadingSession] = useState(false);
  const [isLoadingProvider, setIsLoadingProvider] = useState(true);
  const [isSwitchingProvider, setIsSwitchingProvider] = useState(false);
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
        const status = await api.getLLMProvider();
        if (isCancelled) return;
        setProviderStatus(status);
      } catch (caught) {
        if (!isCancelled) {
          setProviderMessage(getErrorMessage(caught, "LLM 模式状态加载失败。"));
        }
      } finally {
        if (!isCancelled) setIsLoadingProvider(false);
      }
    })();

    return () => {
      isCancelled = true;
    };
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

  async function switchProvider(provider: LLMProviderName) {
    if (isSwitchingProvider || providerStatus?.provider === provider) return;
    setIsSwitchingProvider(true);
    setProviderMessage(null);
    setError(null);

    try {
      const result = await api.switchLLMProvider({ provider });
      setProviderStatus((current) => ({
        available_providers: current?.available_providers ?? ["mock", "openai"],
        provider: result.provider,
        openai_configured: result.openai_configured,
      }));
      setProviderMessage(result.provider === "openai" ? "已切换到真实接口模式。" : "已切换回 Mock 演示模式，工具调用演示可继续使用。");
    } catch (caught) {
      setProviderMessage(getErrorMessage(caught, "LLM 模式切换失败，请稍后重试。"));
    } finally {
      setIsSwitchingProvider(false);
    }
  }

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
      setSessions((current) => current
        .map((session) => session.id === sessionId
          ? {
              ...session,
              title: session.title === "New conversation" ? content.slice(0, 40) : session.title,
              updated_at: result.assistant_message.created_at,
            }
          : session)
        .sort((left, right) => right.updated_at.localeCompare(left.updated_at)));

      try {
        const refreshedSessions = await api.listSessions();
        setSessions(refreshedSessions);
      } catch {
        setError("消息已发送，但会话列表刷新失败；重新加载页面后可恢复同步。");
      }
    } catch (caught) {
      setError(getErrorMessage(caught, "消息发送失败，请稍后重试。"));
    } finally {
      setIsSending(false);
    }
  }

  return (
    <main className="min-h-screen bg-canvas p-0 text-ink md:p-5">
      <div className="mx-auto grid min-h-screen max-w-[1440px] overflow-hidden border border-line bg-panel shadow-shell md:min-h-[calc(100vh-2.5rem)] md:grid-cols-[312px_minmax(0,1fr)] md:rounded-[1.75rem]">
        <SessionSidebar
          activeSessionId={activeSessionId}
          isCreating={isCreating}
          isLoading={isLoadingSessions}
          interactionDisabled={isSending}
          onCreateSession={() => void createSession()}
          onSelectSession={(sessionId) => void loadSession(sessionId)}
          sessions={sessions}
        />

        <section className="flex min-h-screen min-w-0 flex-col bg-parchment bg-arcana [background-size:36px_36px] md:min-h-0">
          <header className="flex min-h-24 flex-wrap items-center gap-3 border-b border-line bg-panel/90 px-4 py-3 sm:px-7">
            <div className="md:hidden"><LogoMark /></div>
            <div className="min-w-0 flex-1">
              <p className="text-[11px] font-semibold uppercase tracking-[0.14em] text-muted">魔法书页面 · 当前工作台</p>
              <h1 className="mt-1 truncate text-xl font-semibold tracking-tight text-ink">{activeSession?.title ?? "开启一条新卷轴"}</h1>
              <p className="mt-0.5 text-xs text-muted">
                {activeSession ? "消息、工具调用与执行结果已同步保存" : "开启会话后记录一次完整 Agent 任务"}
              </p>
            </div>
            <ProviderSwitcher
              isLoading={isLoadingProvider}
              isSwitching={isSwitchingProvider}
              message={providerMessage}
              onSwitch={(provider) => void switchProvider(provider)}
              status={providerStatus}
            />
            <div className="flex items-center gap-2 md:hidden">
              {sessions.length > 0 && (
                <select aria-label="选择会话" className="max-w-32 rounded-xl border border-line bg-white px-2 py-2 text-xs outline-none focus:ring-4 focus:ring-brand/10" disabled={isSending} onChange={(event) => void loadSession(event.target.value)} value={activeSessionId ?? ""}>
                  {sessions.map((session) => <option key={session.id} value={session.id}>{session.title}</option>)}
                </select>
              )}
              <button aria-label="新建会话" className="grid size-10 place-items-center rounded-xl bg-brand text-lg text-white disabled:opacity-50" disabled={isCreating || isSending} onClick={() => void createSession()} type="button">✦</button>
            </div>
          </header>

          {error && (
            <div className="mx-4 mt-4 flex items-start justify-between gap-3 rounded-2xl border border-danger/20 bg-[#fff1f1] px-4 py-3 text-sm text-danger sm:mx-7" role="alert">
              <span>{error}</span>
              <button className="shrink-0 text-danger/60 transition hover:text-danger" onClick={() => setError(null)} type="button">关闭</button>
            </div>
          )}

          <div className="min-h-0 flex-1 overflow-y-auto px-4 py-6 sm:px-7">
            {isLoadingSession && (
              <div className="mx-auto max-w-4xl space-y-5" aria-label="正在加载消息">
                <div className="h-24 w-2/3 animate-pulse rounded-3xl border border-line bg-panel" />
                <div className="ml-auto h-20 w-1/2 animate-pulse rounded-3xl bg-[#f3edff]" />
              </div>
            )}

            {!isLoadingSession && !activeSessionId && (
              <div className="flex min-h-full items-center justify-center py-12">
                <div className="max-w-md rounded-[2rem] border border-line bg-panel/90 p-8 text-center shadow-scroll">
                  <div className="mx-auto grid size-16 place-items-center rounded-3xl border border-brand/20 bg-[#f3edff] text-2xl font-semibold text-brandDeep shadow-sm">TA</div>
                  <h2 className="mt-6 text-2xl font-semibold tracking-tight text-ink">开启一条工具卷轴</h2>
                  <p className="mt-3 text-sm leading-7 text-muted">用一次会话串起问题、Agent 回信和工具施放记录，适合录屏展示完整任务流。</p>
                  <button className="mt-7 rounded-2xl bg-brand px-5 py-3 text-sm font-semibold text-white shadow-scroll transition hover:bg-brandDeep focus:outline-none focus:ring-4 focus:ring-brand/15" disabled={isCreating} onClick={() => void createSession()} type="button">{isCreating ? "正在开启..." : "开启新卷轴"}</button>
                </div>
              </div>
            )}

            {!isLoadingSession && activeSessionId && messages.length === 0 && !isSending && (
              <div className="flex min-h-full items-center justify-center py-12">
                <div className="max-w-sm rounded-[2rem] border border-line bg-panel/90 p-7 text-center shadow-sm">
                  <div className="mx-auto grid size-14 place-items-center rounded-2xl border border-accent/30 bg-[#fff8e6] text-xl font-semibold text-accent">✦</div>
                  <h2 className="mt-5 text-xl font-semibold text-ink">卷轴已经铺开</h2>
                  <p className="mt-2 text-sm leading-6 text-muted">在下方输入第一条指令，开始记录你的 Agent 任务过程。</p>
                </div>
              </div>
            )}

            {!isLoadingSession && (messages.length > 0 || isSending) && (
              <div className="mx-auto max-w-4xl space-y-5">
                <MessageTimeline messages={messages} toolCalls={toolCalls} />

                {isSending && (
                  <div className="flex gap-3" aria-live="polite">
                    <div className="grid size-9 shrink-0 place-items-center rounded-2xl border border-brand/20 bg-[#f3edff] text-xs font-semibold text-brandDeep">回</div>
                    <div className="flex items-center gap-1.5 rounded-3xl rounded-tl-md border border-line bg-panel px-5 py-4 shadow-sm">
                      {[0, 1, 2].map((item) => <span className="size-2 animate-pulse rounded-full bg-brand/50" key={item} style={{ animationDelay: `${item * 150}ms` }} />)}
                      <span className="ml-2 text-xs text-muted">Agent 正在整理回复</span>
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
            maxLength={MAX_USER_MESSAGE_LENGTH}
            onEmptySubmit={() => setError("请输入消息内容后再发送。")}
            onSubmit={(content) => void sendMessage(content)}
            onTooLongSubmit={() => setError(`消息长度不能超过 ${MAX_USER_MESSAGE_LENGTH} 个字符。`)}
            value={input}
          />
        </section>
      </div>
    </main>
  );
}
