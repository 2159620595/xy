<script setup lang="ts">
import DisclaimerContent from "@/components/common/DisclaimerContent.vue";
</script>

<template>
  <div class="app-page narrow-page">
    <section class="page-header">
      <div>
        <h1 class="page-title">免责声明</h1>
        <p class="page-description">使用系统前请完整阅读以下说明，继续使用即视为已理解并接受相关条款。</p>
      </div>
    </section>

    <el-card shadow="never">
      <DisclaimerContent />
    </el-card>
  </div>
</template>

<style scoped>
.narrow-page {
  max-width: 960px;
  margin: 0 auto;
}
</style>
