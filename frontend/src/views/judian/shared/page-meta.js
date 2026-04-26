export const JUDIAN_SECTION_META = {
  dashboard: {
    title: '聚点联盟控制台',
    description: '查看聚点账号登录情况、卡密库存状态和最近的真实业务操作记录。',
  },
  accounts: {
    title: '聚点账户登录',
    description: '管理聚点邮箱账号登录、资料同步和账号池状态，数据直接来自真实后端。',
  },
  cdkeys: {
    title: '聚点卡密页面',
    description: '维护聚点卡密库存、批量生成真实卡密，并提供可复制的兑换链接。',
  },
}


export function getJudianSectionMeta(section) {
  return JUDIAN_SECTION_META[section] || JUDIAN_SECTION_META.dashboard
}
