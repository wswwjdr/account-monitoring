<script setup>
import { computed, onMounted, ref } from "vue";
import { useRouter } from "vue-router";
import {
  applyImport,
  batchDeleteAccounts,
  batchMoveAccounts,
  deleteAccount,
  getAccountImportInfo,
  listAccountTypes,
  listAccounts,
  listGroups,
  previewImport,
} from "../api";
import { formatDateTime, tokenErrorHint, tokenStatusLabel } from "../format";

const router = useRouter();
const accounts = ref([]);
const groups = ref([]);
const accountTypes = ref([]);
const keyword = ref("");
const filterGroupId = ref("");
const filterAccountType = ref("");
const importGroupId = ref("");
const importAccountType = ref("");
const selectedIds = ref([]);
const loading = ref(false);
const batchBusy = ref(false);
const message = ref("");
const messageKind = ref("");
const showImport = ref(false);
const importText = ref("");
const importBusy = ref(false);
const showConflict = ref(false);
const conflictEmails = ref([]);
const pendingText = ref("");
const showWipeConfirm = ref(false);
const showBatchDelete = ref(false);
const showBatchMove = ref(false);
const moveGroupId = ref("");
const errorTitle = ref("操作失败");
const errorDetail = ref("");
const showError = ref(false);
const showInfo = ref(false);
const infoBusy = ref(false);
const infoCopyHint = ref("");
const importInfo = ref(null);
const infoEmail = ref("");

const selectedCount = computed(() => selectedIds.value.length);
const allSelected = computed(
  () => accounts.value.length > 0 && selectedIds.value.length === accounts.value.length
);

/**
 * 读取分组列表。导入默认选未分组。
 */
async function loadGroups() {
  groups.value = await listGroups();
}

/**
 * 读取系统账号分类，供筛选与导入下拉使用。
 */
async function loadAccountTypes() {
  accountTypes.value = await listAccountTypes();
}

/**
 * 拉取账号列表并写入页面状态。
 */
async function loadAccounts() {
  loading.value = true;
  try {
    accounts.value = await listAccounts(keyword.value, filterGroupId.value, filterAccountType.value);
    selectedIds.value = [];
  } catch (error) {
    setMessage(error.message, "error");
  } finally {
    loading.value = false;
  }
}

function setMessage(text, kind) {
  if (kind === "error") {
    errorTitle.value = "操作失败";
    errorDetail.value = text;
    showError.value = true;
    return;
  }
  message.value = text;
  messageKind.value = kind;
}

function selectedImportGroupId() {
  if (!importGroupId.value) {
    return null;
  }
  return Number(importGroupId.value);
}

/**
 * 导入必须先选分类；未选则立即失败。
 */
function selectedImportType() {
  const code = importAccountType.value;
  if (!code) {
    throw new Error("请选择账号分类");
  }
  return code;
}

/**
 * 当前导入弹窗所选分类的说明文案。
 */
const importTypeSpec = computed(() => {
  return accountTypes.value.find((item) => item.code === importAccountType.value) || null;
});

function isSelected(id) {
  return selectedIds.value.includes(id);
}

function toggleRow(id) {
  if (isSelected(id)) {
    selectedIds.value = selectedIds.value.filter((item) => item !== id);
    return;
  }
  selectedIds.value = [...selectedIds.value, id];
}

function toggleAll() {
  if (allSelected.value) {
    selectedIds.value = [];
    return;
  }
  selectedIds.value = accounts.value.map((row) => row.id);
}

function selectedMoveGroupId() {
  if (!moveGroupId.value) {
    return null;
  }
  return Number(moveGroupId.value);
}

async function openImport() {
  importText.value = "";
  importAccountType.value = "";
  showConflict.value = false;
  showWipeConfirm.value = false;
  try {
    await loadGroups();
    await loadAccountTypes();
    showImport.value = true;
  } catch (error) {
    setMessage(error.message, "error");
  }
}

function closeImport() {
  showImport.value = false;
  showConflict.value = false;
  showWipeConfirm.value = false;
  pendingText.value = "";
}

/**
 * 先预览冲突：无重复则直接写入所选分组，有重复则弹出选择。
 */
