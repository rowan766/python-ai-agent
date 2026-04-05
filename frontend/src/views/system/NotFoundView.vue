<template>
  <div class="not-found">
    <el-result
      icon="warning"
      title="页面不存在"
      sub-title="这个地址还没有接入到企业级 RAG 工作台里。"
    >
      <template #extra>
        <router-link to="/workspace">
          <el-button type="primary">回到工作台</el-button>
        </router-link>
      </template>
    </el-result>
  </div>
</template>

<style scoped>
.not-found {
  display: grid;
  min-height: 100vh;
  place-items: center;
}
</style>
