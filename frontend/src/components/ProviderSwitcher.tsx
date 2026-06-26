import type { LLMProviderName, LLMProviderStatus } from "../types/api";

interface ProviderSwitcherProps {
  status: LLMProviderStatus | null;
  isLoading: boolean;
  isSwitching: boolean;
  message: string | null;
  onSwitch: (provider: LLMProviderName) => void;
}

const PROVIDER_LABELS: Record<LLMProviderName, string> = {
  mock: "Mock 演示",
  openai: "真实接口",
};

function currentLabel(status: LLMProviderStatus | null) {
  if (!status) return "加载中";
  return status.provider === "openai" ? "DeepSeek / OpenAI-compatible" : "Mock 工具演示";
}

export function ProviderSwitcher({
  status,
  isLoading,
  isSwitching,
  message,
  onSwitch,
}: ProviderSwitcherProps) {
  const disabled = isLoading || isSwitching || !status;

  return (
    <div className="flex flex-col items-stretch gap-2 sm:items-end">
      <div className="rounded-2xl border border-line bg-[#fffaf1] p-1.5 shadow-sm">
        <div className="mb-1 flex items-center justify-between gap-3 px-2 text-[11px] font-semibold uppercase tracking-[0.12em] text-muted">
          <span>模型模式</span>
          <span className="normal-case tracking-normal text-brandDeep">{currentLabel(status)}</span>
        </div>
        <div className="flex flex-wrap items-center gap-1.5">
          {(["mock", "openai"] as LLMProviderName[]).map((provider) => {
            const isActive = status?.provider === provider;
            return (
              <button
                className={`rounded-xl px-3 py-1.5 text-xs font-semibold transition focus:outline-none focus:ring-4 focus:ring-brand/10 disabled:cursor-not-allowed disabled:opacity-60 ${
                  isActive
                    ? "bg-brand text-white shadow-sm"
                    : "bg-panel text-muted hover:text-ink"
                }`}
                disabled={disabled || isActive}
                key={provider}
                onClick={() => onSwitch(provider)}
                type="button"
              >
                {isSwitching && !isActive ? "切换中..." : PROVIDER_LABELS[provider]}
              </button>
            );
          })}
        </div>
      </div>

      {status && !status.openai_configured && (
        <p className="max-w-md rounded-xl border border-warning/20 bg-[#fff8e6] px-3 py-2 text-xs leading-5 text-warning">
          真实 API 未配置，请在 backend/.env 中配置 OPENAI_API_KEY、OPENAI_BASE_URL 和 OPENAI_MODEL。
        </p>
      )}
      {message && <p className="max-w-md text-xs leading-5 text-muted">{message}</p>}
    </div>
  );
}
