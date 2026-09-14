import { createRouter, createWebHistory } from "vue-router";
import AccountsView from "./views/AccountsView.vue";
import GroupsView from "./views/GroupsView.vue";
import MailView from "./views/MailView.vue";

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: "/", name: "accounts", component: AccountsView },
    { path: "/groups", name: "groups", component: GroupsView },
    { path: "/accounts/:id/mail", name: "mail", component: MailView },
  ],
});

export default router;
