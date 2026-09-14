/**
 * 调用本地 FastAPI。路径均以 /api 开头，开发时由 Vite 代理。
 */

async function parseError(response) {
  const payload = await response.json().catch(() => null);
  if (payload && typeof payload.detail === "string") {
    return payload.detail;
  }
  if (payload && payload.detail) {
    return JSON.stringify(payload.detail);
  }
  return `请求失败（${response.status}）`;
}

export async function request(path, options = {}) {
  const headers = { ...(options.headers || {}) };
  if (options.body && !headers["Content-Type"]) {
    headers["Content-Type"] = "application/json";
  }
  const response = await fetch(path, { ...options, headers });
  if (response.status === 204) {
    return null;
  }
  if (!response.ok) {
    throw new Error(await parseError(response));
  }
  return response.json();
}

export function listAccounts(q, groupId, accountType) {
  const params = new URLSearchParams();
  if (q && q.trim()) {
    params.set("q", q.trim());
  }
  if (groupId === "none") {
    params.set("ungrouped", "true");
  } else if (groupId) {
    params.set("group_id", String(groupId));
  }
  if (accountType) {
    params.set("account_type", String(accountType));
  }
  const query = params.toString() ? `?${params.toString()}` : "";
  return request(`/api/accounts${query}`);
}

/**
 * 读取系统账号分类目录，供导入与筛选下拉使用。
 */
export function listAccountTypes() {
  return request("/api/account-types");
}

export function getAccount(id) {
  return request(`/api/accounts/${id}`);
}

/**
 * 读取导入该账号时的四段凭证（含密码与刷新令牌）。
 */
export function getAccountImportInfo(id) {
  return request(`/api/accounts/${id}/import-info`);
}

export function previewImport(text, accountType) {
  return request("/api/accounts/import/preview", {
    method: "POST",
    body: JSON.stringify({ text, account_type: accountType }),
  });
}

export function applyImport(text, groupId, conflictMode, wipeAll, accountType) {
  return request("/api/accounts/import", {
    method: "POST",
    body: JSON.stringify({
      text,
      account_type: accountType,
      group_id: groupId == null ? null : groupId,
      conflict_mode: conflictMode,
      wipe_all: Boolean(wipeAll),
    }),
  });
}

export function deleteAccount(id) {
  return request(`/api/accounts/${id}`, { method: "DELETE" });
}

export function batchDeleteAccounts(ids) {
  return request("/api/accounts/batch/delete", {
    method: "POST",
    body: JSON.stringify({ ids }),
  });
}

export function batchMoveAccounts(ids, groupId) {
  return request("/api/accounts/batch/move", {
    method: "POST",
    body: JSON.stringify({
      ids,
      group_id: groupId == null ? null : groupId,
    }),
  });
}

export function listMessages(accountId, top = 50) {
  return request(`/api/accounts/${accountId}/messages?top=${top}`);
}

export function getMessage(accountId, messageId) {
  return request(`/api/accounts/${accountId}/messages/${encodeURIComponent(messageId)}`);
}

export function listGroups() {
  return request("/api/groups");
}

export function createGroup(name) {
  return request("/api/groups", {
    method: "POST",
    body: JSON.stringify({ name }),
  });
}

export function renameGroup(id, name) {
  return request(`/api/groups/${id}`, {
    method: "PATCH",
    body: JSON.stringify({ name }),
  });
}

export function deleteGroup(id) {
  return request(`/api/groups/${id}`, { method: "DELETE" });
}
