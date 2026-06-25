function LogoMark() {
  return (
    <div className="grid size-10 shrink-0 place-items-center rounded-2xl bg-gradient-to-br from-violet-500 to-indigo-600 text-sm font-bold text-white shadow-lg shadow-violet-950/20">
      AI
    </div>
  );
}

export default function App() {
  return (
    <main className="min-h-screen bg-canvas p-0 text-ink md:p-4">
      <div className="mx-auto grid min-h-screen max-w-[1440px] overflow-hidden bg-white shadow-2xl shadow-slate-300/40 md:min-h-[calc(100vh-2rem)] md:grid-cols-[300px_minmax(0,1fr)] md:rounded-[28px]">
        <aside className="hidden flex-col bg-slate-950 p-5 text-white md:flex">
          <div className="flex items-center gap-3 px-1">
            <LogoMark />
            <div>
              <p className="text-sm font-semibold">AI Chatbot</p>
              <p className="mt-0.5 text-xs text-slate-400">你的智能工作助手</p>
            </div>
          </div>

          <button
            className="mt-7 flex w-full items-center justify-center gap-2 rounded-2xl bg-white px-4 py-3 text-sm font-semibold text-slate-950 transition hover:bg-violet-50"
            type="button"
          >
            <span className="text-lg leading-none">＋</span>
            新建会话
          </button>

          <div className="mt-7">
            <p className="px-2 text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">
              最近会话
            </p>
            <div className="mt-3 rounded-2xl border border-dashed border-slate-800 px-4 py-8 text-center">
              <p className="text-sm text-slate-400">暂无历史会话</p>
              <p className="mt-1 text-xs leading-5 text-slate-600">
                新建会话后会显示在这里
              </p>
            </div>
          </div>

          <div className="mt-auto rounded-2xl bg-slate-900 p-4">
            <div className="flex items-center gap-2 text-xs text-slate-300">
              <span className="size-2 rounded-full bg-emerald-400 shadow-sm shadow-emerald-400" />
              后端服务状态
            </div>
            <p className="mt-2 text-xs leading-5 text-slate-500">
              会话与消息由服务端持久化保存
            </p>
          </div>
        </aside>

        <section className="flex min-h-screen min-w-0 flex-col bg-white md:min-h-0">
          <header className="flex min-h-20 items-center gap-3 border-b border-slate-100 px-4 sm:px-7">
            <div className="md:hidden">
              <LogoMark />
            </div>
            <div className="min-w-0">
              <h1 className="truncate font-semibold text-slate-900">开始新对话</h1>
              <p className="mt-0.5 text-xs text-slate-500">
                新建一个会话，开始与 AI 助手交流
              </p>
            </div>
          </header>

          <div className="flex flex-1 items-center justify-center px-6 py-12">
            <div className="max-w-md text-center">
              <div className="mx-auto grid size-20 place-items-center rounded-[28px] bg-violet-50 text-3xl shadow-inner shadow-violet-100">
                ✦
              </div>
              <h2 className="mt-6 text-2xl font-semibold tracking-tight text-slate-900">
                有什么可以帮你？
              </h2>
              <p className="mt-3 text-sm leading-7 text-slate-500">
                新建会话后，你可以连续提问，并在这里查看助手回复和工具调用过程。
              </p>
              <button
                className="mt-7 rounded-2xl bg-brand px-5 py-3 text-sm font-semibold text-white shadow-lg shadow-violet-200 transition hover:bg-violet-700"
                type="button"
              >
                新建会话
              </button>
            </div>
          </div>

          <footer className="border-t border-slate-100 bg-white px-4 py-4 sm:px-7">
            <div className="mx-auto flex max-w-4xl items-end gap-3 rounded-2xl border border-slate-200 bg-slate-50 p-2 shadow-sm">
              <textarea
                className="min-h-12 flex-1 resize-none bg-transparent px-3 py-3 text-sm outline-none placeholder:text-slate-400"
                disabled
                placeholder="请先新建会话"
                rows={1}
              />
              <button
                className="grid size-11 shrink-0 place-items-center rounded-xl bg-slate-200 text-slate-400"
                disabled
                type="button"
              >
                ↑
              </button>
            </div>
            <p className="mt-2 text-center text-[11px] text-slate-400">
              AI 生成内容可能存在误差，请核对重要信息
            </p>
          </footer>
        </section>
      </div>
    </main>
  );
}
