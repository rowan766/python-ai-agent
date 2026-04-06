<script setup lang="ts">
import { ElMessage, ElMessageBox } from 'element-plus'
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  approveKnowledgeBaseShareRequest,
  fetchMyKnowledgeBaseShareRequests,
  fetchPendingKnowledgeBaseShareRequests,
  rejectKnowledgeBaseShareRequest,
} from '@/api/modules/knowledge'
import {
  approveDepartmentJoinRequest,
  bootstrapFirstDepartment,
  createDepartmentJoinRequest,
  fetchDepartmentTree,
  fetchMyDepartmentJoinRequests,
  fetchPendingDepartmentJoinRequests,
  rejectDepartmentJoinRequest,
} from '@/api/modules/organization'
import { useAuthStore } from '@/stores/auth'
import type {
  DepartmentJoinRequestItem,
  DepartmentNode,
  PendingDepartmentJoinRequestItem,
} from '@/types/organization'
import type { KnowledgeBaseShareRequestItem } from '@/types/knowledge'

type OrganizationTab = 'access' | 'departments' | 'approvals'

const VALID_TABS: OrganizationTab[] = ['access', 'departments', 'approvals']

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()

const loading = ref(false)
const submitting = ref(false)
const pendingItems = ref<PendingDepartmentJoinRequestItem[]>([])
const myItems = ref<DepartmentJoinRequestItem[]>([])
const pendingShareItems = ref<KnowledgeBaseShareRequestItem[]>([])
const myShareItems = ref<KnowledgeBaseShareRequestItem[]>([])
const departments = ref<DepartmentNode[]>([])
const activeTab = ref<OrganizationTab>(normalizeTab(route.query.tab))

const bootstrapForm = reactive({
  code: 'dept-root',
  name: '企业知识中心',
  full_name: '企业知识中心',
})

const joinForm = reactive({
  target_department_id: undefined as number | undefined,
  requested_role_code: 'department_member',
  reason: '',
})

const hasDepartments = computed(() => departments.value.length > 0)
const hasMemberships = computed(() => (authStore.user?.memberships?.length ?? 0) > 0)
const totalDepartmentCount = computed(() => countDepartments(departments.value))
const totalPendingApprovals = computed(() => pendingItems.value.length + pendingShareItems.value.length)

function normalizeTab(rawValue: unknown): OrganizationTab {
  return VALID_TABS.includes(rawValue as OrganizationTab)
    ? (rawValue as OrganizationTab)
    : 'access'
}

function syncTabQuery(tab: OrganizationTab) {
  if (route.query.tab === tab) {
    return
  }
  void router.replace({
    name: 'organization',
    query: {
      ...route.query,
      tab,
    },
  })
}

function countDepartments(nodes: DepartmentNode[]): number {
  return nodes.reduce((total, node) => total + 1 + countDepartments(node.children || []), 0)
}

async function loadData() {
  loading.value = true
  try {
    const [treeResult, myResult, pendingResult, myShareResult, pendingShareResult, userResult] =
      await Promise.allSettled([
        fetchDepartmentTree(),
        fetchMyDepartmentJoinRequests(),
        fetchPendingDepartmentJoinRequests(),
        fetchMyKnowledgeBaseShareRequests(),
        fetchPendingKnowledgeBaseShareRequests(),
        authStore.fetchCurrentUser(),
      ])

    departments.value = treeResult.status === 'fulfilled' ? treeResult.value.items : []
    myItems.value = myResult.status === 'fulfilled' ? myResult.value.items : []
    pendingItems.value = pendingResult.status === 'fulfilled' ? pendingResult.value.items : []
    myShareItems.value = myShareResult.status === 'fulfilled' ? myShareResult.value.items : []
    pendingShareItems.value =
      pendingShareResult.status === 'fulfilled' ? pendingShareResult.value.items : []

    if (userResult.status === 'rejected') {
      throw userResult.reason
    }
  } catch (error) {
    ElMessage.error('读取组织中心数据失败，请稍后重试。')
    console.error(error)
  } finally {
    loading.value = false
  }
}

async function handleBootstrap() {
  submitting.value = true
  try {
    await bootstrapFirstDepartment(bootstrapForm)
    ElMessage.success('首个部门初始化成功，你已成为默认负责人。')
    await loadData()
  } catch (error) {
    ElMessage.error('初始化首个部门失败，请检查编码是否重复。')
    console.error(error)
  } finally {
    submitting.value = false
  }
}

