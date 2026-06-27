import type { ChatbotRole } from "../types/api";

interface RoleSwitcherProps {
  roles: ChatbotRole[];
  selectedRoleId: string;
  disabled: boolean;
  isLoading: boolean;
  isSwitching: boolean;
  onChange: (roleId: string) => void;
}

export function RoleSwitcher({
  roles,
  selectedRoleId,
  disabled,
  isLoading,
  isSwitching,
  onChange,
}: RoleSwitcherProps) {
  const selectedRole = roles.find((role) => role.role_id === selectedRoleId) ?? null;

  return (
    <div
      className="min-w-52 rounded-2xl border bg-white p-2 shadow-sm"
      style={{ borderColor: selectedRole?.color ? `${selectedRole.color}55` : undefined }}
    >
      <label className="block" htmlFor="assistant-role">
        <span className="flex items-center justify-between gap-3 px-1 text-[11px] font-semibold uppercase tracking-[0.12em] text-muted">
          <span>助手角色</span>
          <span className="normal-case tracking-normal text-ink">
            {isLoading ? "加载中" : selectedRole?.name ?? "未选择"}
          </span>
        </span>
        <span className="mt-1.5 flex items-center gap-2">
          <span
            className="grid size-8 shrink-0 place-items-center rounded-xl border text-[11px] font-bold"
            style={{
              backgroundColor: selectedRole?.color ? `${selectedRole.color}12` : "#f8f5ee",
              borderColor: selectedRole?.color ? `${selectedRole.color}45` : undefined,
              color: selectedRole?.color ?? undefined,
            }}
          >
            {selectedRole?.icon ?? "TA"}
          </span>
          <select
            className="min-w-0 flex-1 rounded-xl border border-line bg-panel px-2.5 py-2 text-xs font-semibold text-ink outline-none focus:ring-4 focus:ring-brand/10 disabled:opacity-60"
            disabled={disabled || isLoading || isSwitching || roles.length === 0}
            id="assistant-role"
            onChange={(event) => onChange(event.target.value)}
            value={selectedRoleId}
          >
            {roles.map((role) => (
              <option key={role.role_id} value={role.role_id}>{role.name}</option>
            ))}
          </select>
        </span>
      </label>
      <p className="mt-1.5 max-w-64 px-1 text-[11px] leading-4 text-muted">
        {isSwitching ? "正在保存角色..." : selectedRole?.description ?? "选择本次对话的助手侧重点"}
      </p>
    </div>
  );
}
