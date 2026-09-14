/**
 * 把后端 ISO 时间格式化成本地中文日期时间。
 */
export function formatDateTime(value) {
  if (!value) {
    return "—";
  }
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return String(value);
  }
  return date.toLocaleString("zh-CN", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    hour12: false,
  });
}

/**
 * 令牌状态转中文标签。
 */
export function tokenStatusLabel(status) {
  if (status === "normal") {
    return "正常";
  }
  if (status === "error") {
    return "异常";
  }
  return "未知";
}

/**
 * 异常令牌的悬停说明。
 */
export function tokenErrorHint(row) {
  if (!row || row.token_status !== "error") {
    return "";
  }
  if (row.token_error) {
    return row.token_error;
  }
  return "令牌刷新失败，无法读取邮件。请检查 Client ID 与刷新令牌后重新导入。";
}
