import { FormEvent, KeyboardEvent } from "react";

interface ChatComposerProps {
  value: string;
  disabled: boolean;
  isSending: boolean;
  maxLength: number;
  onChange: (value: string) => void;
  onEmptySubmit: () => void;
  onSubmit: (content: string) => void;
  onTooLongSubmit: () => void;
}

export function ChatComposer({
  value,
  disabled,
  isSending,
  maxLength,
  onChange,
  onEmptySubmit,
  onSubmit,
  onTooLongSubmit,
}: ChatComposerProps) {
  function submit() {
    const content = value.trim();
    if (!content) {
      onEmptySubmit();
      return;
    }
    if (content.length > maxLength) {
      onTooLongSubmit();
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
    <footer className="border-t border-line bg-panel/95 px-4 py-4 sm:px-7">
      <form
        className="mx-auto flex max-w-4xl items-end gap-3 rounded-xl border border-line bg-white p-2 shadow-soft transition focus-within:border-brand/35 focus-within:ring-4 focus-within:ring-brand/10"
        onSubmit={handleSubmit}
      >
        <textarea
          aria-label="消息内容"
          className="max-h-40 min-h-12 flex-1 resize-none bg-transparent px-3 py-3 text-sm leading-6 text-ink outline-none placeholder:text-muted/70 disabled:text-muted"
          disabled={disabled || isSending}
          onChange={(event) => onChange(event.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={disabled ? "请先新建会话" : "输入任务、问题或要验证的信息"}
          rows={1}
          value={value}
        />
        <button
          aria-label={isSending ? "正在发送" : "发送消息"}
          className="grid size-11 shrink-0 place-items-center rounded-lg bg-brand text-lg font-semibold text-white shadow-sm transition hover:bg-[#264d43] focus:outline-none focus:ring-4 focus:ring-brand/15 disabled:bg-[#dedbd1] disabled:text-muted disabled:shadow-none"
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
      <div className="mx-auto mt-2 flex max-w-4xl items-center justify-between gap-4 text-[11px] text-muted">
        <p>结果用于辅助判断，请核对关键事实与数字</p>
        <p className={value.length > maxLength ? "font-semibold text-danger" : ""}>
          {value.length}/{maxLength}
        </p>
      </div>
    </footer>
  );
}
