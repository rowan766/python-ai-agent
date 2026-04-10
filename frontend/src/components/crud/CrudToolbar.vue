<template>
  <div class="crud-toolbar-shell">
    <div v-if="$slots.search" class="crud-search-bar">
      <slot name="search" />
    </div>
    <div v-if="$slots.actions" class="crud-action-toolbar">
      <slot name="actions" />
    </div>
  </div>
</template>

<style scoped>
.crud-toolbar-shell {
  display: flex;
  flex-direction: column;
  gap: 14px;
  margin-bottom: 18px;
}

.crud-search-bar :deep(.el-form) {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
}

.crud-search-bar :deep(.el-form-item) {
  margin-bottom: 0;
}

.crud-action-toolbar {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}
</style>
