<script setup lang="ts">
import { computed, onMounted, reactive, ref } from "vue";
import {
  Delete,
  Edit,
  Plus,
  RefreshRight,
  Switch,
  View,
} from "@element-plus/icons-vue";
import { ElMessage, ElMessageBox } from "element-plus";
import { getAccountDetails } from "@/api/accounts";
import { getCards } from "@/api/cards";
import {
  addDeliveryRule,
  deleteDeliveryRule,
  getDeliveryRuleRecords,
  getDeliveryRules,
  updateDeliveryRule,
} from "@/api/delivery";
import { getItems } from "@/api/items";
import type {
  AccountDetail,
  CardData,
  DeliveryRecord,
  DeliveryRule,
  Item,
} from "@/types";

const loading = ref(true);
const saving = ref(false);
const recordsLoading = ref(false);
const rules = ref<DeliveryRule[]>([]);
const accounts = ref<AccountDetail[]>([]);
const cards = ref<CardData[]>([]);
const items = ref<Item[]>([]);
const dialogVisible = ref(false);
const recordsDialogVisible = ref(false);
const editingRule = ref<DeliveryRule | null>(null);
const currentRecordRule = ref<DeliveryRule | null>(null);
const records = ref<DeliveryRecord[]>([]);

const form = reactive({
  itemId: "",
  cardId: "",
  description: "",
  enabled: true,
});

const accountMap = computed(() => {
  return new Map(accounts.value.map((item) => [item.id, item]));
});

const itemOptions = computed(() =>
  items.value.map((item) => ({
    label: `${item.item_title || item.title || item.item_id} (${item.item_id})`,
    value: item.item_id,
  })),
);

const cardOptions = computed(() =>
  cards.value.map((card) => ({
    label: card.is_multi_spec
      ? `${card.name} [${card.spec_name || "-"}: ${card.spec_value || "-"}]`
      : card.name,
    value: String(card.id),
  })),
);

const getItemTitle = (item?: Item | null, rule?: DeliveryRule | null) => {
  return (
    item?.item_title ||
    item?.title ||
    rule?.item_title ||
    rule?.keyword ||
    rule?.item_id ||
    "-"
  );
};

const getItemPrice = (item?: Item | null, rule?: DeliveryRule | null) => {
  return item?.item_price || item?.price || rule?.item_price || "-";
};

const getItemImage = (item?: Item | null, rule?: DeliveryRule | null) => {
  return (
    item?.primary_image_url ||
    item?.images?.find((image) => image.is_primary)?.image_url ||
    item?.images?.[0]?.thumbnail_url ||
    item?.images?.[0]?.image_url ||
    item?.item_detail_parsed?.pic_info?.picUrl ||
    item?.item_detail_parsed?.pic_info?.url ||
    rule?.primary_image_url ||
    ""
  );
};

const getItemAccountText = (item?: Item | null) => {
  if (!item?.cookie_id) return "-";
  const account = accountMap.value.get(item.cookie_id);
  return account?.xianyu_nickname
    ? `${item.cookie_id}（${account.xianyu_nickname}）`
    : item.cookie_id;
};

const resetForm = () => {
  form.itemId = "";
  form.cardId = "";
  form.description = "";
  form.enabled = true;
  editingRule.value = null;
};

const loadPage = async () => {
  loading.value = true;
  try {
    const [accountsResult, cardsResult, itemsResult, rulesResult] =
      await Promise.all([
        getAccountDetails(),
        getCards(),
        getItems(),
        getDeliveryRules(),
      ]);
    accounts.value = accountsResult;
    cards.value = cardsResult.data || [];
    items.value = itemsResult.data || [];
    rules.value = rulesResult.data || [];
  } catch {
    ElMessage.error("加载自动发货页面失败");
  } finally {
    loading.value = false;
  }
};

const openAddDialog = () => {
  resetForm();
  dialogVisible.value = true;
};

const openEditDialog = (rule: DeliveryRule) => {
  resetForm();
  editingRule.value = rule;
  form.itemId = rule.item_id || "";
  form.cardId = String(rule.card_id);
  form.description = rule.description || "";
  form.enabled = rule.enabled;
  dialogVisible.value = true;
};

const closeDialog = () => {
  dialogVisible.value = false;
  resetForm();
};

const handleSubmit = async () => {
  if (!form.itemId) {
    ElMessage.warning("请选择绑定商品");
    return;
  }
  if (!form.cardId) {
    ElMessage.warning("请选择关联卡券");
    return;
  }

  saving.value = true;
  try {
    const selectedItem = items.value.find((item) => item.item_id === form.itemId);
    const selectedTitle = getItemTitle(selectedItem, editingRule.value);
    const payload = {
      item_id: form.itemId,
      item_title: selectedTitle,
      keyword: selectedTitle,
      card_id: Number(form.cardId),
      delivery_count: 1,
      description: form.description.trim() || undefined,
      enabled: form.enabled,
    };

    if (editingRule.value) {
      await updateDeliveryRule(String(editingRule.value.id), payload);
      ElMessage.success("发货规则更新成功");
    } else {
      await addDeliveryRule(payload);
      ElMessage.success("发货规则创建成功");
    }

    closeDialog();
    await loadPage();
  } catch {
    ElMessage.error("保存发货规则失败");
  } finally {
    saving.value = false;
  }
};

