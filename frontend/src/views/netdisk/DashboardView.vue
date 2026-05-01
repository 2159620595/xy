<template>
  <section class="netdisk-dashboard">
    <div class="netdisk-dashboard__metrics">
      <el-card
        v-for="item in statistics"
        :key="item.title"
        shadow="never"
        class="netdisk-dashboard__metric-card"
      >
        <div class="netdisk-dashboard__metric-top">
          <el-icon :style="{ color: item.color }">
            <component :is="item.icon" />
          </el-icon>
          <span class="netdisk-dashboard__metric-label">{{ item.title }}</span>
        </div>
        <div class="netdisk-dashboard__metric-value">{{ item.value }}</div>
        <div class="netdisk-dashboard__metric-help">{{ item.sub }}</div>
      </el-card>
    </div>

    <div class="netdisk-dashboard__charts">
      <el-card shadow="never">
        <template #header>账号状态分布</template>
        <div ref="pieRef" style="height: 260px" />
      </el-card>
      <el-card shadow="never">
        <template #header>卡密状态分布</template>
        <div ref="barRef" style="height: 260px" />
      </el-card>
    </div>
  </section>
</template>

<script setup>
import { ref, onMounted, nextTick } from 'vue'
import {
  Warning,
  Key,
  CircleCheck,
  User,
} from '@element-plus/icons-vue'
import { baiduApi } from '@/api/baidu'
import * as echarts from 'echarts/core'
import { PieChart, BarChart } from 'echarts/charts'
import { TooltipComponent, LegendComponent, GridComponent } from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'

echarts.use([PieChart, BarChart, TooltipComponent, LegendComponent, GridComponent, CanvasRenderer])

const pieRef = ref(null)
const barRef = ref(null)

const statistics = ref([
  {
    title: '在线账号',
    value: 0,
    sub: '状态正常的网盘账号',
    icon: User,
    color: '#18a058',
  },
  { title: '失效账号', value: 0, sub: '需要重新登录的账号', icon: Warning, color: '#d03050' },
  {
    title: '未使用卡密',
    value: 0,
    sub: '可用于兑换的卡密数量',
    icon: Key,
    color: '#2080f0',
  },
  {
    title: '已使用卡密',
    value: 0,
    sub: '已被用户兑换的卡密',
    icon: CircleCheck,
    color: '#f0a020',
  },
])

onMounted(async () => {
  await loadData()
})

async function loadData() {
  try {
    const [accRes, keyRes] = await Promise.all([baiduApi.getAccounts(), baiduApi.getCdKeys()])

    const accounts = accRes.data || []
    const keys = keyRes.data || []

    const onlineCount = accounts.filter((a) => a.status === 1).length
    const offlineCount = accounts.filter((a) => a.status !== 1).length
    const unusedKeys = keys.filter((k) => k.status === 0).length
    const usedKeys = keys.filter((k) => k.status === 1).length
    const voidedKeys = keys.filter((k) => k.status === 2).length

    statistics.value[0].value = onlineCount
    statistics.value[1].value = offlineCount
    statistics.value[2].value = unusedKeys
    statistics.value[3].value = usedKeys

    await nextTick()
    renderPie(onlineCount, offlineCount)
    renderBar(unusedKeys, usedKeys, voidedKeys)
  } catch (e) {
    console.error('Dashboard load error:', e)
  }
}

function renderPie(online, offline) {
  if (!pieRef.value) return
  const chart = echarts.init(pieRef.value)
  chart.setOption({
    tooltip: { trigger: 'item', formatter: '{b}: {c} ({d}%)' },
    legend: {
      bottom: 0,
      itemWidth: 10,
      itemHeight: 10,
      textStyle: { fontSize: 12 },
    },
    series: [
      {
        type: 'pie',
        radius: ['40%', '68%'],
        center: ['50%', '44%'],
        itemStyle: { borderRadius: 6, borderWidth: 2, borderColor: '#fff' },
        label: { show: false },
        data: [
          { value: online, name: '正常账号', itemStyle: { color: '#18a058' } },
          { value: offline, name: '失效账号', itemStyle: { color: '#e0e0e0' } },
        ],
      },
    ],
  })
}

function renderBar(unused, used, voided) {
  if (!barRef.value) return
  const chart = echarts.init(barRef.value)
  chart.setOption({
    tooltip: { trigger: 'axis' },
    grid: { left: 16, right: 16, bottom: 24, top: 16, containLabel: true },
    xAxis: {
      type: 'category',
      data: ['未使用', '已使用', '已作废'],
      axisLine: { show: false },
      axisTick: { show: false },
    },
    yAxis: {
      type: 'value',
      splitLine: { lineStyle: { color: '#f0f0f0' } },
    },
    series: [
      {
        type: 'bar',
        barWidth: '40%',
        itemStyle: { borderRadius: [6, 6, 0, 0] },
        data: [
          { value: unused, itemStyle: { color: '#2080f0' } },
          { value: used, itemStyle: { color: '#18a058' } },
          { value: voided, itemStyle: { color: '#e0e0e0' } },
        ],
      },
    ],
  })
}
</script>

<style scoped>
.netdisk-dashboard {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.netdisk-dashboard__metrics {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 12px;
}

.netdisk-dashboard__metric-card :deep(.el-card__body) {
  min-height: 118px;
}

.netdisk-dashboard__metric-top {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 10px;
  color: #475569;
}

.netdisk-dashboard__metric-label {
  font-size: 14px;
  font-weight: 600;
}

.netdisk-dashboard__metric-value {
  font-size: 28px;
  line-height: 1.2;
  font-weight: 700;
  color: #0f172a;
}

.netdisk-dashboard__metric-help {
  margin-top: 8px;
  color: #64748b;
  font-size: 12px;
}

.netdisk-dashboard__charts {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
}

@media (max-width: 1080px) {
  .netdisk-dashboard__metrics {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .netdisk-dashboard__charts {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 640px) {
  .netdisk-dashboard__metrics {
    grid-template-columns: 1fr;
  }
}
</style>
