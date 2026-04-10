<template>
  <div class="crud-table-shell">
    <el-table
      v-bind="$attrs"
      :data="data"
      :class="['crud-table', tableClass]"
      v-loading="loading"
      @selection-change="$emit('selection-change', $event)"
    >
      <slot />
    </el-table>

    <div v-if="showPagination" class="crud-pagination">
      <div v-if="showSummary" class="crud-table-summary">
        <slot name="pagination-left">
          <el-icon v-if="summaryIcon"><component :is="summaryIcon" /></el-icon>
          <span>{{ summaryText }}</span>
        </slot>
      </div>

      <el-pagination
        :current-page="currentPage"
        :page-size="pageSize"
        :page-sizes="pageSizes"
        :layout="paginationLayout"
        :total="total"
        @update:current-page="handleUpdateCurrentPage"
        @update:page-size="handleUpdatePageSize"
        @size-change="handleSizeChange"
        @current-change="handleCurrentChange"
      />
    </div>
  </div>
</template>

<script setup>
defineOptions({ inheritAttrs: false })

const props = defineProps({
  data: {
    type: Array,
    default: () => []
  },
  loading: {
    type: Boolean,
    default: false
  },
  tableClass: {
    type: [String, Array, Object],
    default: ''
  },
  showPagination: {
    type: Boolean,
    default: true
  },
  showSummary: {
    type: Boolean,
    default: false
  },
  summaryText: {
    type: String,
    default: ''
  },
  summaryIcon: {
    type: [Object, Function],
    default: null
  },
  currentPage: {
    type: Number,
    default: 1
  },
  pageSize: {
    type: Number,
    default: 10
  },
  total: {
    type: Number,
    default: 0
  },
  pageSizes: {
    type: Array,
    default: () => [10, 20, 50, 100]
  },
  paginationLayout: {
    type: String,
    default: 'sizes, prev, pager, next, jumper'
  }
})

const emit = defineEmits([
  'selection-change',
  'update:currentPage',
  'update:pageSize',
  'page-size-change',
  'page-current-change'
])

const handleUpdateCurrentPage = (value) => {
  emit('update:currentPage', value)
}

const handleUpdatePageSize = (value) => {
  emit('update:pageSize', value)
}

const handleSizeChange = (value) => {
  emit('page-size-change', value)
}

const handleCurrentChange = (value) => {
  emit('page-current-change', value)
}
</script>

<style scoped>
.crud-table {
  border: 1px solid #edf2f7;
  border-radius: 16px;
  overflow: hidden;
}

.crud-table :deep(.el-table__header-wrapper th) {
  background: #f4f5f7;
  color: #4b5563;
  font-weight: 700;
  border-bottom-color: #e5e7eb;
}

.crud-table :deep(.el-table__row td) {
  border-bottom-color: #edf2f7;
}

.crud-table :deep(.el-table__row:hover td) {
  background: #f7fbff !important;
}

.crud-pagination {
  margin-top: 20px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.crud-table-summary {
  display: flex;
  align-items: center;
  gap: 8px;
  color: #7b8ba0;
}

@media (max-width: 960px) {
  .crud-pagination {
    flex-direction: column;
    align-items: flex-start;
  }
}
</style>
