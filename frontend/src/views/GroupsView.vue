<script setup>
import { onMounted, ref } from "vue";
import { createGroup, deleteGroup, listGroups, renameGroup } from "../api";

const groups = ref([]);
const newName = ref("");
const loading = ref(false);
const busy = ref(false);
const message = ref("");
const messageKind = ref("");

function setMessage(text, kind) {
  message.value = text;
  messageKind.value = kind;
}

/**
 * 刷新分组列表。
 */
async function loadGroups() {
  loading.value = true;
  try {
    groups.value = await listGroups();
  } catch (error) {
    setMessage(error.message, "error");
  } finally {
    loading.value = false;
  }
}

async function addGroup() {
  busy.value = true;
  try {
    await createGroup(newName.value);
    newName.value = "";
    setMessage("已创建分组", "ok");
    await loadGroups();
  } catch (error) {
    setMessage(error.message, "error");
  } finally {
    busy.value = false;
  }
}

async function editGroup(group) {
  const name = window.prompt("新的分组名称", group.name);
  if (name === null) {
    return;
  }
  busy.value = true;
  try {
    await renameGroup(group.id, name);
    setMessage("已重命名", "ok");
    await loadGroups();
  } catch (error) {
    setMessage(error.message, "error");
  } finally {
    busy.value = false;
  }
}

async function removeGroup(group) {
  const ok = window.confirm(`删除分组「${group.name}」？`);
  if (!ok) {
    return;
  }
  busy.value = true;
  try {
    await deleteGroup(group.id);
    setMessage("已删除分组", "ok");
    await loadGroups();
  } catch (error) {
    setMessage(error.message, "error");
  } finally {
    busy.value = false;
  }
}

onMounted(loadGroups);
</script>

<template>
  <div class="page-head">
    <div>
      <h1>分组管理</h1>
      <p>导入账号时可选择分组；不选则为未分组。删除分组后，其中账号变为未分组。</p>
    </div>
  </div>

  <div class="toolbar">
    <input v-model="newName" class="search" type="text" placeholder="新分组名称" @keyup.enter="addGroup" />
    <button class="btn" type="button" :disabled="busy" @click="addGroup">新建分组</button>
  </div>

  <p v-if="message" class="flash" :class="messageKind">{{ message }}</p>

  <div class="panel">
    <p v-if="loading" class="empty">加载中…</p>
    <p v-else-if="groups.length === 0" class="empty">还没有分组。账号可以先保持未分组。</p>
    <table v-else>
      <thead>
        <tr>
          <th>名称</th>
          <th>账号数</th>
          <th>操作</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="group in groups" :key="group.id">
          <td>{{ group.name }}</td>
          <td class="mono">{{ group.account_count }}</td>
          <td>
            <div class="row-actions">
              <button class="linkish" type="button" :disabled="busy" @click="editGroup(group)">重命名</button>
              <button class="linkish danger" type="button" :disabled="busy" @click="removeGroup(group)">删除</button>
            </div>
          </td>
        </tr>
      </tbody>
    </table>
  </div>
</template>
