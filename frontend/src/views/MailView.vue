<script setup>
import { computed, onMounted, ref, watch } from "vue";
import { useRoute } from "vue-router";
import { getAccount, getMessage, listMessages } from "../api";
import { formatDateTime, tokenErrorHint, tokenStatusLabel } from "../format";

const route = useRoute();
const accountId = computed(() => Number(route.params.id));
const account = ref(null);
const messages = ref([]);
const selectedId = ref("");
const detail = ref(null);
const loadingList = ref(false);
const loadingDetail = ref(false);
const errorDetail = ref("");
const showError = ref(false);

/**
 * 加载账号摘要与收件箱列表。
 */
async function loadInbox() {
  loadingList.value = true;
  errorDetail.value = "";
  showError.value = false;
  detail.value = null;
  selectedId.value = "";
  try {
    account.value = await getAccount(accountId.value);
    messages.value = await listMessages(accountId.value);
    account.value = await getAccount(accountId.value);
  } catch (err) {
    messages.value = [];
    errorDetail.value = err.message;
    showError.value = true;
    try {
      account.value = await getAccount(accountId.value);
    } catch {
      return;
    }
  } finally {
    loadingList.value = false;
  }
}

/**
 * 读取单封邮件正文。
 */
async function openMessage(message) {
  selectedId.value = message.id;
  loadingDetail.value = true;
  try {
    detail.value = await getMessage(accountId.value, message.id);
  } catch (err) {
    detail.value = null;
    errorDetail.value = err.message;
    showError.value = true;
  } finally {
    loadingDetail.value = false;
  }
}

const frameBody = computed(() => {
  if (!detail.value || detail.value.body_type !== "html") {
    return "";
  }
  return detail.value.body_content;
});

watch(accountId, loadInbox);
onMounted(loadInbox);
</script>

<template>
  <router-link class="back" to="/">← 返回账号管理</router-link>
  <div class="page-head">
    <div>
      <h1>{{ account ? account.email : "邮件" }}</h1>
      <p v-if="account">
        导入时间 {{ formatDateTime(account.imported_at) }} · {{ account.group_name }} · 令牌
        <span
          class="status"
          :class="[account.token_status, { 'has-tip': account.token_status === 'error' }]"
        >
          {{ tokenStatusLabel(account.token_status) }}
          <span v-if="account.token_status === 'error'" class="tip">{{ tokenErrorHint(account) }}</span>
        </span>
      </p>
    </div>
  </div>

  <div class="panel mail-layout">
    <aside class="mail-list">
      <p v-if="loadingList" class="empty">正在拉取收件箱…</p>
      <p v-else-if="messages.length === 0" class="empty">没有邮件</p>
      <button
        v-for="item in messages"
        :key="item.id"
        class="mail-item"
        :class="{ active: item.id === selectedId }"
        type="button"
        @click="openMessage(item)"
      >
        <strong>{{ item.subject || "（无主题）" }}</strong>
        <span>{{ item.from_name || item.from_address || "未知发件人" }}</span>
        <span> · {{ formatDateTime(item.received_at) }}</span>
      </button>
    </aside>
    <section class="mail-detail">
      <p v-if="loadingDetail" class="empty">正在打开邮件…</p>
      <template v-else-if="detail">
        <h2>{{ detail.subject || "（无主题）" }}</h2>
        <p class="mail-meta">
          {{ detail.from_name }} &lt;{{ detail.from_address }}&gt; ·
          {{ formatDateTime(detail.received_at) }}
        </p>
        <iframe
          v-if="detail.body_type === 'html'"
          class="mail-frame"
          sandbox=""
          referrerpolicy="no-referrer"
          :srcdoc="frameBody"
        />
        <div v-else class="mail-body-text">{{ detail.body_content || "（无正文）" }}</div>
      </template>
      <p v-else class="empty">选择左侧一封邮件查看正文</p>
    </section>
  </div>

  <div v-if="showError" class="overlay">
    <div class="modal">
      <h2>读取邮件失败</h2>
      <p class="hint error-text">{{ errorDetail }}</p>
      <div class="modal-actions">
        <button class="btn" type="button" @click="showError = false">确定</button>
      </div>
    </div>
  </div>
</template>
