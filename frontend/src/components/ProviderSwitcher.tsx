import type { LLMProviderName, LLMProviderStatus } from "../types/api";

interface ProviderSwitcherProps {
  status: LLMProviderStatus | null;
  isLoading: boolean;
  isSwitching: boolean;
  message: string | null;
  onSwitch: (provider: LLMProviderName) => void;
}

const PROVIDER_LABELS: Record<LLMProviderName, string> = {
  mock: "演示模式",
  openai: "真实接口",
};

function currentLabel(status: LLMProviderStatus | null) {
  if (!status) return "加载中";
  return status.provider === "openai" ? "OpenAI-compatible" : "Demo";
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
      <div className="flex flex-wrap items-center gap-2 rounded-xl border border-line bg-panel p-1.5">
        <span className="px-2 text-xs font-medium text-muted">
          当前模式：{currentLabel(status)}
        </span>
        {(["mock", "openai"] as LLMProviderName[]).map((provider) => {
          const isActive = status?.provider === provider;
          return (
            <button
              className={`rounded-lg px-3 py-1.5 text-xs font-semibold transition focus:outline-none focus:ring-4 focus:ring-brand/10 disabled:cursor-not-allowed disabled:opacity-60 ${
                isActive
                  ? "bg-brand text-white shadow-sm"
                  : "bg-white text-muted hover:text-ink"
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

      {status && !status.openai_configured && (
        <p className="max-w-md text-xs leading-5 text-warning">
          真实 API 未配置，请在 backend/.env 中配置 OPENAI_API_KEY、OPENAI_BASE_URL 和 OPENAI_MODEL。
        </p>
      )}
      {message && <p className="max-w-md text-xs leading-5 text-muted">{message}</p>}
    </div>
  );
}
