<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import {
  fetchKnowledgeBases,
  fetchKnowledgeDocuments,
  fetchMyKnowledgeBaseShareRequests,
  fetchPendingKnowledgeBaseShareRequests,
} from '@/api/modules/knowledge'
import {
  fetchMyDepartmentJoinRequests,
  fetchPendingDepartmentJoinRequests,
} from '@/api/modules/organization'
import { useAuthStore } from '@/stores/auth'
import { formatMembershipLabel, getPreferredMembership } from '@/utils/organization'

const authStore = useAuthStore()
const router = useRouter()

const loading = ref(false)
const knowledgeBaseCount = ref(0)
const documentCount = ref(0)
const pendingJoinCount = ref(0)
const pendingShareCount = ref(0)
const myJoinCount = ref(0)
const myShareCount = ref(0)

const memberships = computed(() => authStore.user?.memberships ?? [])
const currentMembership = computed(() => getPreferredMembership(memberships.value))
const pendingApprovalCount = computed(() => pendingJoinCount.value + pendingShareCount.value)
const myRequestCount = computed(() => myJoinCount.value + myShareCount.value)

const quickActions = [
  { label: '进入知识空间', path: '/knowledge-bases' },
  { label: '上传文档', path: '/documents/upload' },
  { label: '知识检索', path: '/knowledge/search' },
  { label: '审批中心', path: '/approvals' },
]

const pendingRows = computed(() => [
  { label: '组织申请待办', count: pendingJoinCount.value, path: '/approvals' },
  { label: '共享申请待办', count: pendingShareCount.value, path: '/approvals' },
])

const initiatedRows = computed(() => [
  { label: '我发起的组织申请', count: myJoinCount.value, path: '/approvals' },
  { label: '我发起的共享申请', count: myShareCount.value, path: '/approvals' },
])

async function loadWorkspace() {
  loading.value = true
  try {
    const [
      knowledgeBaseResult,
      documentResult,
      pendingJoinResult,
      pendingShareResult,
      myJoinResult,
      myShareResult,
    ] = await Promise.allSettled([
      fetchKnowledgeBases(),
      fetchKnowledgeDocuments(),
      fetchPendingDepartmentJoinRequests(),
      fetchPendingKnowledgeBaseShareRequests(),
      fetchMyDepartmentJoinRequests(),
      fetchMyKnowledgeBaseShareRequests(),
    ])

    knowledgeBaseCount.value =
      knowledgeBaseResult.status === 'fulfilled' ? knowledgeBaseResult.value.count : 0
    documentCount.value = documentResult.status === 'fulfilled' ? documentResult.value.count : 0
    pendingJoinCount.value =
      pendingJoinResult.status === 'fulfilled' ? pendingJoinResult.value.count : 0
    pendingShareCount.value =
      pendingShareResult.status === 'fulfilled' ? pendingShareResult.value.count : 0
    myJoinCount.value = myJoinResult.status === 'fulfilled' ? myJoinResult.value.count : 0
    myShareCount.value = myShareResult.status === 'fulfilled' ? myShareResult.value.count : 0
  } finally {
    loading.value = false
  }
}

function openPath(path: string) {
  void router.push(path)
}

onMounted(() => {
  void loadWorkspace()
})
</script>

<template>
  <div class="page">
    <section class="page-toolbar">
      <div class="page-toolbar__title">
        <h2>工作台</h2>
        <span>当前部门：{{ currentMembership?.department_name || '未设置' }}</span>
      </div>
      <div class="page-toolbar__actions">
        <el-button
          v-for="action in quickActions"
          :key="action.path"
          :type="action.path === '/knowledge-bases' ? 'primary' : 'default'"
          @click="openPath(action.path)"
        >
          {{ action.label }}
        </el-button>
      </div>
    </section>

    <section class="summary-grid">
      <el-card class="summary-card" shadow="never">
        <span class="summary-card__label">当前部门</span>
        <strong class="summary-card__value">{{ currentMembership?.department_name || '--' }}</strong>
      </el-card>
      <el-card class="summary-card" shadow="never">
        <span class="summary-card__label">可访问知识空间</span>
        <strong class="summary-card__value">{{ knowledgeBaseCount }}</strong>
      </el-card>
      <el-card class="summary-card" shadow="never">
        <span class="summary-card__label">可访问文档</span>
        <strong class="summary-card__value">{{ documentCount }}</strong>
      </el-card>
      <el-card class="summary-card" shadow="never">
        <span class="summary-card__label">待处理审批</span>
        <strong class="summary-card__value">{{ pendingApprovalCount }}</strong>
      </el-card>
    </section>

    <section class="split-grid">
      <el-card class="table-card" shadow="never">
        <template #header>
          <div class="table-toolbar">
            <strong>我的部门</strong>
          </div>
        </template>
        <el-table v-loading="loading" :data="memberships" stripe empty-text="暂无部门归属">
          <el-table-column prop="department_name" label="部门" min-width="180" />
          <el-table-column label="关系" min-width="140">
            <template #default="{ row }">
              {{ formatMembershipLabel(row) }}
            </template>
          </el-table-column>
          <el-table-column label="主部门" width="100">
            <template #default="{ row }">
              {{ row.is_primary ? '是' : '否' }}
            </template>
          </el-table-column>
          <el-table-column label="操作" width="140" fixed="right">
            <template #default>
              <el-button text type="primary" @click="openPath('/organization')">
                查看组织
              </el-button>
            </template>
          </el-table-column>
        </el-table>
      </el-card>

      <el-card class="table-card" shadow="never">
        <template #header>
          <div class="table-toolbar">
            <strong>快捷入口</strong>
          </div>
        </template>
        <div class="action-grid">
          <button
            v-for="action in quickActions"
            :key="action.path"
            type="button"
            class="workspace-action"
            @click="openPath(action.path)"
          >
            {{ action.label }}
          </button>
        </div>
      </el-card>
    </section>

    <section class="split-grid">
      <el-card class="table-card" shadow="never">
        <template #header>
          <div class="table-toolbar">
            <strong>待办概览</strong>
          </div>
        </template>
        <el-table v-loading="loading" :data="pendingRows" stripe>
          <el-table-column prop="label" label="事项" min-width="180" />
          <el-table-column prop="count" label="数量" width="100" />
          <el-table-column label="入口" width="140" fixed="right">
            <template #default="{ row }">
              <el-button text type="primary" @click="openPath(row.path)">
                进入
              </el-button>
            </template>
          </el-table-column>
        </el-table>
      </el-card>

      <el-card class="table-card" shadow="never">
        <template #header>
          <div class="table-toolbar">
            <strong>我发起的事项</strong>
          </div>
        </template>
        <el-table v-loading="loading" :data="initiatedRows" stripe>
          <el-table-column prop="label" label="事项" min-width="180" />
          <el-table-column prop="count" label="数量" width="100" />
          <el-table-column label="总计" width="120">
            <template #default="{ $index }">
              {{ $index === 0 ? myRequestCount : '--' }}
            </template>
          </el-table-column>
        </el-table>
      </el-card>
    </section>
  </div>
</template>

<style scoped>
.workspace-action {
  border: 1px solid rgba(15, 23, 42, 0.08);
  border-radius: 10px;
  padding: 14px 16px;
  background: #ffffff;
  color: #111827;
  cursor: pointer;
  text-align: left;
}

.workspace-action:hover {
  border-color: rgba(64, 158, 255, 0.25);
  background: #ecf5ff;
}
</style>
