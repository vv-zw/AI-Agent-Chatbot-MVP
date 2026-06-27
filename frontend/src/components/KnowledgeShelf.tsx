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
    <section className="border-b border-line bg-[#f7f1ff]/75 px-4 py-3 sm:px-7" aria-label="当前会话知识库">
      <div className="mx-auto flex max-w-4xl flex-wrap items-center gap-3">
        <div className="flex min-w-0 items-center gap-2">
          <span className="grid size-8 shrink-0 place-items-center rounded-xl border border-brand/20 bg-panel text-sm text-brandDeep">⌘</span>
          <div>
            <p className="text-xs font-semibold text-ink">资料夹</p>
            <p className="text-[11px] text-muted">仅当前卷轴可检索 · TXT / MD / CSV / JSON</p>
          </div>
        </div>

        <div className="flex min-w-0 flex-1 gap-2 overflow-x-auto py-1">
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
          className="shrink-0 rounded-xl border border-brand/20 bg-panel px-3 py-2 text-xs font-semibold text-brandDeep transition hover:border-brand/40 hover:bg-white focus:outline-none focus:ring-4 focus:ring-brand/10 disabled:opacity-50"
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
