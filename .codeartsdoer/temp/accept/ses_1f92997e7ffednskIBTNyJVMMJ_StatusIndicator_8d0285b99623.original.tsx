interface StatusIndicatorProps {
  status: string | null | undefined;
}

export function StatusIndicator({ status }: StatusIndicatorProps) {
  const tone = getStatusTone(status);
  const label = getStatusLabel(status);
  return (
    <span className={`status-indicator status-indicator--${tone}`}>
      {tone === "success" ? "●" : tone === "danger" ? "✕" : tone === "warning" ? "▲" : "○"} {label}
    </span>
  );
}

type Tone = "success" | "warning" | "danger" | "neutral";

const labels: Record<string, string> = {
  active: "启用",
  approved: "已批准",
  attention_required: "需关注",
  available: "可用",
  disabled: "禁用",
  dry_run: "演练",
  failed: "失败",
  healthy: "健康",
  local: "本地",
  missing: "缺失",
  missing_files: "文件缺失",
  partial: "部分可用",
  passed: "通过",
  pending: "待处理",
  ready: "就绪",
  ready_for_real_integration: "可集成",
  rejected: "已拒绝",
  rolled_back: "已回滚",
  running: "运行中",
  stopped: "已停止",
  unavailable: "不可用",
  unconfigured: "未配置",
};

const warningSet = new Set(["attention_required", "dry_run", "missing", "missing_files", "partial", "pending", "unconfigured"]);
const dangerSet = new Set(["failed", "rejected", "unavailable"]);
const successSet = new Set(["active", "approved", "available", "healthy", "local", "passed", "ready", "ready_for_real_integration", "running"]);

function getStatusLabel(status: string | null | undefined): string {
  if (!status) return "未知";
  return labels[status] ?? status;
}

function getStatusTone(status: string | null | undefined): Tone {
  if (!status) return "neutral";
  if (dangerSet.has(status)) return "danger";
  if (warningSet.has(status)) return "warning";
  if (successSet.has(status)) return "success";
  return "neutral";
}

export { getStatusLabel, getStatusTone };