async function handleJoinRequest() {
  if (!joinForm.target_department_id) {
    ElMessage.warning('请先选择目标部门。')
    return
  }
  if (!joinForm.reason.trim()) {
    ElMessage.warning('请填写申请理由。')
    return
  }

  submitting.value = true
  try {
    await createDepartmentJoinRequest({
      target_department_id: joinForm.target_department_id,
      requested_role_code: joinForm.requested_role_code,
      reason: joinForm.reason.trim(),
    })
    ElMessage.success('加入部门申请已提交。')
    joinForm.reason = ''
    await loadData()
    activeTab.value = 'approvals'
  } catch (error) {
    ElMessage.error('申请提交失败，请确认是否已有待审批记录。')
    console.error(error)
  } finally {
    submitting.value = false
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

watch(
  () => route.query.tab,
  (value) => {
    activeTab.value = normalizeTab(value)
  },
)

watch(activeTab, (value) => {
  syncTabQuery(value)
})

onMounted(() => {
  void loadData()
})
</script>

<template>
  <div class="page">
    <section class="hero-card organization-hero">
      <div>
        <h2>组织中心</h2>
        <p class="page-copy">组织接入、部门管理、权限申请、审批处理</p>
      </div>
      <el-tag :type="hasMemberships ? 'success' : 'warning'" effect="dark" round>
        {{ hasMemberships ? '组织已接入' : '待加入组织' }}
      </el-tag>
    </section>

    <section class="stat-grid">
      <el-card class="metric-card" shadow="hover">
        <span class="metric-card__label">组织状态</span>
        <strong>{{ hasMemberships ? '已接入' : '待接入' }}</strong>
        <p>当前账号的组织状态。</p>
      </el-card>
      <el-card class="metric-card" shadow="hover">
        <span class="metric-card__label">部门总数</span>
        <strong>{{ totalDepartmentCount }}</strong>
        <p>当前组织树规模。</p>
      </el-card>
      <el-card class="metric-card" shadow="hover">
        <span class="metric-card__label">我的成员关系</span>
        <strong>{{ authStore.user?.memberships.length || 0 }}</strong>
        <p>影响文档与审批权限。</p>
      </el-card>
      <el-card class="metric-card" shadow="hover">
        <span class="metric-card__label">待处理审批</span>
        <strong>{{ totalPendingApprovals }}</strong>
        <p>待办审批数量。</p>
      </el-card>
    </section>

    <el-card shadow="never" class="soft-card center-tabs">
      <el-tabs v-model="activeTab">
        <el-tab-pane label="接入与权限" name="access">
          <section class="grid-two">
            <el-card shadow="never" class="soft-card soft-card--inner">
              <template #header>当前组织状态</template>
              <el-skeleton :loading="loading" animated :rows="5">
                <template #default>
                  <div v-if="hasMemberships" class="roadmap-boxes">
                    <div
                      v-for="membership in authStore.user?.memberships || []"
                      :key="membership.id"
                      class="roadmap-box"
                    >
                      <strong>{{ membership.department_name }}</strong>
                      <span>
                        {{ membership.membership_type }} / {{ membership.is_primary ? '主部门' : '协作部门' }}
                      </span>
                    </div>
                  </div>
                  <el-empty
                    v-else
                    description="你还没有部门归属。可以先创建首个根部门，或向已有部门发起加入申请。"
                  />
                </template>
              </el-skeleton>
            </el-card>

            <el-card shadow="never" class="soft-card soft-card--inner">
              <template #header>我的申请记录</template>
              <el-table :data="myItems" empty-text="还没有提交过申请" style="width: 100%">
                <el-table-column prop="target_department_name" label="目标部门" min-width="140" />
                <el-table-column prop="requested_role_code" label="申请角色" min-width="140" />
                <el-table-column prop="status" label="状态" width="120" />
                <el-table-column prop="review_comment" label="审批意见" min-width="180" />
              </el-table>
            </el-card>
          </section>

          <section v-if="!hasDepartments" class="grid-two">
            <el-card shadow="never" class="soft-card soft-card--inner">
              <template #header>初始化首个部门</template>
              <el-form label-position="top">
                <el-form-item label="部门编码">
                  <el-input v-model="bootstrapForm.code" placeholder="例如 dept-root" />
                </el-form-item>
                <el-form-item label="部门名称">
                  <el-input v-model="bootstrapForm.name" placeholder="例如 企业知识中心" />
                </el-form-item>
                <el-form-item label="部门全称">
                  <el-input v-model="bootstrapForm.full_name" placeholder="例如 企业知识中心" />
                </el-form-item>
                <el-button type="primary" :loading="submitting" @click="handleBootstrap">
                  创建首个部门并设我为负责人
                </el-button>
              </el-form>
            </el-card>
          </section>

          <section v-else>
            <el-card shadow="never" class="soft-card soft-card--inner">
              <template #header>申请加入部门</template>
              <el-form label-position="top">
                <el-form-item label="目标部门">
                  <el-tree-select
                    v-model="joinForm.target_department_id"
                    :data="departments"
                    node-key="id"
                    check-strictly
                    default-expand-all
                    :props="{ label: 'name', children: 'children', value: 'id' }"
                    placeholder="请选择要加入的部门"
                  />
                </el-form-item>
                <el-form-item label="申请角色">
                  <el-select v-model="joinForm.requested_role_code" placeholder="请选择申请角色">
                    <el-option label="部门成员" value="department_member" />
                    <el-option label="知识上传者" value="knowledge_operator" />
                    <el-option label="知识审核者" value="knowledge_reviewer" />
                  </el-select>
                </el-form-item>
                <el-form-item label="申请理由">
                  <el-input
                    v-model="joinForm.reason"
                    type="textarea"
                    :rows="4"
                    placeholder="请输入申请原因和计划承担的职责"
                  />
                </el-form-item>
                <el-button type="primary" :loading="submitting" @click="handleJoinRequest">
                  提交加入申请
                </el-button>
              </el-form>
            </el-card>
          </section>
        </el-tab-pane>

        <el-tab-pane label="部门与治理" name="departments">
          <div class="section-head">
            <strong>部门结构总览</strong>
            <router-link class="section-head__link" to="/departments">进入高级部门治理</router-link>
          </div>

          <section class="grid-two">
            <el-card shadow="never" class="soft-card soft-card--inner">
              <template #header>当前部门树</template>
              <el-tree
                :data="departments"
                node-key="id"
                default-expand-all
                :props="{ label: 'name', children: 'children' }"
                empty-text="暂无部门"
              />
            </el-card>

            <el-card shadow="never" class="soft-card soft-card--inner">
              <template #header>我的成员关系</template>
              <div class="roadmap-boxes">
                <div
                  v-for="membership in authStore.user?.memberships || []"
                  :key="membership.id"
                  class="roadmap-box"
                >
                  <strong>{{ membership.department_name }}</strong>
                  <span>
                    {{ membership.membership_type }} / {{ membership.is_primary ? '主部门' : '协作部门' }}
                  </span>
                </div>
                <el-empty
                  v-if="!(authStore.user?.memberships?.length)"
                  description="当前没有成员关系。"
                />
              </div>
            </el-card>
          </section>
        </el-tab-pane>

        <el-tab-pane label="审批中心" name="approvals">
          <el-tabs class="approval-tabs">
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

            <el-tab-pane :label="`我发起的加入 (${myItems.length})`">
              <el-table :data="myItems" empty-text="你还没有发起过加入申请">
                <el-table-column prop="target_department_name" label="目标部门" min-width="140" />
                <el-table-column prop="requested_role_code" label="申请角色" min-width="140" />
                <el-table-column prop="reason" label="申请理由" min-width="220" show-overflow-tooltip />
                <el-table-column prop="status" label="状态" width="120" />
                <el-table-column prop="review_comment" label="审批意见" min-width="180" show-overflow-tooltip />
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
        </el-tab-pane>
      </el-tabs>
    </el-card>
  </div>
</template>

<style scoped>
.organization-hero {
  align-items: center;
}

.center-tabs :deep(.el-tabs__header) {
  margin-bottom: 22px;
}

.soft-card--inner {
  border: 1px solid rgba(24, 54, 48, 0.08);
}

.section-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 18px;
}

.section-head strong {
  display: block;
  color: var(--page-green-deep);
}

.section-head__link {
  color: var(--page-green);
  font-weight: 600;
  text-decoration: none;
}

.approval-tabs :deep(.el-tabs__header) {
  margin-bottom: 18px;
}

@media (max-width: 960px) {
  .organization-hero,
  .section-head {
    align-items: flex-start;
    flex-direction: column;
  }
}
</style>