async function submitImport() {
  const text = importText.value;
  importBusy.value = true;
  try {
    const accountType = selectedImportType();
    const groupId = selectedImportGroupId();
    const preview = await previewImport(text, accountType);
    if (preview.conflict_emails.length === 0) {
      const result = await applyImport(text, groupId, null, false, accountType);
      closeImport();
      setMessage(`已导入 ${result.inserted} 条`, "ok");
      await loadAccounts();
      return;
    }
    pendingText.value = text;
    conflictEmails.value = preview.conflict_emails;
    showConflict.value = true;
  } catch (error) {
    setMessage(error.message, "error");
  } finally {
    importBusy.value = false;
  }
}

/**
 * 对当前批次冲突邮箱统一追加或覆盖最新，并写入所选分组。
 */
async function resolveConflict(mode) {
  importBusy.value = true;
  try {
    const result = await applyImport(
      pendingText.value,
      selectedImportGroupId(),
      mode,
      false,
      selectedImportType()
    );
    closeImport();
    const parts = [`新增 ${result.inserted} 条`];
    if (result.updated) {
      parts.push(`覆盖 ${result.updated} 条`);
    }
    setMessage(parts.join("，"), "ok");
    await loadAccounts();
  } catch (error) {
    setMessage(error.message, "error");
  } finally {
    importBusy.value = false;
  }
}

async function wipeAndImport() {
  importBusy.value = true;
  try {
    const result = await applyImport(
      importText.value,
      selectedImportGroupId(),
      null,
      true,
      selectedImportType()
    );
    closeImport();
    setMessage(`已清空后导入 ${result.inserted} 条`, "ok");
    await loadAccounts();
  } catch (error) {
    setMessage(error.message, "error");
  } finally {
    importBusy.value = false;
  }
}

async function removeAccount(row) {
  const ok = window.confirm(`删除 ${row.email}（导入于 ${formatDateTime(row.imported_at)}）？`);
  if (!ok) {
    return;
  }
  try {
    await deleteAccount(row.id);
    setMessage("已删除", "ok");
    await loadAccounts();
  } catch (error) {
    setMessage(error.message, "error");
  }
}

function openBatchMove() {
  if (!selectedCount.value) {
    return;
  }
  moveGroupId.value = "";
  showBatchMove.value = true;
}

/**
 * 批量删除当前勾选的账号版本。
 */
async function confirmBatchDelete() {
  batchBusy.value = true;
  try {
    const result = await batchDeleteAccounts(selectedIds.value);
    showBatchDelete.value = false;
    setMessage(`已删除 ${result.count} 条`, "ok");
    await loadAccounts();
  } catch (error) {
    setMessage(error.message, "error");
  } finally {
    batchBusy.value = false;
  }
}

/**
 * 把勾选账号改到所选分组或未分组。
 */
async function confirmBatchMove() {
  batchBusy.value = true;
  try {
    const result = await batchMoveAccounts(selectedIds.value, selectedMoveGroupId());
    showBatchMove.value = false;
    setMessage(`已移动 ${result.count} 条`, "ok");
    await loadAccounts();
  } catch (error) {
    setMessage(error.message, "error");
  } finally {
    batchBusy.value = false;
  }
}

function openMail(row) {
  router.push({ name: "mail", params: { id: String(row.id) } });
}

/**
 * 打开导入信息弹窗，按需拉取四段凭证。
 */
async function openInfo(row) {
  infoEmail.value = row.email;
  importInfo.value = null;
  infoCopyHint.value = "";
  showInfo.value = true;
  infoBusy.value = true;
  try {
    importInfo.value = await getAccountImportInfo(row.id);
  } catch (error) {
    showInfo.value = false;
    setMessage(error.message, "error");
  } finally {
    infoBusy.value = false;
  }
}

function closeInfo() {
  showInfo.value = false;
  importInfo.value = null;
  infoCopyHint.value = "";
  infoEmail.value = "";
}

/**
 * 将导入整行复制到剪贴板。
 */
async function copyImportLine() {
  if (!importInfo.value) {
    return;
  }
  try {
    await navigator.clipboard.writeText(importInfo.value.import_line);
    infoCopyHint.value = "已复制整行";
  } catch (error) {
    infoCopyHint.value = error.message || "复制失败";
  }
}

onMounted(async () => {
  try {
    await loadGroups();
    await loadAccountTypes();
  } catch (error) {
    setMessage(error.message, "error");
  }
  await loadAccounts();
});
</script>