const toggleRule = async (rule: DeliveryRule) => {
  try {
    await updateDeliveryRule(String(rule.id), { enabled: !rule.enabled });
    ElMessage.success(rule.enabled ? "规则已禁用" : "规则已启用");
    await loadPage();
  } catch {
    ElMessage.error("规则状态更新失败");
  }
};

const removeRule = async (rule: DeliveryRule) => {
  try {
    await ElMessageBox.confirm(
      `确定删除规则“${rule.item_title || rule.keyword || rule.item_id}”吗？`,
      "删除确认",
      {
        type: "warning",
        confirmButtonText: "删除",
        cancelButtonText: "取消",
      },
    );
    await deleteDeliveryRule(String(rule.id));
    ElMessage.success("发货规则已删除");
    await loadPage();
  } catch {
    // ignore cancel
  }
};

const openRecordsDialog = async (rule: DeliveryRule) => {
  currentRecordRule.value = rule;
  recordsDialogVisible.value = true;
  recordsLoading.value = true;
  records.value = [];
  try {
    const result = await getDeliveryRuleRecords(String(rule.id));
    records.value = result.data || [];
  } catch {
    ElMessage.error("加载发货明细失败");
  } finally {
    recordsLoading.value = false;
  }
};

const closeRecordsDialog = () => {
  recordsDialogVisible.value = false;
  currentRecordRule.value = null;
  records.value = [];
};

onMounted(loadPage);
</script>

