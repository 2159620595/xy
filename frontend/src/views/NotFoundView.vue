<script setup lang="ts">
import { useRouter } from 'vue-router'

const router = useRouter()
</script>

<template>
  <div class="not-found">
    <el-card class="not-found-card" shadow="never">
      <div class="code">404</div>
      <h1>页面不存在</h1>
      <p>当前地址还没有迁移到 Vue 端，或输入的路径不正确。</p>
      <div class="actions">
        <el-button type="primary" @click="router.push('/dashboard')">返回仪表盘</el-button>
        <el-button @click="router.push('/items')">去商品管理</el-button>
      </div>
    </el-card>
  </div>
</template>

<style scoped>
.not-found {
  min-height: 100vh;
  display: grid;
  place-items: center;
  padding: 24px;
}

.not-found-card {
  width: min(100%, 520px);
  text-align: center;
  border-radius: 24px;
}

.code {
  font-size: 72px;
  font-weight: 800;
  color: #2563eb;
  line-height: 1;
}

h1 {
  margin: 16px 0 12px;
  font-size: 32px;
}

p {
  color: #64748b;
  line-height: 1.7;
}

.actions {
  display: flex;
  justify-content: center;
  gap: 12px;
  margin-top: 24px;
  flex-wrap: wrap;
}
</style>
