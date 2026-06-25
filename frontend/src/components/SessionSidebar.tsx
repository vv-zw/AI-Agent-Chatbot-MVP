import type { ChatSession } from "../types/api";

interface SessionSidebarProps {
  sessions: ChatSession[];
  activeSessionId: string | null;
  isLoading: boolean;
  isCreating: boolean;
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
    <div className="grid size-10 shrink-0 place-items-center rounded-2xl bg-gradient-to-br from-violet-500 to-indigo-600 text-sm font-bold text-white shadow-lg shadow-violet-950/20">
      AI
    </div>
  );
}

export function SessionSidebar({
  sessions,
  activeSessionId,
  isLoading,
  isCreating,
  onCreateSession,
  onSelectSession,
}: SessionSidebarProps) {
  return (
    <aside className="hidden min-h-0 flex-col bg-slate-950 p-5 text-white md:flex">
      <div className="flex items-center gap-3 px-1">
        <LogoMark />
        <div>
          <p className="text-sm font-semibold">AI Chatbot</p>
          <p className="mt-0.5 text-xs text-slate-400">你的智能工作助手</p>
        </div>
      </div>

      <button
        className="mt-7 flex w-full items-center justify-center gap-2 rounded-2xl bg-white px-4 py-3 text-sm font-semibold text-slate-950 transition hover:bg-violet-50 disabled:opacity-60"
        disabled={isCreating}
        onClick={onCreateSession}
        type="button"
      >
        <span className="text-lg leading-none">{isCreating ? "···" : "＋"}</span>
        {isCreating ? "正在新建" : "新建会话"}
      </button>

      <div className="mt-7 flex min-h-0 flex-1 flex-col">
        <p className="px-2 text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">
          最近会话
        </p>
        <nav className="mt-3 min-h-0 flex-1 space-y-1.5 overflow-y-auto pr-1" aria-label="会话列表">
          {isLoading && sessions.length === 0 && (
            <div className="space-y-2" aria-label="正在加载会话">
              {[0, 1, 2].map((item) => (
                <div className="h-16 animate-pulse rounded-2xl bg-slate-900" key={item} />
              ))}
            </div>
          )}

          {!isLoading && sessions.length === 0 && (
            <div className="rounded-2xl border border-dashed border-slate-800 px-4 py-8 text-center">
              <p className="text-sm text-slate-400">暂无历史会话</p>
              <p className="mt-1 text-xs leading-5 text-slate-600">
                新建会话后会显示在这里
              </p>
            </div>
          )}

          {sessions.map((session) => {
            const isActive = session.id === activeSessionId;
            return (
              <button
                aria-current={isActive ? "page" : undefined}
                className={`group w-full rounded-2xl px-3.5 py-3 text-left transition ${
                  isActive
                    ? "bg-violet-500 text-white shadow-lg shadow-violet-950/30"
                    : "text-slate-300 hover:bg-slate-900 hover:text-white"
                }`}
                key={session.id}
                onClick={() => onSelectSession(session.id)}
                type="button"
              >
                <span className="block truncate text-sm font-medium">{session.title}</span>
                <span className={`mt-1 block text-xs ${isActive ? "text-violet-200" : "text-slate-600"}`}>
                  更新于 {formatSessionTime(session.updated_at)}
                </span>
              </button>
            );
          })}
        </nav>
      </div>

      <div className="mt-4 rounded-2xl bg-slate-900 p-4">
        <div className="flex items-center gap-2 text-xs text-slate-300">
          <span className="size-2 rounded-full bg-emerald-400 shadow-sm shadow-emerald-400" />
          已连接 API
        </div>
        <p className="mt-2 text-xs leading-5 text-slate-500">
          会话与消息由服务端持久化保存
        </p>
      </div>
    </aside>
  );
}