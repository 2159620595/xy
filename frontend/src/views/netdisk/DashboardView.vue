<template>
  <n-space vertical size="large">
    <n-grid :x-gap="12" :y-gap="12" :cols="4" item-responsive>
      <n-gi v-for="item in statistics" :key="item.title">
        <n-card size="small" :bordered="false">
          <n-statistic :label="item.title">
            <template #prefix>
              <n-icon :component="item.icon" :color="item.color" />
            </template>
            <span class="text-2xl font-bold">
              <n-number-animation :from="0" :to="item.value" :duration="800" />
            </span>
          </n-statistic>
          <div class="mt-2 text-xs">
            <n-text depth="3">{{ item.sub }}</n-text>
          </div>
        </n-card>
      </n-gi>
    </n-grid>

    <n-grid :x-gap="12" :cols="2">
      <n-gi>
        <n-card title="账号状态分布" :bordered="false">
          <div ref="pieRef" style="height: 260px" />
        </n-card>
      </n-gi>
      <n-gi>
        <n-card title="卡密状态分布" :bordered="false">
          <div ref="barRef" style="height: 260px" />
        </n-card>
      </n-gi>
    </n-grid>
  </n-space>
</template>

<script setup>
import { ref, onMounted, nextTick } from 'vue'
import {
  CloudServerOutlined,
  KeyOutlined,
  SafetyCertificateOutlined,
  AlertOutlined,
} from '@vicons/antd'
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
    icon: CloudServerOutlined,
    color: '#18a058',
  },
  { title: '失效账号', value: 0, sub: '需要重新登录的账号', icon: AlertOutlined, color: '#d03050' },
  {
    title: '未使用卡密',
    value: 0,
    sub: '可用于兑换的卡密数量',
    icon: KeyOutlined,
    color: '#2080f0',
  },
  {
    title: '已使用卡密',
    value: 0,
    sub: '已被用户兑换的卡密',
    icon: SafetyCertificateOutlined,
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
