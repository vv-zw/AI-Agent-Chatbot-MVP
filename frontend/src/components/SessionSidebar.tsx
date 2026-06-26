import type { ChatSession } from "../types/api";

interface SessionSidebarProps {
  sessions: ChatSession[];
  activeSessionId: string | null;
  isLoading: boolean;
  isCreating: boolean;
  interactionDisabled: boolean;
  deletingSessionId: string | null;
  onCreateSession: () => void;
  onDeleteSession: (sessionId: string) => void;
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
    <div className="relative grid size-11 shrink-0 place-items-center rounded-2xl border border-brand/25 bg-[#f3edff] text-sm font-semibold text-brandDeep shadow-scroll">
      <span className="absolute -right-1 -top-1 size-3 rounded-full border border-accent/40 bg-accent/80" />
      TA
    </div>
  );
}

export function SessionSidebar({
  sessions,
  activeSessionId,
  isLoading,
  isCreating,
  interactionDisabled,
  deletingSessionId,
  onCreateSession,
  onDeleteSession,
  onSelectSession,
}: SessionSidebarProps) {
  return (
    <aside className="hidden min-h-0 flex-col border-r border-line bg-[#f4eddf] p-5 text-ink md:flex">
      <div className="rounded-2xl border border-line bg-panel/80 p-3 shadow-sm">
        <div className="flex items-center gap-3">
          <LogoMark />
          <div>
            <p className="text-sm font-semibold tracking-tight">ToolMind Arcana</p>
            <p className="mt-0.5 text-xs text-muted">Agent 工具魔法工坊</p>
          </div>
        </div>
      </div>

      <button
        className="mt-5 flex w-full items-center justify-center gap-2 rounded-2xl border border-brand/20 bg-brand px-4 py-3 text-sm font-semibold text-white shadow-scroll transition hover:bg-brandDeep focus:outline-none focus:ring-4 focus:ring-brand/15 disabled:opacity-60"
        disabled={isCreating || interactionDisabled || Boolean(deletingSessionId)}
        onClick={onCreateSession}
        type="button"
      >
        <span className="text-base leading-none">{isCreating ? "···" : "✦"}</span>
        {isCreating ? "正在开启" : "开启新卷轴"}
      </button>

      <div className="mt-7 flex min-h-0 flex-1 flex-col">
        <p className="px-2 text-[11px] font-semibold uppercase tracking-[0.16em] text-muted">
          会话档案
        </p>
        <nav className="mt-3 min-h-0 flex-1 space-y-2 overflow-y-auto pr-1" aria-label="会话列表">
          {isLoading && sessions.length === 0 && (
            <div className="space-y-2" aria-label="正在加载会话">
              {[0, 1, 2].map((item) => (
                <div className="h-[4.25rem] animate-pulse rounded-2xl border border-line bg-panel/70" key={item} />
              ))}
            </div>
          )}

          {!isLoading && sessions.length === 0 && (
            <div className="rounded-2xl border border-dashed border-line bg-panel/75 px-4 py-8 text-center">
              <p className="text-sm font-medium text-ink">暂无卷轴</p>
              <p className="mt-1 text-xs leading-5 text-muted">
                开启新会话后会收纳在这里
              </p>
            </div>
          )}

          {sessions.map((session) => {
            const isActive = session.id === activeSessionId;
            const isDeleting = deletingSessionId === session.id;
            return (
              <div
                className={`group relative flex items-stretch overflow-hidden rounded-2xl border transition focus-within:ring-4 focus-within:ring-brand/10 ${
                  isActive
                    ? "border-brand/35 bg-panel text-ink shadow-scroll"
                    : "border-line/70 bg-[#fbf6eb]/70 text-muted hover:border-brand/20 hover:bg-panel hover:text-ink"
                }`}
                key={session.id}
              >
                <span className={`absolute left-0 top-3 h-8 w-1 rounded-r-full ${isActive ? "bg-accent" : "bg-transparent group-hover:bg-brand/25"}`} />
                <button
                  aria-current={isActive ? "page" : undefined}
                  className="min-w-0 flex-1 px-4 py-3 pr-2 text-left outline-none disabled:opacity-60"
                  disabled={interactionDisabled || Boolean(deletingSessionId)}
                  onClick={() => onSelectSession(session.id)}
                  type="button"
                >
                  <span className="block truncate text-sm font-semibold">{session.title}</span>
                  <span className={`mt-1 flex items-center gap-1.5 text-xs ${isActive ? "text-brandDeep" : "text-muted/75"}`}>
                    <span className="size-1.5 rounded-full bg-current opacity-60" />
                    更新于 {formatSessionTime(session.updated_at)}
                  </span>
                </button>
                <button
                  aria-label={`删除会话：${session.title}`}
                  className="m-2 grid size-9 shrink-0 place-items-center rounded-xl border border-danger/15 bg-[#fff6f3] text-xs font-semibold text-danger opacity-75 transition hover:border-danger/30 hover:bg-[#ffeceb] hover:opacity-100 focus:outline-none focus:ring-4 focus:ring-danger/10 disabled:opacity-40"
                  disabled={interactionDisabled || Boolean(deletingSessionId)}
                  onClick={() => onDeleteSession(session.id)}
                  title="删除会话"
                  type="button"
                >
                  {isDeleting ? (
                    <span className="size-3.5 animate-spin rounded-full border-2 border-danger/30 border-t-danger" />
                  ) : (
                    "×"
                  )}
                </button>
              </div>
            );
          })}
        </nav>
      </div>

      <div className="mt-4 rounded-2xl border border-line bg-panel/80 p-4 shadow-sm">
        <div className="flex items-center gap-2 text-xs font-semibold text-ink">
          <span className="size-2 rounded-full bg-success" />
          后端服务已连接
        </div>
        <p className="mt-2 text-xs leading-5 text-muted">
          会话、消息与工具施放记录会同步保存
        </p>
      </div>
    </aside>
  );
}
