<script setup lang="ts">
import { ElMessage, ElMessageBox } from 'element-plus'
import { onMounted, ref } from 'vue'
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

const loading = ref(false)
const pendingItems = ref<PendingDepartmentJoinRequestItem[]>([])
const myItems = ref<DepartmentJoinRequestItem[]>([])
const pendingShareItems = ref<KnowledgeBaseShareRequestItem[]>([])
const myShareItems = ref<KnowledgeBaseShareRequestItem[]>([])

async function loadData() {
  loading.value = true
  try {
    const [pendingResult, myResult, pendingShareResult, myShareResult] = await Promise.all([
      fetchPendingDepartmentJoinRequests(),
      fetchMyDepartmentJoinRequests(),
      fetchPendingKnowledgeBaseShareRequests(),
      fetchMyKnowledgeBaseShareRequests(),
    ])
    pendingItems.value = pendingResult.items
    myItems.value = myResult.items
    pendingShareItems.value = pendingShareResult.items
    myShareItems.value = myShareResult.items
  } catch (error) {
    ElMessage.error('读取审批数据失败。')
    console.error(error)
  } finally {
    loading.value = false
  }
}

async function handleApprove(requestId: number) {
  try {
    const { value } = await ElMessageBox.prompt('可选填写审批意见', '审批通过', {
      inputPlaceholder: '例如：通过，欢迎加入部门',
      confirmButtonText: '通过',
      cancelButtonText: '取消',
    })
    await approveDepartmentJoinRequest(requestId, { review_comment: value })
    ElMessage.success('已通过该申请。')
    await loadData()
  } catch (error) {
    if (error !== 'cancel') {
      console.error(error)
    }
  }
}

async function handleReject(requestId: number) {
  try {
    const { value } = await ElMessageBox.prompt('请输入驳回原因', '驳回申请', {
      inputPlaceholder: '例如：当前部门暂未开放该角色',
      confirmButtonText: '驳回',
      cancelButtonText: '取消',
    })
    await rejectDepartmentJoinRequest(requestId, { review_comment: value })
    ElMessage.success('已驳回该申请。')
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
      inputPlaceholder: '例如：同意共享给目标部门使用',
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
      inputPlaceholder: '例如：当前部门暂不开放该类知识资产',
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
    <section class="hero-card">
      <div>
        <p class="page-eyebrow">Approval Center</p>
        <h2>审批中心已经接通部门加入申请，后续继续扩展文档发布和共享审批。</h2>
        <p class="page-copy">
          当前后端已支持负责人查看待审批的部门加入申请，并执行通过 / 驳回。下一阶段会继续接入文档发布审批、共享审批和更完整的多级审批流。
        </p>
      </div>
    </section>

    <el-card shadow="never" class="soft-card">
      <template #header>审批中心</template>
      <el-skeleton :loading="loading" animated :rows="6">
        <template #default>
          <el-tabs>
            <el-tab-pane :label="`待我审批 (${pendingItems.length})`">
              <el-table :data="pendingItems" empty-text="当前没有待审批的加入申请">
                <el-table-column prop="applicant_username" label="申请人" min-width="120" />
                <el-table-column prop="applicant_email" label="邮箱" min-width="180" />
                <el-table-column prop="target_department_name" label="目标部门" min-width="140" />
                <el-table-column prop="requested_role_code" label="申请角色" min-width="140" />
                <el-table-column prop="reason" label="申请理由" min-width="220" show-overflow-tooltip />
                <el-table-column label="操作" width="180" fixed="right">
                  <template #default="{ row }">
                    <el-button type="success" link @click="handleApprove(row.id)">通过</el-button>
                    <el-button type="danger" link @click="handleReject(row.id)">驳回</el-button>
                  </template>
                </el-table-column>
                </el-table>
            </el-tab-pane>

            <el-tab-pane :label="`我发起的 (${myItems.length})`">
              <el-table :data="myItems" empty-text="你还没有发起过申请">
                <el-table-column prop="target_department_name" label="目标部门" min-width="140" />
                <el-table-column prop="requested_role_code" label="申请角色" min-width="140" />
                <el-table-column prop="reason" label="申请理由" min-width="220" show-overflow-tooltip />
                <el-table-column prop="status" label="状态" width="120" />
                <el-table-column prop="review_comment" label="审批意见" min-width="180" show-overflow-tooltip />
              </el-table>
            </el-tab-pane>

            <el-tab-pane :label="`共享待审批 (${pendingShareItems.length})`">
              <el-table :data="pendingShareItems" empty-text="当前没有待审批的共享申请">
                <el-table-column prop="knowledge_base_name" label="知识库空间" min-width="160" />
                <el-table-column prop="source_department_name" label="来源部门" min-width="140" />
                <el-table-column prop="target_department_name" label="目标部门" min-width="140" />
                <el-table-column prop="requested_by_username" label="申请人" min-width="120" />
                <el-table-column prop="reason" label="共享理由" min-width="220" show-overflow-tooltip />
                <el-table-column label="操作" width="180" fixed="right">
                  <template #default="{ row }">
                    <el-button type="success" link @click="handleApproveShare(row.id)">通过</el-button>
                    <el-button type="danger" link @click="handleRejectShare(row.id)">驳回</el-button>
                  </template>
                </el-table-column>
              </el-table>
            </el-tab-pane>

            <el-tab-pane :label="`我发起的共享 (${myShareItems.length})`">
              <el-table :data="myShareItems" empty-text="你还没有发起过共享申请">
                <el-table-column prop="knowledge_base_name" label="知识库空间" min-width="160" />
                <el-table-column prop="source_department_name" label="来源部门" min-width="140" />
                <el-table-column prop="target_department_name" label="目标部门" min-width="140" />
                <el-table-column prop="reason" label="共享理由" min-width="220" show-overflow-tooltip />
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