<template>
  <div class="app-page">
    <section class="page-header">
      <div>
        <h1 class="page-title">自动发货</h1>
        <p class="page-description">
          把商品和卡券绑定成自动发货规则，并查看历史自动发货明细。
        </p>
      </div>
      <div class="page-actions">
        <el-button :icon="RefreshRight" @click="loadPage">刷新列表</el-button>
        <el-button type="primary" :icon="Plus" @click="openAddDialog">
          添加规则
        </el-button>
      </div>
    </section>

    <el-card shadow="never">
      <div class="table-toolbar">
        <div class="toolbar-meta">当前共 {{ rules.length }} 条发货规则</div>
        <el-tag type="primary" effect="plain">已接入规则新增、编辑、启停、删除和明细查看</el-tag>
      </div>

      <el-table v-loading="loading" :data="rules" style="width: 100%; margin-top: 16px">
        <el-table-column label="绑定商品" min-width="280">
          <template #default="{ row }">
            <div class="item-cell">
              <div class="thumb-wrap">
                <el-image
                  v-if="getItemImage(items.find((item) => item.item_id === row.item_id), row)"
                  :src="getItemImage(items.find((item) => item.item_id === row.item_id), row)"
                  fit="cover"
                  class="item-thumb"
                  :preview-src-list="[getItemImage(items.find((item) => item.item_id === row.item_id), row)]"
                  preview-teleported
                />
                <div v-else class="thumb-empty">无图</div>
              </div>
              <div class="cell-title">
                <div class="cell-title-main">
                  {{ getItemTitle(items.find((item) => item.item_id === row.item_id), row) }}
                </div>
                <div class="cell-title-sub">
                  {{ row.item_id || "-" }} / {{ getItemPrice(items.find((item) => item.item_id === row.item_id), row) }}
                </div>
                <div class="cell-title-sub">
                  {{ getItemAccountText(items.find((item) => item.item_id === row.item_id)) }}
                </div>
              </div>
            </div>
          </template>
        </el-table-column>

        <el-table-column label="关联卡券" min-width="180">
          <template #default="{ row }">
            <div class="cell-title">
              <div class="cell-title-main">{{ row.card_name || `卡券 #${row.card_id}` }}</div>
              <div v-if="row.is_multi_spec" class="cell-title-sub">
                {{ row.spec_name || "-" }}: {{ row.spec_value || "-" }}
              </div>
            </div>
          </template>
        </el-table-column>

        <el-table-column label="已发次数" width="100">
          <template #default="{ row }">
            {{ row.delivery_times || 0 }}
          </template>
        </el-table-column>

        <el-table-column label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="row.enabled ? 'success' : 'info'" effect="plain">
              {{ row.enabled ? "启用" : "禁用" }}
            </el-tag>
          </template>
        </el-table-column>

        <el-table-column label="备注" min-width="180">
          <template #default="{ row }">
            <span class="text-muted">{{ row.description || "-" }}</span>
          </template>
        </el-table-column>

        <el-table-column label="操作" min-width="260" fixed="right">
          <template #default="{ row }">
            <div class="row-actions">
              <el-button link type="primary" :icon="View" @click="openRecordsDialog(row)">
                明细
              </el-button>
              <el-button link type="primary" :icon="Edit" @click="openEditDialog(row)">
                编辑
              </el-button>
              <el-button
                link
                :type="row.enabled ? 'warning' : 'success'"
                :icon="Switch"
                @click="toggleRule(row)"
              >
                {{ row.enabled ? "禁用" : "启用" }}
              </el-button>
              <el-button link type="danger" :icon="Delete" @click="removeRule(row)">
                删除
              </el-button>
            </div>
          </template>
        </el-table-column>

        <template #empty>
          <el-empty description="暂无自动发货规则" />
        </template>
      </el-table>
    </el-card>

    <el-dialog
      v-model="dialogVisible"
      :title="editingRule ? '编辑发货规则' : '添加发货规则'"
      width="720px"
      destroy-on-close
      @closed="closeDialog"
    >
      <el-form label-position="top">
        <el-form-item label="绑定商品">
          <el-select
            v-model="form.itemId"
            filterable
            placeholder="请选择商品"
            style="width: 100%"
          >
            <el-option
              v-for="item in itemOptions"
              :key="item.value"
              :label="item.label"
              :value="item.value"
            />
          </el-select>
        </el-form-item>

        <el-form-item label="关联卡券">
          <el-select
            v-model="form.cardId"
            filterable
            placeholder="请选择卡券"
            style="width: 100%"
          >
            <el-option
              v-for="item in cardOptions"
              :key="item.value"
              :label="item.label"
              :value="item.value"
            />
          </el-select>
        </el-form-item>

        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="启用状态">
              <el-switch v-model="form.enabled" />
            </el-form-item>
          </el-col>
        </el-row>

        <el-form-item label="规则描述">
          <el-input
            v-model="form.description"
            type="textarea"
            :rows="3"
            placeholder="可选，填写规则说明"
          />
        </el-form-item>
      </el-form>

      <template #footer>
        <el-button @click="closeDialog">取消</el-button>
        <el-button type="primary" :loading="saving" @click="handleSubmit">保存</el-button>
      </template>
    </el-dialog>

    <el-dialog
      v-model="recordsDialogVisible"
      title="自动发货明细"
      width="820px"
      destroy-on-close
      @closed="closeRecordsDialog"
    >
      <div class="dialog-subtitle">
        {{
          currentRecordRule?.item_title ||
          currentRecordRule?.keyword ||
          currentRecordRule?.item_id ||
          "-"
        }}
      </div>

      <el-table v-loading="recordsLoading" :data="records" style="width: 100%; margin-top: 12px">
        <el-table-column label="订单号" min-width="160">
          <template #default="{ row }">
            <span class="mono">{{ row.order_id || "-" }}</span>
          </template>
        </el-table-column>
        <el-table-column label="买家" min-width="120">
          <template #default="{ row }">
            {{ row.buyer_id || "-" }}
          </template>
        </el-table-column>
        <el-table-column label="卡券" min-width="160">
          <template #default="{ row }">
            {{ row.card_name || row.card_id || "-" }}
          </template>
        </el-table-column>
        <el-table-column label="发送条数" width="100">
          <template #default="{ row }">
            {{ row.sent_count || 0 }}
          </template>
        </el-table-column>
        <el-table-column label="时间" min-width="160">
          <template #default="{ row }">
            {{ row.created_at || "-" }}
          </template>
        </el-table-column>
        <el-table-column label="发货内容" min-width="240">
          <template #default="{ row }">
            <div class="record-content">{{ row.delivery_content || "-" }}</div>
          </template>
        </el-table-column>

        <template #empty>
          <el-empty description="暂无自动发货明细" />
        </template>
      </el-table>

      <template #footer>
        <el-button @click="closeRecordsDialog">关闭</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.row-actions {
  display: flex;
  align-items: center;
  gap: 4px;
  flex-wrap: wrap;
}

.item-cell {
  display: flex;
  align-items: center;
  gap: 12px;
}

.thumb-wrap {
  width: 52px;
  height: 52px;
  flex-shrink: 0;
}

.item-thumb {
  width: 52px;
  height: 52px;
  border-radius: 12px;
}

.thumb-empty {
  width: 52px;
  height: 52px;
  display: grid;
  place-items: center;
  border-radius: 12px;
  background: #f1f5f9;
  color: #94a3b8;
  font-size: 12px;
}

.dialog-subtitle {
  color: #64748b;
  font-size: 14px;
}

.record-content {
  white-space: pre-wrap;
  word-break: break-all;
  color: #475569;
}
</style>
