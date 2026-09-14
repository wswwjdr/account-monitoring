<template>
  <div class="shell">
    <aside class="brand-rail">
      <span class="brand-mark">账号管家</span>
      <p class="brand-copy">本机管理账号。当前支持 Outlook 四段凭证，用 Graph 查看邮件。</p>
      <nav class="rail-nav">
        <router-link to="/" :class="{ active: route.name !== 'groups' }">账号管理</router-link>
        <router-link to="/groups" :class="{ active: route.name === 'groups' }">分组管理</router-link>
      </nav>
    </aside>
    <main class="stage">
      <router-view />
    </main>
  </div>
</template>

<script setup>
import { useRoute } from "vue-router";

const route = useRoute();
</script>
