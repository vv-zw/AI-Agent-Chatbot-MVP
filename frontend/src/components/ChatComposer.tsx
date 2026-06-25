import { FormEvent, KeyboardEvent } from "react";

interface ChatComposerProps {
  value: string;
  disabled: boolean;
  isSending: boolean;
  onChange: (value: string) => void;
  onEmptySubmit: () => void;
  onSubmit: (content: string) => void;
}

export function ChatComposer({
  value,
  disabled,
  isSending,
  onChange,
  onEmptySubmit,
  onSubmit,
}: ChatComposerProps) {
  function submit() {
    const content = value.trim();
    if (!content) {
      onEmptySubmit();
      return;
    }
    onSubmit(content);
  }

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    submit();
  }

  function handleKeyDown(event: KeyboardEvent<HTMLTextAreaElement>) {
    if (event.key === "Enter" && !event.shiftKey && !event.nativeEvent.isComposing) {
      event.preventDefault();
      if (!disabled && !isSending) submit();
    }
  }

  return (
    <footer className="border-t border-slate-100 bg-white px-4 py-4 sm:px-7">
      <form
        className="mx-auto flex max-w-4xl items-end gap-3 rounded-2xl border border-slate-200 bg-slate-50 p-2 shadow-sm transition-within focus-within:border-violet-300 focus-within:ring-4 focus-within:ring-violet-50"
        onSubmit={handleSubmit}
      >
        <textarea
          aria-label="消息内容"
          className="max-h-40 min-h-12 flex-1 resize-none bg-transparent px-3 py-3 text-sm leading-6 outline-none placeholder:text-slate-400 disabled:text-slate-400"
          disabled={disabled || isSending}
          onChange={(event) => onChange(event.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={disabled ? "请先新建会话" : "输入消息，Enter 发送，Shift + Enter 换行"}
          rows={1}
          value={value}
        />
        <button
          aria-label={isSending ? "正在发送" : "发送消息"}
          className="grid size-11 shrink-0 place-items-center rounded-xl bg-brand text-lg font-semibold text-white shadow-md shadow-violet-200 transition hover:bg-violet-700 disabled:bg-slate-200 disabled:text-slate-400 disabled:shadow-none"
          disabled={disabled || isSending}
          type="submit"
        >
          {isSending ? (
            <span className="size-4 animate-spin rounded-full border-2 border-white/40 border-t-white" />
          ) : (
            "↑"
          )}
        </button>
      </form>
      <p className="mt-2 text-center text-[11px] text-slate-400">
        AI 生成内容可能存在误差，请核对重要信息
      </p>
    </footer>
  );
}