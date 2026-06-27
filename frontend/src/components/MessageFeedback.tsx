import { useEffect, useState } from "react";

import type { FeedbackRating, MessageFeedback as Feedback } from "../types/api";

const MAX_REASON_LENGTH = 500;

interface MessageFeedbackProps {
  feedback?: Feedback | null;
  messageId: string;
  onSubmit: (rating: FeedbackRating, reason: string) => Promise<void>;
}

function ThumbIcon({ direction }: { direction: "up" | "down" }) {
  return (
    <svg
      aria-hidden="true"
      className={direction === "down" ? "size-3.5 rotate-180" : "size-3.5"}
      fill="none"
      viewBox="0 0 24 24"
    >
      <path
        d="M7.5 10.25 11.2 3.9a1.65 1.65 0 0 1 3.08 1.05v4.3h3.22a2 2 0 0 1 1.94 2.5l-1.65 6.35a2 2 0 0 1-1.94 1.5H7.5m0-9.35v9.35m0-9.35H4.9a1.4 1.4 0 0 0-1.4 1.4v6.55a1.4 1.4 0 0 0 1.4 1.4h2.6"
        stroke="currentColor"
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth="1.8"
      />
    </svg>
  );
}

export function MessageFeedback({ feedback, messageId, onSubmit }: MessageFeedbackProps) {
  const [isReasonOpen, setIsReasonOpen] = useState(false);
  const [reason, setReason] = useState(feedback?.reason ?? "");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!isReasonOpen) setReason(feedback?.reason ?? "");
  }, [feedback, isReasonOpen]);

  async function submit(rating: FeedbackRating, nextReason: string) {
    setIsSubmitting(true);
    setError(null);
    try {
      await onSubmit(rating, nextReason);
      setIsReasonOpen(false);
    } catch (caught) {
      setError(caught instanceof Error && caught.message
        ? caught.message
        : "反馈提交失败，请稍后重试。");
    } finally {
      setIsSubmitting(false);
    }
  }

  const statusText = feedback
    ? `${feedback.rating === "like" ? "已点赞" : "已点踩"} · 可修改`
    : "这个回答有帮助吗？";

  return (
    <div className="mt-1.5 pl-2 text-xs" aria-live="polite">
      <div className="flex min-h-7 flex-wrap items-center gap-1.5 text-muted">
        <span className={feedback ? "mr-1 text-brandDeep/70" : "mr-1 opacity-75"}>
          {statusText}
        </span>
        <button
          aria-label="点赞这条 AI 回复"
          aria-pressed={feedback?.rating === "like"}
          className={`grid size-7 place-items-center rounded-full border transition-colors focus:outline-none focus:ring-2 focus:ring-brand/30 disabled:cursor-wait disabled:opacity-50 ${
            feedback?.rating === "like"
              ? "border-success/25 bg-[#eefaf5] text-success"
              : "border-transparent text-muted hover:border-line hover:bg-panel hover:text-success"
          }`}
          disabled={isSubmitting}
          onClick={() => void submit("like", "")}
          title="有帮助"
          type="button"
        >
          <ThumbIcon direction="up" />
        </button>
        <button
          aria-expanded={isReasonOpen}
          aria-label="点踩这条 AI 回复并填写原因"
          aria-pressed={feedback?.rating === "dislike"}
          className={`grid size-7 place-items-center rounded-full border transition-colors focus:outline-none focus:ring-2 focus:ring-brand/30 disabled:cursor-wait disabled:opacity-50 ${
            feedback?.rating === "dislike"
              ? "border-danger/20 bg-[#fff1f1] text-danger"
              : "border-transparent text-muted hover:border-line hover:bg-panel hover:text-danger"
          }`}
          disabled={isSubmitting}
          onClick={() => {
            setError(null);
            setReason(feedback?.rating === "dislike" ? feedback.reason : "");
            setIsReasonOpen((current) => !current);
          }}
          title="需要改进"
          type="button"
        >
          <ThumbIcon direction="down" />
        </button>
      </div>

      {isReasonOpen && (
        <form
          className="mt-2 max-w-xl rounded-2xl border border-line bg-parchment p-3 shadow-sm"
          onSubmit={(event) => {
            event.preventDefault();
            void submit("dislike", reason);
          }}
        >
          <label className="font-medium text-ink" htmlFor={`feedback-reason-${messageId}`}>
            哪里需要改进？ <span className="font-normal text-muted">（可选）</span>
          </label>
          <textarea
            autoFocus
            className="mt-2 block w-full resize-y rounded-xl border border-line bg-panel px-3 py-2 text-sm leading-6 text-ink outline-none transition focus:border-brand/45 focus:ring-2 focus:ring-brand/10"
            id={`feedback-reason-${messageId}`}
            maxLength={MAX_REASON_LENGTH}
            onChange={(event) => setReason(event.target.value)}
            placeholder="例如：结论不准确、缺少依据或没有回答到重点"
            rows={2}
            value={reason}
          />
          <div className="mt-2 flex items-center justify-between gap-3">
            <span className="text-[10px] text-muted">{reason.length}/{MAX_REASON_LENGTH}</span>
            <div className="flex gap-2">
              <button className="rounded-lg px-3 py-1.5 text-muted hover:bg-panel" onClick={() => setIsReasonOpen(false)} type="button">
                取消
              </button>
              <button className="rounded-lg bg-brand px-3 py-1.5 font-medium text-white hover:bg-brandDeep disabled:cursor-wait disabled:opacity-60" disabled={isSubmitting} type="submit">
                {isSubmitting ? "提交中…" : feedback?.rating === "dislike" ? "更新反馈" : "提交反馈"}
              </button>
            </div>
          </div>
        </form>
      )}

      {error && <p className="mt-1.5 text-danger" role="alert">{error}</p>}
    </div>
  );
}
