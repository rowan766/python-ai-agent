<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  approveKnowledgeBaseShareRequest,
  fetchMyKnowledgeBaseShareRequests,
  fetchPendingKnowledgeBaseShareRequests,
  rejectKnowledgeBaseShareRequest,
} from '@/api/modules/knowledge'
import {
  approveDepartmentJoinRequest,
  fetchMyDepartmentJoinRequests,
  fetchPendingDepartmentJoinRequests,
  rejectDepartmentJoinRequest,
} from '@/api/modules/organization'
import type {
  DepartmentJoinRequestItem,
  PendingDepartmentJoinRequestItem,
} from '@/types/organization'
import type { KnowledgeBaseShareRequestItem } from '@/types/knowledge'
import { formatRequestedRole } from '@/utils/organization'

const loading = ref(false)
const pendingJoinItems = ref<PendingDepartmentJoinRequestItem[]>([])
const myJoinItems = ref<DepartmentJoinRequestItem[]>([])
const pendingShareItems = ref<KnowledgeBaseShareRequestItem[]>([])
const myShareItems = ref<KnowledgeBaseShareRequestItem[]>([])

const pendingTotal = computed(() => pendingJoinItems.value.length + pendingShareItems.value.length)
const initiatedTotal = computed(() => myJoinItems.value.length + myShareItems.value.length)

async function loadData() {
  loading.value = true
  try {
    const [pendingJoinResult, myJoinResult, pendingShareResult, myShareResult] = await Promise.all([
      fetchPendingDepartmentJoinRequests(),
      fetchMyDepartmentJoinRequests(),
      fetchPendingKnowledgeBaseShareRequests(),
      fetchMyKnowledgeBaseShareRequests(),
    ])
    pendingJoinItems.value = pendingJoinResult.items
    myJoinItems.value = myJoinResult.items
    pendingShareItems.value = pendingShareResult.items
    myShareItems.value = myShareResult.items
  } catch (error) {
    ElMessage.error('读取审批数据失败，请稍后重试。')
    console.error(error)
  } finally {
    loading.value = false
  }
}

async function handleApproveJoin(requestId: number) {
  try {
    const { value } = await ElMessageBox.prompt('可选填写审批意见', '通过组织申请', {
      inputPlaceholder: '例如：通过，后续请把资料统一沉淀到产品空间',
      confirmButtonText: '通过',
      cancelButtonText: '取消',
    })
    await approveDepartmentJoinRequest(requestId, { review_comment: value })
    ElMessage.success('已通过该组织申请。')
    await loadData()
  } catch (error) {
    if (error !== 'cancel') {
      console.error(error)
    }
  }
}

async function handleRejectJoin(requestId: number) {
  try {
    const { value } = await ElMessageBox.prompt('请输入驳回原因', '驳回组织申请', {
      inputPlaceholder: '例如：当前阶段先不开放该协作范围',
      confirmButtonText: '驳回',
      cancelButtonText: '取消',
    })
    await rejectDepartmentJoinRequest(requestId, { review_comment: value })
    ElMessage.success('已驳回该组织申请。')
    await loadData()
  } catch (error) {
    if (error !== 'cancel') {
      console.error(error)
    }
  }
}

async function handleApproveShare(requestId: number) {
  try {
    const { value } = await ElMessageBox.prompt('可选填写审批意见', '通过共享申请', {
      inputPlaceholder: '例如：同意纳入产品部门的可见范围',
      confirmButtonText: '通过',
      cancelButtonText: '取消',
    })
    await approveKnowledgeBaseShareRequest(requestId, { review_comment: value })
    ElMessage.success('已通过该共享申请。')
    await loadData()
  } catch (error) {
    if (error !== 'cancel') {
      console.error(error)
    }
  }
}

async function handleRejectShare(requestId: number) {
  try {
    const { value } = await ElMessageBox.prompt('请输入驳回原因', '驳回共享申请', {
      inputPlaceholder: '例如：当前阶段暂不向该部门开放这类资料',
      confirmButtonText: '驳回',
      cancelButtonText: '取消',
    })
    await rejectKnowledgeBaseShareRequest(requestId, { review_comment: value })
    ElMessage.success('已驳回该共享申请。')
    await loadData()
  } catch (error) {
    if (error !== 'cancel') {
      console.error(error)
    }
  }
}

onMounted(() => {
  void loadData()
})
</script>

