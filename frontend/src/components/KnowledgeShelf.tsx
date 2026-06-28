import { useRef } from "react";

import type { KnowledgeFile } from "../types/api";

interface KnowledgeShelfProps {
  disabled: boolean;
  error: string | null;
  files: KnowledgeFile[];
  isLoading: boolean;
  isUploading: boolean;
  onUpload: (file: File) => void;
}

function formatSize(size: number) {
  return size < 1024 ? `${size} B` : `${Math.ceil(size / 1024)} KB`;
}

export function KnowledgeShelf({
  disabled,
  error,
  files,
  isLoading,
  isUploading,
  onUpload,
}: KnowledgeShelfProps) {
  const inputRef = useRef<HTMLInputElement>(null);

  return (
    <section className="shrink-0 border-b border-line bg-[#f7f1ff]/75 px-3 py-2 sm:px-7 sm:py-3" aria-label="当前会话知识库">
      <div className="mx-auto grid max-w-4xl grid-cols-[minmax(0,1fr)_auto] items-center gap-2 sm:flex sm:flex-wrap sm:gap-3">
        <div className="flex min-w-0 items-center gap-2">
          <span className="grid size-7 shrink-0 place-items-center rounded-lg border border-brand/20 bg-panel text-xs text-brandDeep sm:size-8 sm:rounded-xl sm:text-sm">⌘</span>
          <div>
            <p className="text-xs font-semibold text-ink">资料夹</p>
            <p className="hidden text-[11px] text-muted sm:block">仅当前卷轴可检索 · TXT / MD / CSV / JSON</p>
          </div>
        </div>

        <div className="order-3 col-span-2 flex min-w-0 w-full gap-2 overflow-x-auto py-0.5 sm:order-none sm:w-auto sm:flex-1 sm:py-1">
          {isLoading && <span className="animate-pulse text-xs text-muted">正在展开资料夹…</span>}
          {!isLoading && files.length === 0 && <span className="text-xs text-muted">还没有资料，上传后即可在对话里引用。</span>}
          {files.map((file) => (
            <span className="group flex shrink-0 items-center gap-2 rounded-full border border-brand/15 bg-panel px-3 py-1.5 shadow-sm" key={file.id} title={`${file.chunk_count} 个片段`}>
              <span className="size-1.5 rounded-full bg-brand" />
              <span className="max-w-40 truncate text-xs font-medium text-ink">{file.filename}</span>
              <span className="text-[10px] text-muted">{formatSize(file.size)}</span>
            </span>
          ))}
        </div>

        <input
          accept=".txt,.md,.csv,.json,text/plain,text/markdown,text/csv,application/json"
          className="sr-only"
          disabled={disabled || isUploading}
          onChange={(event) => {
            const selected = event.target.files?.[0];
            if (selected) onUpload(selected);
            event.target.value = "";
          }}
          ref={inputRef}
          type="file"
        />
        <button
          className="shrink-0 rounded-xl border border-brand/20 bg-panel px-2.5 py-2 text-xs font-semibold text-brandDeep transition hover:border-brand/40 hover:bg-white focus:outline-none focus:ring-4 focus:ring-brand/10 disabled:opacity-50"
          disabled={disabled || isUploading}
          onClick={() => inputRef.current?.click()}
          type="button"
        >
          {isUploading ? "正在收录…" : "+ 上传资料"}
        </button>
      </div>
      {error && <p className="mx-auto mt-2 max-w-4xl text-xs text-danger" role="alert">{error}</p>}
    </section>
  );
}
