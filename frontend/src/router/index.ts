import { createRouter, createWebHistory } from "vue-router";
import AppLayout from "@/components/layout/AppLayout.vue";
import LoginView from "@/views/auth/LoginView.vue";
import RegisterView from "@/views/auth/RegisterView.vue";
import DashboardView from "@/views/dashboard/DashboardView.vue";
import AccountsView from "@/views/accounts/AccountsView.vue";
import CardsView from "@/views/cards/CardsView.vue";
import KeywordsView from "@/views/keywords/KeywordsView.vue";
import DeliveryView from "@/views/delivery/DeliveryView.vue";
import ItemsView from "@/views/items/ItemsView.vue";
import ItemRepliesView from "@/views/item-replies/ItemRepliesView.vue";
import NotificationChannelsView from "@/views/notifications/NotificationChannelsView.vue";
import MessageNotificationsView from "@/views/notifications/MessageNotificationsView.vue";
import OrdersView from "@/views/orders/OrdersView.vue";
import SettingsView from "@/views/settings/SettingsView.vue";
import UsersView from "@/views/admin/UsersView.vue";
import LogsView from "@/views/admin/LogsView.vue";
import RiskLogsView from "@/views/admin/RiskLogsView.vue";
import DataManagementView from "@/views/admin/DataManagementView.vue";
import AboutView from "@/views/about/AboutView.vue";
import DisclaimerView from "@/views/disclaimer/DisclaimerView.vue";
import NotFoundView from "@/views/NotFoundView.vue";
import NetdiskDashboardView from "@/views/netdisk/DashboardView.vue";
import NetdiskAccountsView from "@/views/netdisk/AccountsView.vue";
import NetdiskCdKeysView from "@/views/netdisk/CdKeysView.vue";
import NetdiskDeviceLogsView from "@/views/netdisk/DeviceLogsView.vue";
import NetdiskLoginLogsView from "@/views/netdisk/LoginLogsView.vue";
import NetdiskRedeemView from "@/views/netdisk/RedeemView.vue";
import JudianDashboardView from "@/views/judian/DashboardView.vue";
import JudianAccountsView from "@/views/judian/AccountsView.vue";
import JudianCdKeysView from "@/views/judian/CdKeysView.vue";
import JudianRedeemView from "@/views/judian/RedeemView.vue";
import { useAuthStore } from "@/stores/auth";
import { initializeAuth } from "@/utils/auth-bootstrap";

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: "/",
      component: AppLayout,
      children: [
        {
          path: "",
          redirect: "/dashboard",
        },
        {
          path: "dashboard",
          name: "dashboard",
          component: DashboardView,
          meta: {
            title: "仪表盘",
            description: "查看 Vue 管理台当前迁移状态与核心入口。",
          },
        },
        {
          path: "accounts",
          name: "accounts",
          component: AccountsView,
          meta: {
            title: "账号管理",
            description: "管理闲鱼账号、登录方式、默认回复和 AI 回复设置。",
          },
        },
        {
          path: "keywords",
          name: "keywords",
          component: KeywordsView,
          meta: {
            title: "关键词管理",
            description: "管理文本关键词、图片关键词以及导入导出。",
          },
        },
        {
          path: "cards",
          name: "cards",
          component: CardsView,
          meta: {
            title: "卡券管理",
            description: "管理自动发货卡券，覆盖文本、API、批量和图片类型。",
          },
        },
        {
          path: "delivery",
          name: "delivery",
          component: DeliveryView,
          meta: {
            title: "自动发货",
            description: "把商品与卡券绑定成自动发货规则，并查看发货明细。",
          },
        },
        {
          path: "items",
          name: "items",
          component: ItemsView,
          meta: {
            title: "商品管理",
            description:
              "筛选账号、查看商品状态，并逐步补齐编辑与批量操作能力。",
          },
        },
        {
          path: "item-replies",
          name: "item-replies",
          component: ItemRepliesView,
          meta: {
            title: "自动回复",
            description: "查看、添加和编辑商品级自动回复配置。",
          },
        },
        {
          path: "notification-channels",
          name: "notification-channels",
          component: NotificationChannelsView,
          meta: {
            title: "通知渠道",
            description: "维护钉钉、飞书、邮件、Webhook 等通知发送渠道。",
          },
        },
        {
          path: "message-notifications",
          name: "message-notifications",
          component: MessageNotificationsView,
          meta: {
            title: "消息通知",
            description: "把账号与通知渠道绑定，控制消息通知是否启用。",
          },
        },
        {
          path: "orders",
          name: "orders",
          component: OrdersView,
          meta: {
            title: "订单管理",
            description: "查看订单列表，按账号主动抓取真实订单并处理详情与删除。",
          },
        },
        {
          path: "settings",
          name: "settings",
          component: SettingsView,
          meta: {
            title: "系统设置",
            description: "维护系统参数、邮件配置、AI 配置以及备份恢复能力。",
          },
        },
        {
          path: "about",
          name: "about",
          component: AboutView,
          meta: {
            title: "关于系统",
            description: "查看系统简介、版本信息、交流群二维码和相关链接。",
          },
        },
        {
          path: "disclaimer",
          name: "disclaimer",
          component: DisclaimerView,
          meta: {
            title: "免责声明",
            description: "查看系统使用须知、风险说明和隐私保护承诺。",
          },
        },
        {
          path: "netdisk/dashboard",
          name: "netdisk-dashboard",
          component: NetdiskDashboardView,
          meta: {
            title: "网盘控制台",
            description: "查看百度网盘账号池、卡密库存与扫码管理总览。",
          },
        },
        {
          path: "netdisk/accounts",
          name: "netdisk-accounts",
          component: NetdiskAccountsView,
          meta: {
            title: "网盘账号池",
            description: "管理百度网盘账号、Cookie、二维码登录和设备信息。",
          },
        },
        {
          path: "netdisk/cdkeys",
          name: "netdisk-cdkeys",
          component: NetdiskCdKeysView,
          meta: {
            title: "网盘卡密",
            description: "生成、作废和清理百度网盘发放卡密。",
          },
        },
        {
          path: "netdisk/device-logs",
          name: "netdisk-device-logs",
          component: NetdiskDeviceLogsView,
          meta: {
            title: "网盘设备记录",
            description: "查看当前在线设备、历史设备记录并执行踢设备。",
          },
        },
        {
          path: "netdisk/login-logs",
          name: "netdisk-login-logs",
          component: NetdiskLoginLogsView,
          meta: {
            title: "网盘登录审计",
            description: "筛选管理员登录日志、风险等级和活跃锁定状态。",
          },
        },
        {
          path: "judian/dashboard",
          name: "judian-dashboard",
          component: JudianDashboardView,
          meta: {
            title: "聚店控制台",
            description: "查看聚店账号、钻石余额、卡密状态和最近活动。",
          },
        },
        {
          path: "judian/accounts",
          name: "judian-accounts",
          component: JudianAccountsView,
          meta: {
            title: "聚店账户",
            description: "登录、重登和启停聚店账户，并同步远端会话。",
          },
        },
        {
          path: "judian/cdkeys",
          name: "judian-cdkeys",
          component: JudianCdKeysView,
          meta: {
            title: "聚店卡密",
            description: "管理聚店卡密、导入网盘卡密和发货模板内容。",
          },
        },
        {
          path: "admin/users",
          name: "admin-users",
          component: UsersView,
          meta: {
            title: "用户管理",
            description: "查看全站用户列表，并执行删除等管理员操作。",
            requiresAdmin: true,
          },
        },
        {
          path: "admin/logs",
          name: "admin-logs",
          component: LogsView,
          meta: {
            title: "系统日志",
            description: "查看系统运行日志，支持过滤、导出与清空。",
            requiresAdmin: true,
          },
        },
        {
          path: "admin/risk-logs",
          name: "admin-risk-logs",
          component: RiskLogsView,
          meta: {
            title: "风控日志",
            description: "查看风控事件和处理结果，支持按账号筛选。",
            requiresAdmin: true,
          },
        },
        {
          path: "admin/data",
          name: "admin-data",
          component: DataManagementView,
          meta: {
            title: "数据管理",
            description: "浏览表数据，执行清空、缓存刷新和数据库恢复。",
            requiresAdmin: true,
          },
        },
      ],
    },
    {
      path: "/register",
      name: "register",
      component: RegisterView,
      meta: { public: true },
    },
    {
      path: "/login",
      name: "login",
      component: LoginView,
      meta: { public: true },
    },
    {
      path: "/netdisk/redeem",
      name: "netdisk-redeem",
      component: NetdiskRedeemView,
      meta: { public: true },
    },
    {
      path: "/judian/redeem",
      name: "judian-redeem",
      component: JudianRedeemView,
      meta: { public: true },
    },
    {
      path: "/:pathMatch(.*)*",
      name: "not-found",
      component: NotFoundView,
      meta: { public: true },
    },
  ],
});

router.beforeEach(async (to) => {
  const authStore = useAuthStore();

  if (!authStore.initialized) {
    await initializeAuth();
  }

  if (to.meta.public) {
    if (authStore.isAuthenticated && (to.path === "/login" || to.path === "/register")) {
      return "/dashboard";
    }
    return true;
  }

  if (!authStore.isAuthenticated) {
    return "/login";
  }

  if (to.meta.requiresAdmin && !authStore.user?.is_admin) {
    return "/dashboard";
  }

  return true;
});

export default router;
