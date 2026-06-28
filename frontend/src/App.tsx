import { useCallback, useEffect, useRef, useState } from "react";

import { ChatComposer } from "./components/ChatComposer";
import { MessageTimeline } from "./components/MessageTimeline";
import { KnowledgeShelf } from "./components/KnowledgeShelf";
import { ProviderSwitcher } from "./components/ProviderSwitcher";
import { RoleSwitcher } from "./components/RoleSwitcher";
import { LogoMark, SessionSidebar } from "./components/SessionSidebar";
import { api } from "./lib/api";
import type { ChatbotRole, ChatMessage, ChatSession, FeedbackRating, LLMProviderName, LLMProviderStatus, KnowledgeFile, ToolCall } from "./types/api";

const MAX_USER_MESSAGE_LENGTH = 10_000;

function getErrorMessage(error: unknown, fallback: string) {
  return error instanceof Error && error.message ? error.message : fallback;
}

export default function App() {
  const [sessions, setSessions] = useState<ChatSession[]>([]);
  const [roles, setRoles] = useState<ChatbotRole[]>([]);
  const [newSessionRoleId, setNewSessionRoleId] = useState("general");
  const [activeSessionId, setActiveSessionId] = useState<string | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [toolCalls, setToolCalls] = useState<ToolCall[]>([]);
  const [knowledgeFiles, setKnowledgeFiles] = useState<KnowledgeFile[]>([]);
  const [isLoadingKnowledge, setIsLoadingKnowledge] = useState(false);
  const [isUploadingKnowledge, setIsUploadingKnowledge] = useState(false);
  const [knowledgeError, setKnowledgeError] = useState<string | null>(null);
  const [providerStatus, setProviderStatus] = useState<LLMProviderStatus | null>(null);
  const [providerMessage, setProviderMessage] = useState<string | null>(null);
  const [input, setInput] = useState("");
  const [isLoadingSessions, setIsLoadingSessions] = useState(true);
  const [isLoadingSession, setIsLoadingSession] = useState(false);
  const [isLoadingProvider, setIsLoadingProvider] = useState(true);
  const [isLoadingRoles, setIsLoadingRoles] = useState(true);
  const [isSwitchingProvider, setIsSwitchingProvider] = useState(false);
  const [isSwitchingRole, setIsSwitchingRole] = useState(false);
  const [isCreating, setIsCreating] = useState(false);
  const [isDeletingSession, setIsDeletingSession] = useState<string | null>(null);
  const [isSending, setIsSending] = useState(false);
  const [useStreaming, setUseStreaming] = useState(true);
  const [streamingPhase, setStreamingPhase] = useState<"saving" | "tool" | "replying" | null>(null);
  const [error, setError] = useState<string | null>(null);
  const detailRequestId = useRef(0);
  const messageViewportRef = useRef<HTMLDivElement>(null);
  const shouldFollowOutputRef = useRef(true);

  const activeSession = sessions.find((session) => session.id === activeSessionId) ?? null;
  const selectedRoleId = activeSession?.role_id ?? newSessionRoleId;

  useEffect(() => {
    if (!shouldFollowOutputRef.current) return;

    const frame = window.requestAnimationFrame(() => {
      const viewport = messageViewportRef.current;
      if (!viewport) return;
      viewport.scrollTo({
        top: viewport.scrollHeight,
        behavior: isSending ? "auto" : "smooth",
      });
    });

    return () => window.cancelAnimationFrame(frame);
  }, [messages, toolCalls, isSending, streamingPhase]);

  const loadSession = useCallback(async (sessionId: string) => {
    const requestId = ++detailRequestId.current;
    shouldFollowOutputRef.current = true;
    setActiveSessionId(sessionId);
    setIsLoadingSession(true);
    setIsLoadingKnowledge(true);
    setError(null);
    setKnowledgeError(null);

    try {
      const [detail, files] = await Promise.all([api.getSession(sessionId), api.listKnowledgeFiles(sessionId)]);
      if (requestId !== detailRequestId.current) return;
      setMessages(detail.messages);
      setToolCalls(detail.tool_calls);
      setKnowledgeFiles(files);
      setSessions((current) => current.map((item) => item.id === detail.id ? detail : item));
    } catch (caught) {
      if (requestId !== detailRequestId.current) return;
      setMessages([]);
      setToolCalls([]);
      setKnowledgeFiles([]);
      setError(getErrorMessage(caught, "加载会话失败，请稍后重试。"));
    } finally {
      if (requestId === detailRequestId.current) {
        setIsLoadingSession(false);
        setIsLoadingKnowledge(false);
      }
    }
  }, []);

  useEffect(() => {
    let isCancelled = false;

    void (async () => {
      try {
        const items = await api.listRoles();
        if (!isCancelled) setRoles(items);
      } catch (caught) {
        if (!isCancelled) setError(getErrorMessage(caught, "助手角色加载失败。"));
      } finally {
        if (!isCancelled) setIsLoadingRoles(false);
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

  async function switchRole(roleId: string) {
    if (isSwitchingRole || roleId === selectedRoleId) return;
    if (!activeSessionId) {
      setNewSessionRoleId(roleId);
      return;
    }

    const nextRole = roles.find((role) => role.role_id === roleId);
    const confirmed = window.confirm(
      `推荐新建会话使用“${nextRole?.name ?? roleId}”。确定要修改当前会话角色吗？后续消息会使用新的 system prompt，已有消息会保留。`,
    );
    if (!confirmed) return;

    setIsSwitchingRole(true);
    setError(null);
    try {
      const updated = await api.updateSessionRole(activeSessionId, { role_id: roleId });
      setSessions((current) => current.map((session) => session.id === updated.id ? updated : session));
      setNewSessionRoleId(roleId);
    } catch (caught) {
      setError(getErrorMessage(caught, "助手角色切换失败，请稍后重试。"));
    } finally {
      setIsSwitchingRole(false);
    }
  }

  async function createSession() {
    if (isCreating || isSending) return;
    setIsCreating(true);
    setError(null);

    try {
      const created = await api.createSession({ role_id: newSessionRoleId });
      detailRequestId.current += 1;
      setSessions((current) => [created, ...current.filter((item) => item.id !== created.id)]);
      setActiveSessionId(created.id);
      setMessages([]);
      setToolCalls([]);
      setKnowledgeFiles([]);
      setKnowledgeError(null);
      setInput("");
    } catch (caught) {
      setError(getErrorMessage(caught, "新建会话失败，请稍后重试。"));
    } finally {
      setIsCreating(false);
    }
  }

  async function deleteSession(sessionId: string) {
    if (isSending || isCreating || isDeletingSession) return;
    const target = sessions.find((session) => session.id === sessionId);
    const confirmed = window.confirm(`确定删除“${target?.title ?? "这条会话"}”吗？删除后不可恢复。`);
    if (!confirmed) return;

    setIsDeletingSession(sessionId);
    setError(null);

    try {
      await api.deleteSession(sessionId);
      const remaining = sessions.filter((session) => session.id !== sessionId);
      setSessions(remaining);

      if (activeSessionId === sessionId) {
        detailRequestId.current += 1;
        const nextSession = remaining[0] ?? null;
        if (nextSession) {
          await loadSession(nextSession.id);
        } else {
          setActiveSessionId(null);
          setMessages([]);
          setToolCalls([]);
          setKnowledgeFiles([]);
          setKnowledgeError(null);
          setInput("");
        }
      }
    } catch (caught) {
      setError(getErrorMessage(caught, "删除会话失败，请稍后重试。"));
    } finally {
      setIsDeletingSession(null);
    }
  }

  async function uploadKnowledge(file: File) {
    if (!activeSessionId || isUploadingKnowledge) return;
    const sessionId = activeSessionId;
    setIsUploadingKnowledge(true);
    setKnowledgeError(null);
    try {
      const uploaded = await api.uploadKnowledgeFile(sessionId, file);
      if (activeSessionId !== sessionId) return;
      setKnowledgeFiles((current) => [uploaded, ...current]);
    } catch (caught) {
      setKnowledgeError(getErrorMessage(caught, "文件上传失败，请检查格式和大小后重试。"));
    } finally {
      setIsUploadingKnowledge(false);
    }
  }
  async function submitFeedback(messageId: string, rating: FeedbackRating, reason: string) {
    const message = messages.find((item) => item.id === messageId);
    if (!message || message.role !== "assistant") {
      throw new Error("只能对已保存的 AI 回复提交反馈。");
    }

    const feedback = await api.submitFeedback(
      message.session_id,
      messageId,
      { rating, reason },
    );
    setMessages((current) => current.map((item) =>
      item.id === messageId ? { ...item, feedback } : item));
  }

  async function sendMessage(content: string) {
    if (!activeSessionId || isSending) return;
    const sessionId = activeSessionId;
    const provider = providerStatus?.provider ?? "mock";
    shouldFollowOutputRef.current = true;
    setIsSending(true);
    setError(null);
    let optimisticUserId: string | null = null;

    try {
      if (useStreaming) {
        const stamp = Date.now();
        const temporaryUserId = `stream-user-${stamp}`;
        optimisticUserId = temporaryUserId;
        const temporaryAssistantId = `stream-assistant-${stamp}`;
        const createdAt = new Date().toISOString();
        const optimisticUser: ChatMessage = {
          id: temporaryUserId,
          session_id: sessionId,
          role: "user",
          content,
          created_at: createdAt,
          delivery_status: "complete",
        };
        setInput("");
        setStreamingPhase("saving");
        setMessages((current) => [...current, optimisticUser]);

        const upsertToolCall = (call: ToolCall) => {
          setToolCalls((current) => {
            const exists = current.some((item) => item.id === call.id);
            return exists
              ? current.map((item) => item.id === call.id ? call : item)
              : [...current, call];
          });
        };

        await api.sendMessageStream(sessionId, { content, provider }, (streamEvent) => {
          if (streamEvent.event === "user_message_saved") {
            setMessages((current) => current.map((message) =>
              message.id === temporaryUserId ? streamEvent.data.user_message : message));
          } else if (streamEvent.event === "tool_call_start") {
            setStreamingPhase("tool");
            upsertToolCall(streamEvent.data.tool_call);
          } else if (streamEvent.event === "tool_call_result") {
            upsertToolCall(streamEvent.data.tool_call);
          } else if (streamEvent.event === "assistant_delta") {
            setStreamingPhase("replying");
            setMessages((current) => {
              const existing = current.find((message) => message.id === temporaryAssistantId);
              if (existing) {
                return current.map((message) => message.id === temporaryAssistantId
                  ? { ...message, content: message.content + streamEvent.data.delta }
                  : message);
              }
              return [...current, {
                id: temporaryAssistantId,
                session_id: sessionId,
                role: "assistant",
                content: streamEvent.data.delta,
                created_at: new Date().toISOString(),
                delivery_status: "streaming",
              }];
            });
          } else if (streamEvent.event === "assistant_done") {
            const result = streamEvent.data;
            setMessages((current) => {
              const withoutTemporaryUser = current.map((message) =>
                message.id === temporaryUserId ? result.user_message : message);
              return withoutTemporaryUser.some((message) => message.id === temporaryAssistantId)
                ? withoutTemporaryUser.map((message) => message.id === temporaryAssistantId
                  ? { ...result.assistant_message, delivery_status: "complete" }
                  : message)
                : [...withoutTemporaryUser, { ...result.assistant_message, delivery_status: "complete" }];
            });
            result.tool_calls.forEach(upsertToolCall);
            setSessions((current) => current
              .map((session) => session.id === sessionId
                ? {
                    ...session,
                    title: session.title === "New conversation" ? content.slice(0, 40) : session.title,
                    updated_at: result.assistant_message.created_at,
                  }
                : session)
              .sort((left, right) => right.updated_at.localeCompare(left.updated_at)));
          }
        });
      } else {
        const result = await api.sendMessage(sessionId, { content, provider });
        if (activeSessionId !== sessionId) return;
        setInput("");
        setMessages((current) => [...current, result.user_message, result.assistant_message]);
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
      }

      try {
        setSessions(await api.listSessions());
      } catch {
        setError("消息已发送，但会话列表刷新失败；重新加载页面后可恢复同步。");
      }
    } catch (caught) {
      setMessages((current) => current
        .filter((message) => message.id !== optimisticUserId)
        .map((message) =>
          message.delivery_status === "streaming"
          ? { ...message, delivery_status: "failed" }
          : message));
      setError(getErrorMessage(caught, "消息发送失败，请稍后重试。"));
    } finally {
      setStreamingPhase(null);
      setIsSending(false);
    }
  }
  return (
    <main className="h-[100dvh] overflow-hidden bg-canvas p-0 text-ink md:p-5">
      <div className="mx-auto grid h-full max-w-[1440px] overflow-hidden bg-panel md:grid-cols-[312px_minmax(0,1fr)] md:rounded-[1.75rem] md:border md:border-line md:shadow-shell">
        <SessionSidebar
          activeSessionId={activeSessionId}
          isCreating={isCreating}
          isLoading={isLoadingSessions}
          interactionDisabled={isSending}
          deletingSessionId={isDeletingSession}
          newSessionRoleId={newSessionRoleId}
          onCreateSession={() => void createSession()}
          onDeleteSession={(sessionId) => void deleteSession(sessionId)}
          onNewSessionRoleChange={setNewSessionRoleId}
          onSelectSession={(sessionId) => void loadSession(sessionId)}
          roles={roles}
          sessions={sessions}
        />

        <section className="flex h-full min-h-0 min-w-0 flex-col overflow-hidden bg-parchment bg-arcana [background-size:36px_36px]">
          <header className="shrink-0 border-b border-line bg-panel/95 px-3 py-2.5 sm:px-7 sm:py-3">
            <div className="flex items-center gap-3">
              <div className="md:hidden"><LogoMark /></div>
              <div className="min-w-0 flex-1">
                <p className="hidden text-[11px] font-semibold uppercase tracking-[0.14em] text-muted md:block">魔法书页面 · 当前工作台</p>
                <h1 className="truncate text-base font-semibold tracking-tight text-ink md:mt-1 md:text-xl">{activeSession?.title ?? "开启一条新卷轴"}</h1>
                <p className="mt-0.5 hidden text-xs text-muted md:block">
                  {activeSession ? "消息、工具调用与执行结果已同步保存" : "开启会话后记录一次完整 Agent 任务"}
                </p>
              </div>

              <div className="hidden flex-wrap items-start gap-3 md:flex">
                <RoleSwitcher
                  disabled={isCreating || isSending || Boolean(isDeletingSession)}
                  isLoading={isLoadingRoles}
                  isSwitching={isSwitchingRole}
                  onChange={(roleId) => void switchRole(roleId)}
                  roles={roles}
                  selectedRoleId={selectedRoleId}
                />
                <ProviderSwitcher
                  isLoading={isLoadingProvider}
                  isSwitching={isSwitchingProvider}
                  message={providerMessage}
                  onSwitch={(provider) => void switchProvider(provider)}
                  status={providerStatus}
                />
              </div>

              <button
                aria-label="新建会话"
                className="grid size-10 shrink-0 place-items-center rounded-xl bg-brand text-lg text-white shadow-sm transition hover:bg-brandDeep focus:outline-none focus:ring-4 focus:ring-brand/15 disabled:opacity-50 md:hidden"
                disabled={isCreating || isSending}
                onClick={() => void createSession()}
                title="新建会话"
                type="button"
              >
                {isCreating ? <span className="size-4 animate-spin rounded-full border-2 border-white/40 border-t-white" /> : "✦"}
              </button>
            </div>

            <div className="mt-2 grid gap-2 md:hidden">
              <div className="grid grid-cols-[minmax(0,1fr)_2.5rem] gap-2">
                <label className="min-w-0 rounded-xl border border-line bg-[#fffaf1] px-2.5 py-1.5 transition focus-within:border-brand/35 focus-within:ring-4 focus-within:ring-brand/10">
                  <span className="block text-[9px] font-semibold uppercase tracking-[0.12em] text-muted">当前会话</span>
                  <select
                    aria-label="选择会话"
                    className="mt-0.5 w-full truncate bg-transparent text-xs font-semibold text-ink outline-none disabled:text-muted"
                    disabled={isSending || sessions.length === 0}
                    onChange={(event) => void loadSession(event.target.value)}
                    value={activeSessionId ?? ""}
                  >
                    {sessions.length === 0 && <option value="">暂无会话</option>}
                    {sessions.map((session) => <option key={session.id} value={session.id}>{session.title}</option>)}
                  </select>
                </label>
                <button
                  aria-label="删除当前会话"
                  className="grid size-10 place-items-center self-center rounded-xl border border-danger/20 bg-[#fff7f5] text-xl leading-none text-danger transition hover:bg-[#fff1f1] focus:outline-none focus:ring-4 focus:ring-danger/10 disabled:opacity-40"
                  disabled={!activeSessionId || isSending || isCreating || Boolean(isDeletingSession)}
                  onClick={() => activeSessionId && void deleteSession(activeSessionId)}
                  title="删除当前会话"
                  type="button"
                >
                  {isDeletingSession === activeSessionId ? <span className="size-4 animate-spin rounded-full border-2 border-danger/25 border-t-danger" /> : "×"}
                </button>
              </div>

              <div className="grid grid-cols-2 gap-2">
                <label className="min-w-0 rounded-xl border border-line bg-white px-2.5 py-1.5 transition focus-within:border-brand/35 focus-within:ring-4 focus-within:ring-brand/10">
                  <span className="block text-[9px] font-semibold uppercase tracking-[0.12em] text-muted">助手角色</span>
                  <select
                    aria-label="选择助手角色"
                    className="mt-0.5 w-full truncate bg-transparent text-xs font-semibold text-ink outline-none disabled:text-muted"
                    disabled={isCreating || isSending || isLoadingRoles || isSwitchingRole || Boolean(isDeletingSession) || roles.length === 0}
                    onChange={(event) => void switchRole(event.target.value)}
                    value={selectedRoleId}
                  >
                    {roles.map((role) => <option key={role.role_id} value={role.role_id}>{role.name}</option>)}
                  </select>
                </label>
                <label className="min-w-0 rounded-xl border border-line bg-white px-2.5 py-1.5 transition focus-within:border-brand/35 focus-within:ring-4 focus-within:ring-brand/10">
                  <span className="block text-[9px] font-semibold uppercase tracking-[0.12em] text-muted">模型模式</span>
                  <select
                    aria-label="选择模型模式"
                    className="mt-0.5 w-full truncate bg-transparent text-xs font-semibold text-ink outline-none disabled:text-muted"
                    disabled={isLoadingProvider || isSwitchingProvider || !providerStatus}
                    onChange={(event) => void switchProvider(event.target.value as LLMProviderName)}
                    value={providerStatus?.provider ?? "mock"}
                  >
                    <option value="mock">Mock 工具演示</option>
                    <option value="openai">DeepSeek</option>
                  </select>
                </label>
              </div>

              {(providerMessage || (providerStatus && !providerStatus.openai_configured)) && (
                <p className="truncate px-1 text-[10px] leading-4 text-warning" title={providerMessage ?? "真实 API 尚未配置"}>
                  {providerMessage ?? "真实 API 尚未配置，当前可使用 Mock 工具演示"}
                </p>
              )}
            </div>
          </header>

          <KnowledgeShelf
            disabled={!activeSessionId || isLoadingSession || isSending}
            error={knowledgeError}
            files={knowledgeFiles}
            isLoading={isLoadingKnowledge}
            isUploading={isUploadingKnowledge}
            onUpload={(file) => void uploadKnowledge(file)}
          />
          {error && (
            <div className="mx-3 mt-3 flex items-start justify-between gap-3 rounded-xl border border-danger/20 bg-[#fff1f1] px-3 py-2.5 text-xs text-danger sm:mx-7 sm:mt-4 sm:rounded-2xl sm:px-4 sm:py-3 sm:text-sm" role="alert">
              <span>{error}</span>
              <button className="shrink-0 text-danger/60 transition hover:text-danger" onClick={() => setError(null)} type="button">关闭</button>
            </div>
          )}

          <div
            className="min-h-0 flex-1 overflow-y-auto overscroll-contain px-3 py-4 [scrollbar-gutter:stable] sm:px-7 sm:py-6"
            onScroll={(event) => {
              if (isSending) return;
              const viewport = event.currentTarget;
              shouldFollowOutputRef.current =
                viewport.scrollHeight - viewport.scrollTop - viewport.clientHeight < 96;
            }}
            ref={messageViewportRef}
          >
            {isLoadingSession && (
              <div className="mx-auto max-w-4xl space-y-5" aria-label="正在加载消息">
                <div className="h-24 w-2/3 animate-pulse rounded-3xl border border-line bg-panel" />
                <div className="ml-auto h-20 w-1/2 animate-pulse rounded-3xl bg-[#f3edff]" />
              </div>
            )}

            {!isLoadingSession && !activeSessionId && (
              <div className="flex min-h-full items-center justify-center py-6 sm:py-12">
                <div className="max-w-md rounded-3xl border border-line bg-panel/90 p-6 text-center shadow-scroll sm:rounded-[2rem] sm:p-8">
                  <div className="mx-auto grid size-16 place-items-center rounded-3xl border border-brand/20 bg-[#f3edff] text-2xl font-semibold text-brandDeep shadow-sm">TA</div>
                  <h2 className="mt-6 text-2xl font-semibold tracking-tight text-ink">开启一条工具卷轴</h2>
                  <p className="mt-3 text-sm leading-7 text-muted">用一次会话串起问题、Agent 回信和工具施放记录，适合录屏展示完整任务流。</p>
                  <button className="mt-7 rounded-2xl bg-brand px-5 py-3 text-sm font-semibold text-white shadow-scroll transition hover:bg-brandDeep focus:outline-none focus:ring-4 focus:ring-brand/15" disabled={isCreating} onClick={() => void createSession()} type="button">{isCreating ? "正在开启..." : "开启新卷轴"}</button>
                </div>
              </div>
            )}

            {!isLoadingSession && activeSessionId && messages.length === 0 && !isSending && (
              <div className="flex min-h-full items-center justify-center py-6 sm:py-12">
                <div className="max-w-sm rounded-3xl border border-line bg-panel/90 p-6 text-center shadow-sm sm:rounded-[2rem] sm:p-7">
                  <div className="mx-auto grid size-14 place-items-center rounded-2xl border border-accent/30 bg-[#fff8e6] text-xl font-semibold text-accent">✦</div>
                  <h2 className="mt-5 text-xl font-semibold text-ink">卷轴已经铺开</h2>
                  <p className="mt-2 text-sm leading-6 text-muted">在下方输入第一条指令，开始记录你的 Agent 任务过程。</p>
                </div>
              </div>
            )}

            {!isLoadingSession && (messages.length > 0 || isSending) && (
              <div className="mx-auto max-w-4xl space-y-5">
                <MessageTimeline messages={messages} onFeedback={submitFeedback} toolCalls={toolCalls} />

                {isSending && (
                  <div className="flex gap-3" aria-live="polite">
                    <div className="grid size-9 shrink-0 place-items-center rounded-2xl border border-brand/20 bg-[#f3edff] text-xs font-semibold text-brandDeep">回</div>
                    <div className="flex items-center gap-1.5 rounded-3xl rounded-tl-md border border-line bg-panel px-5 py-4 shadow-sm">
                      {[0, 1, 2].map((item) => <span className="size-2 animate-pulse rounded-full bg-brand/50" key={item} style={{ animationDelay: `${item * 150}ms` }} />)}
                      <span className="ml-2 text-xs text-muted">{streamingPhase === "tool" ? "Agent 正在执行工具" : streamingPhase === "saving" ? "正在保存用户消息" : useStreaming ? "Agent 正在流式回复" : "Agent 正在整理回复"}</span>
                    </div>
                  </div>
                )}
                <div aria-hidden="true" className="h-px" />
              </div>
            )}
          </div>

          <ChatComposer
            disabled={!activeSessionId || isLoadingSession}
            isSending={isSending}
            useStreaming={useStreaming}
            onStreamingChange={setUseStreaming}
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