<template>
  <div class="page-head">
    <div>
      <h1>账号管理</h1>
      <p>导入须先选择账号分类。可勾选后批量删除或移至分组。导入不选分组则为未分组。</p>
    </div>
  </div>

  <div class="toolbar">
    <input
      v-model="keyword"
      class="search"
      type="search"
      placeholder="搜索邮箱地址"
      @keyup.enter="loadAccounts"
    />
    <select v-model="filterAccountType" class="search filter" @change="loadAccounts">
      <option value="">全部分类</option>
      <option v-for="item in accountTypes" :key="item.code" :value="item.code">
        {{ item.label }}
      </option>
    </select>
    <select v-model="filterGroupId" class="search filter" @change="loadAccounts">
      <option value="">全部</option>
      <option value="none">未分组</option>
      <option v-for="group in groups" :key="group.id" :value="String(group.id)">
        {{ group.name }}
      </option>
    </select>
    <button class="btn btn-ghost" type="button" @click="loadAccounts">查询</button>
    <button class="btn btn-ghost" type="button" :disabled="!selectedCount" @click="openBatchMove">
      移至分组
    </button>
    <button class="btn btn-danger" type="button" :disabled="!selectedCount" @click="showBatchDelete = true">
      批量删除
    </button>
    <button class="btn" type="button" @click="openImport">导入账号</button>
  </div>

  <p v-if="selectedCount" class="flash">已选 {{ selectedCount }} 条</p>
  <p v-if="message" class="flash" :class="messageKind">{{ message }}</p>

  <div class="panel">
    <p v-if="loading" class="empty">加载中…</p>
    <p v-else-if="accounts.length === 0" class="empty">还没有账号，先选择分类并导入。</p>
    <table v-else>
      <thead>
        <tr>
          <th class="check">
            <input type="checkbox" :checked="allSelected" @change="toggleAll" />
          </th>
          <th>#</th>
          <th>邮箱</th>
          <th>分类</th>
          <th>分组</th>
          <th>导入时间</th>
          <th>令牌状态</th>
          <th>操作</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="(row, index) in accounts" :key="row.id">
          <td class="check">
            <input type="checkbox" :checked="isSelected(row.id)" @change="toggleRow(row.id)" />
          </td>
          <td class="mono">{{ index + 1 }}</td>
          <td>{{ row.email }}</td>
          <td>{{ row.account_type_label }}</td>
          <td>{{ row.group_name }}</td>
          <td class="mono">{{ formatDateTime(row.imported_at) }}</td>
          <td>
            <span
              class="status"
              :class="[row.token_status, { 'has-tip': row.token_status === 'error' }]"
            >
              <i />
              {{ tokenStatusLabel(row.token_status) }}
              <span v-if="row.token_status === 'error'" class="tip">{{ tokenErrorHint(row) }}</span>
            </span>
          </td>
          <td>
            <div class="row-actions">
              <button class="linkish" type="button" @click="openInfo(row)">信息</button>
              <button
                v-if="row.supports_mail"
                class="linkish"
                type="button"
                @click="openMail(row)"
              >
                查看邮件
              </button>
              <button class="linkish danger" type="button" @click="removeAccount(row)">删除</button>
            </div>
          </td>
        </tr>
      </tbody>
    </table>
  </div>

  <div v-if="showInfo" class="overlay" @click.self="closeInfo">
    <div class="modal">
      <h2>导入信息</h2>
      <p class="hint">{{ infoEmail }} 导入时的四段凭证。</p>
      <p v-if="infoBusy" class="hint">加载中…</p>
      <template v-else-if="importInfo">
        <label class="field">
          <span>邮箱</span>
          <input class="search info-value" type="text" readonly :value="importInfo.email" />
        </label>
        <label class="field">
          <span>密码</span>
          <input class="search info-value" type="text" readonly :value="importInfo.password" />
        </label>
        <label class="field">
          <span>Client ID</span>
          <input class="search info-value" type="text" readonly :value="importInfo.client_id" />
        </label>
        <label class="field">
          <span>刷新令牌</span>
          <textarea class="info-token" readonly :value="importInfo.refresh_token" rows="7" />
        </label>
        <p v-if="infoCopyHint" class="hint">{{ infoCopyHint }}</p>
      </template>
      <div class="modal-actions">
        <button class="btn btn-ghost" type="button" @click="closeInfo">关闭</button>
        <button
          class="btn"
          type="button"
          :disabled="infoBusy || !importInfo"
          @click="copyImportLine"
        >
          复制整行
        </button>
      </div>
    </div>
  </div>

  <div v-if="showImport" class="overlay" @click.self="closeImport">
    <div class="modal">
      <h2>导入账号</h2>
      <label class="field">
        <span>账号分类</span>
        <select v-model="importAccountType" class="search">
          <option value="">请选择分类</option>
          <option v-for="item in accountTypes" :key="item.code" :value="item.code">
            {{ item.label }}
          </option>
        </select>
      </label>
      <p class="hint">
        {{ importTypeSpec ? importTypeSpec.import_hint : "请先选择账号分类，再粘贴对应格式的账号。" }}
      </p>
      <label class="field">
        <span>导入到分组</span>
        <select v-model="importGroupId" class="search">
          <option value="">未分组</option>
          <option v-for="group in groups" :key="group.id" :value="String(group.id)">
            {{ group.name }}
          </option>
        </select>
      </label>
      <textarea
        v-model="importText"
        :disabled="!importAccountType"
        :placeholder="
          importAccountType
            ? 'user@outlook.com----password----client-id----refresh-token'
            : '请先选择账号分类'
        "
      />
      <div class="modal-actions">
        <button class="btn btn-ghost" type="button" @click="closeImport">取消</button>
        <button
          class="btn btn-danger"
          type="button"
          :disabled="!importAccountType"
          @click="showWipeConfirm = true"
        >
          清空后导入
        </button>
        <button
          class="btn"
          type="button"
          :disabled="importBusy || !importAccountType"
          @click="submitImport"
        >
          导入
        </button>
      </div>
    </div>
  </div>

  <div v-if="showConflict" class="overlay">
    <div class="modal">
      <h2>发现 {{ conflictEmails.length }} 个重复邮箱</h2>
      <p class="hint">
        仅针对当前所选分类。追加会新增一条版本；覆盖只更新该邮箱最新一条，更早的版本保留。本次都会写入所选分组（含未分组）。
      </p>
      <ul class="conflict-list">
        <li v-for="email in conflictEmails" :key="email">{{ email }}</li>
      </ul>
      <div class="modal-actions">
        <button class="btn btn-ghost" type="button" @click="showConflict = false">返回</button>
        <button class="btn btn-ghost" type="button" :disabled="importBusy" @click="resolveConflict('replace_latest')">
          覆盖最新
        </button>
        <button class="btn" type="button" :disabled="importBusy" @click="resolveConflict('append')">
          追加新版本
        </button>
      </div>
    </div>
  </div>

  <div v-if="showWipeConfirm" class="overlay">
    <div class="modal">
      <h2>清空后导入</h2>
      <p class="hint">
        会删除当前所选分类下的全部账号，再写入本次文本。其他分类不受影响。分组本身保留。此操作不可撤销。
      </p>
      <div class="modal-actions">
        <button class="btn btn-ghost" type="button" @click="showWipeConfirm = false">取消</button>
        <button class="btn btn-danger" type="button" :disabled="importBusy" @click="wipeAndImport">确认清空并导入</button>
      </div>
    </div>
  </div>

  <div v-if="showBatchDelete" class="overlay">
    <div class="modal">
      <h2>批量删除</h2>
      <p class="hint">将删除已选的 {{ selectedCount }} 条账号，不可恢复。</p>
      <div class="modal-actions">
        <button class="btn btn-ghost" type="button" @click="showBatchDelete = false">取消</button>
        <button class="btn btn-danger" type="button" :disabled="batchBusy" @click="confirmBatchDelete">确认删除</button>
      </div>
    </div>
  </div>

  <div v-if="showBatchMove" class="overlay" @click.self="showBatchMove = false">
    <div class="modal">
      <h2>移至分组</h2>
      <p class="hint">将已选的 {{ selectedCount }} 条账号改到下方分组。</p>
      <label class="field">
        <span>目标分组</span>
        <select v-model="moveGroupId" class="search">
          <option value="">未分组</option>
          <option v-for="group in groups" :key="group.id" :value="String(group.id)">
            {{ group.name }}
          </option>
        </select>
      </label>
      <div class="modal-actions">
        <button class="btn btn-ghost" type="button" @click="showBatchMove = false">取消</button>
        <button class="btn" type="button" :disabled="batchBusy" @click="confirmBatchMove">确认移动</button>
      </div>
    </div>
  </div>

  <div v-if="showError" class="overlay">
    <div class="modal">
      <h2>{{ errorTitle }}</h2>
      <p class="hint error-text">{{ errorDetail }}</p>
      <div class="modal-actions">
        <button class="btn" type="button" @click="showError = false">确定</button>
      </div>
    </div>
  </div>
</template>
