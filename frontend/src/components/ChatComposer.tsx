import { FormEvent, KeyboardEvent } from "react";

interface ChatComposerProps {
  value: string;
  disabled: boolean;
  isSending: boolean;
  useStreaming: boolean;
  onStreamingChange: (enabled: boolean) => void;
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
  useStreaming,
  onStreamingChange,
  maxLength,
  onChange,
  onEmptySubmit,
  onSubmit,
  onTooLongSubmit,
}: ChatComposerProps) {
  const isBlank = value.trim().length === 0;

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
        className="mx-auto flex max-w-4xl items-end gap-3 rounded-3xl border border-line bg-[#fffaf1] p-2 shadow-scroll transition focus-within:border-brand/35 focus-within:ring-4 focus-within:ring-brand/10"
        onSubmit={handleSubmit}
      >
        <div className="hidden self-stretch border-r border-line px-3 py-3 text-xs font-semibold text-accent sm:block">
          指令
        </div>
        <textarea
          aria-label="消息内容"
          className="max-h-40 min-h-12 flex-1 resize-none bg-transparent px-3 py-3 text-sm leading-6 text-ink outline-none placeholder:text-muted/70 disabled:text-muted"
          disabled={disabled || isSending}
          onChange={(event) => onChange(event.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={disabled ? "请先开启一条会话" : "输入问题或指令，Agent 将为你处理..."}
          rows={1}
          value={value}
        />
        <button
          aria-label={isSending ? "正在发送" : "发送消息"}
          className="grid size-11 shrink-0 place-items-center rounded-2xl bg-brand text-base font-semibold text-white shadow-sm transition hover:bg-brandDeep focus:outline-none focus:ring-4 focus:ring-brand/15 disabled:bg-[#ded4c1] disabled:text-muted disabled:shadow-none"
          disabled={disabled || isSending || isBlank}
          type="submit"
        >
          {isSending ? (
            <span className="size-4 animate-spin rounded-full border-2 border-white/40 border-t-white" />
          ) : (
            "✦"
          )}
        </button>
      </form>
      <div className="mx-auto mt-2 flex max-w-4xl items-center justify-between gap-4 text-[11px] text-muted">
        <label className="flex cursor-pointer items-center gap-2" title="关闭后使用原有普通发送接口">
          <input
            checked={useStreaming}
            disabled={isSending}
            onChange={(event) => onStreamingChange(event.target.checked)}
            type="checkbox"
          />
          <span>{useStreaming ? "流式输出已开启" : "普通发送 fallback"}</span>
        </label>
        <p className={value.length > maxLength ? "font-semibold text-danger" : ""}>
          {value.length}/{maxLength}
        </p>
      </div>
    </footer>
  );
}
