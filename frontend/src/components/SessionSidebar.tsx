import type { ChatSession } from "../types/api";

interface SessionSidebarProps {
  sessions: ChatSession[];
  activeSessionId: string | null;
  isLoading: boolean;
  isCreating: boolean;
  interactionDisabled: boolean;
  onCreateSession: () => void;
  onSelectSession: (sessionId: string) => void;
}

function formatSessionTime(value: string) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "";

  return new Intl.DateTimeFormat("zh-CN", {
    month: "numeric",
    day: "numeric",
  }).format(date);
}

export function LogoMark() {
  return (
    <div className="grid size-10 shrink-0 place-items-center rounded-xl border border-brand/15 bg-brand text-sm font-semibold text-white shadow-soft">
      AG
    </div>
  );
}

export function SessionSidebar({
  sessions,
  activeSessionId,
  isLoading,
  isCreating,
  interactionDisabled,
  onCreateSession,
  onSelectSession,
}: SessionSidebarProps) {
  return (
    <aside className="hidden min-h-0 flex-col border-r border-line bg-[#f7f7f2] p-5 text-ink md:flex">
      <div className="flex items-center gap-3 px-1">
        <LogoMark />
        <div>
          <p className="text-sm font-semibold tracking-tight">Agent Desk</p>
          <p className="mt-0.5 text-xs text-muted">任务协作与执行记录</p>
        </div>
      </div>

      <button
        className="mt-7 flex w-full items-center justify-center gap-2 rounded-xl bg-brand px-4 py-3 text-sm font-semibold text-white shadow-soft transition hover:bg-[#264d43] focus:outline-none focus:ring-4 focus:ring-brand/15 disabled:opacity-60"
        disabled={isCreating || interactionDisabled}
        onClick={onCreateSession}
        type="button"
      >
        <span className="text-lg leading-none">{isCreating ? "···" : "＋"}</span>
        {isCreating ? "正在新建" : "新建会话"}
      </button>

      <div className="mt-7 flex min-h-0 flex-1 flex-col">
        <p className="px-2 text-[11px] font-semibold uppercase tracking-[0.16em] text-muted">
          最近会话
        </p>
        <nav className="mt-3 min-h-0 flex-1 space-y-1 overflow-y-auto pr-1" aria-label="会话列表">
          {isLoading && sessions.length === 0 && (
            <div className="space-y-2" aria-label="正在加载会话">
              {[0, 1, 2].map((item) => (
                <div className="h-16 animate-pulse rounded-xl bg-[#ecebe4]" key={item} />
              ))}
            </div>
          )}

          {!isLoading && sessions.length === 0 && (
            <div className="rounded-xl border border-dashed border-line bg-panel px-4 py-8 text-center">
              <p className="text-sm text-ink">暂无历史会话</p>
              <p className="mt-1 text-xs leading-5 text-muted">
                新建会话后会显示在这里
              </p>
            </div>
          )}

          {sessions.map((session) => {
            const isActive = session.id === activeSessionId;
            return (
              <button
                aria-current={isActive ? "page" : undefined}
                className={`group w-full rounded-xl border px-3.5 py-3 text-left transition focus:outline-none focus:ring-4 focus:ring-brand/10 ${
                  isActive
                    ? "border-brand/25 bg-white text-ink shadow-soft"
                    : "border-transparent text-muted hover:border-line hover:bg-white hover:text-ink"
                }`}
                disabled={interactionDisabled}
                key={session.id}
                onClick={() => onSelectSession(session.id)}
                type="button"
              >
                <span className="block truncate text-sm font-medium">{session.title}</span>
                <span className={`mt-1 block text-xs ${isActive ? "text-brand" : "text-muted/70"}`}>
                  更新于 {formatSessionTime(session.updated_at)}
                </span>
              </button>
            );
          })}
        </nav>
      </div>

      <div className="mt-4 rounded-xl border border-line bg-panel p-4">
        <div className="flex items-center gap-2 text-xs font-medium text-ink">
          <span className="size-2 rounded-full bg-success" />
          服务端已连接
        </div>
        <p className="mt-2 text-xs leading-5 text-muted">
          会话与消息由服务端持久化保存
        </p>
      </div>
    </aside>
  );
}