<template>
  <div class="page">
    <section class="hero-card approvals-hero">
      <div>
        <p class="page-eyebrow">Approvals</p>
        <h2>审批页只处理待办和申请记录，不再和组织治理混在一起。</h2>
        <p class="page-copy">
          你在这里看到的只有两类工作：组织加入审批和知识空间共享审批。处理完成后，相关可见范围会立刻在空间和文档页生效。
        </p>
      </div>
      <div class="hero-card__summary">
        <span>{{ pendingTotal }}</span>
        <small>当前待处理审批</small>
      </div>
    </section>

    <section class="stat-grid">
      <el-card class="metric-card" shadow="hover">
        <span class="metric-card__label">待我处理</span>
        <strong>{{ pendingTotal }}</strong>
        <p>进入这页的首要目标就是把这些待办清空。</p>
      </el-card>
      <el-card class="metric-card" shadow="hover">
        <span class="metric-card__label">组织申请待办</span>
        <strong>{{ pendingJoinItems.length }}</strong>
        <p>会影响成员的部门归属和后续可见范围。</p>
      </el-card>
      <el-card class="metric-card" shadow="hover">
        <span class="metric-card__label">共享申请待办</span>
        <strong>{{ pendingShareItems.length }}</strong>
        <p>会影响目标部门是否能看到对应知识空间。</p>
      </el-card>
      <el-card class="metric-card" shadow="hover">
        <span class="metric-card__label">我发起的事项</span>
        <strong>{{ initiatedTotal }}</strong>
        <p>方便回看自己发起过的组织和共享申请。</p>
      </el-card>
    </section>

    <el-card shadow="never" class="soft-card">
      <template #header>审批中心</template>
      <el-skeleton :loading="loading" animated :rows="6">
        <template #default>
          <el-tabs>
            <el-tab-pane :label="`待我处理的组织申请 (${pendingJoinItems.length})`">
              <el-table :data="pendingJoinItems" empty-text="当前没有待处理的组织申请">
                <el-table-column prop="applicant_username" label="申请人" min-width="120" />
                <el-table-column prop="applicant_email" label="邮箱" min-width="180" />
                <el-table-column prop="target_department_name" label="目标部门" min-width="140" />
                <el-table-column label="期望职责" min-width="140">
                  <template #default="{ row }">
                    {{ formatRequestedRole(row.requested_role_code) }}
                  </template>
                </el-table-column>
                <el-table-column prop="reason" label="职责说明" min-width="220" show-overflow-tooltip />
                <el-table-column label="操作" width="180" fixed="right">
                  <template #default="{ row }">
                    <el-button type="success" link @click="handleApproveJoin(row.id)">通过</el-button>
                    <el-button type="danger" link @click="handleRejectJoin(row.id)">驳回</el-button>
                  </template>
                </el-table-column>
              </el-table>
            </el-tab-pane>

            <el-tab-pane :label="`待我处理的共享申请 (${pendingShareItems.length})`">
              <el-table :data="pendingShareItems" empty-text="当前没有待处理的共享申请">
                <el-table-column prop="knowledge_base_name" label="知识空间" min-width="170" />
                <el-table-column prop="source_department_name" label="来源部门" min-width="140" />
                <el-table-column prop="target_department_name" label="目标部门" min-width="140" />
                <el-table-column prop="requested_by_username" label="申请人" min-width="120" />
                <el-table-column prop="reason" label="共享原因" min-width="220" show-overflow-tooltip />
                <el-table-column label="操作" width="180" fixed="right">
                  <template #default="{ row }">
                    <el-button type="success" link @click="handleApproveShare(row.id)">通过</el-button>
                    <el-button type="danger" link @click="handleRejectShare(row.id)">驳回</el-button>
                  </template>
                </el-table-column>
              </el-table>
            </el-tab-pane>

            <el-tab-pane :label="`我发起的组织申请 (${myJoinItems.length})`">
              <el-table :data="myJoinItems" empty-text="你还没有发起过组织申请">
                <el-table-column prop="target_department_name" label="目标部门" min-width="140" />
                <el-table-column label="期望职责" min-width="140">
                  <template #default="{ row }">
                    {{ formatRequestedRole(row.requested_role_code) }}
                  </template>
                </el-table-column>
                <el-table-column prop="reason" label="职责说明" min-width="220" show-overflow-tooltip />
                <el-table-column prop="status" label="状态" width="120" />
                <el-table-column prop="review_comment" label="审批意见" min-width="180" show-overflow-tooltip />
              </el-table>
            </el-tab-pane>

            <el-tab-pane :label="`我发起的共享申请 (${myShareItems.length})`">
              <el-table :data="myShareItems" empty-text="你还没有发起过共享申请">
                <el-table-column prop="knowledge_base_name" label="知识空间" min-width="170" />
                <el-table-column prop="source_department_name" label="来源部门" min-width="140" />
                <el-table-column prop="target_department_name" label="目标部门" min-width="140" />
                <el-table-column prop="reason" label="共享原因" min-width="220" show-overflow-tooltip />
                <el-table-column prop="status" label="状态" width="120" />
                <el-table-column prop="review_comment" label="审批意见" min-width="180" show-overflow-tooltip />
              </el-table>
            </el-tab-pane>
          </el-tabs>
        </template>
      </el-skeleton>
    </el-card>
  </div>
</template>

<style scoped>
.approvals-hero {
  align-items: center;
}
</style>
